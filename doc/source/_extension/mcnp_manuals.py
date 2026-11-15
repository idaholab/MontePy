"""Sphinx extension for listing MCNP manual references in docstrings.

Add to conf.py::

    extensions = [..., "mcnp_manuals"]
    mcnp_manual_versions = ["632", "631", "63", "62"]  # newest first

Usage::

    .. mcnp-manuals::

       :632sec: 5.2
       :631sec: 5.2
       :62: 55

Each field name is an ``extlinks`` role name without the ``manual`` prefix
(``632sec`` is ``:manual632sec:``), and the field body is that role's argument.
The newest manual that has an entry is always shown; the others are put in a
collapsed ``<details>`` element (HTML) or shown flat (other builders), as a table
of manual and section/page.

Every mistake (unknown key, empty body, no entries, non-field-list content)
is a hard error so that ``sphinx -W`` fails rather than silently dropping
a reference.
"""

from __future__ import annotations

import re
from typing import Any, Dict

from docutils import nodes
from docutils.parsers.rst import Directive
from sphinx.application import Sphinx

SUFFIXES = ("sec", "part", "chapter", "sub")
"""The role suffixes that can follow a manual version in a field name.

These mirror the keys of ``_MCNP_ANCHOR_KINDS`` in ``conf.py``.
The empty suffix (a subsection, or a page for the page-only manuals) is implicit.
"""


class mcnp_details(nodes.General, nodes.Element):
    """A group of nodes that HTML builders collapse into a ``<details>`` element.

    The ``summary`` attribute is the text shown on the collapsed element.
    The children are rendered as usual.
    Builders without a ``<details>`` equivalent (LaTeX, plain text, man pages,
    Texinfo) render just the children, with no surrounding element or summary.
    """


def _visit_details_html(self, node):
    """Open the ``<details>`` element for an :class:`mcnp_details` node.

    Sphinx calls this as ``visit(translator, node)``, which is why the first
    parameter is ``self``: it is the HTML translator, not an instance of anything
    defined in this module. That is also why this is a module level function
    and not a method of the directive: ``app.add_node`` takes plain callables.

    The element is closed by :func:`_depart_details_html`.
    The summary is escaped with the translator's own ``encode`` so any markup
    characters in it are safe.

    Parameters
    ----------
    self : sphinx.writers.html.HTML5Translator
        The translator building the page.
    node : mcnp_details
        The node being visited. Its ``summary`` attribute is the clickable text.
    """
    self.body.append(
        '<details class="mcnp-manuals">\n<summary>'
        f"{self.encode(node['summary'])}</summary>\n"
    )


def _depart_details_html(self, node):
    """Close the ``<details>`` element opened by :func:`_visit_details_html`.

    Parameters
    ----------
    self : sphinx.writers.html.HTML5Translator
        The translator building the page.
    node : mcnp_details
        The node being departed. Unused, but Sphinx always passes it.
    """
    self.body.append("</details>\n")


def _passthrough(self, node):
    """Visit or depart an :class:`mcnp_details` node without writing anything.

    Used as both the ``visit`` and ``depart`` function for the builders that
    have no equivalent of ``<details>``. Doing nothing means only the node's
    children are written, so the table appears flat in the output.
    Each builder needs both functions registered, even if they do nothing.

    Parameters
    ----------
    self : sphinx.writers.text.TextTranslator or sphinx.writers.latex.LaTeXTranslator, etc.
        The translator building the output. Unused.
    node : mcnp_details
        The node being visited or departed. Unused.
    """


class MCNPManuals(Directive):
    """The ``mcnp-manuals`` directive.

    The content must be a field list. See the module docstring for the syntax.
    The result is a bullet list of the references into the newest manual that
    has any, followed by an :class:`mcnp_details` node holding a table of the
    references into the older manuals (if there are any).

    The version order comes from the ``mcnp_manual_versions`` config value, and
    the URLs and link text come from the ``extlinks`` config value, so this
    class has no manual specific data of its own.
    """

    has_content = True
    required_arguments = 0
    optional_arguments = 0

    @staticmethod
    def _make_row(*cells):
        """Build a table row with one entry per cell.

        Parameters
        ----------
        *cells : docutils.nodes.Node
            The node to put in each column. Each is wrapped in a paragraph
            inside its own table entry.

        Returns
        -------
        docutils.nodes.row
            The row.
        """
        row = nodes.row()
        for cell in cells:
            row += nodes.entry("", nodes.paragraph("", "", cell))
        return row

    @staticmethod
    def _make_table(rows):
        """Build the two column table of older manual references.

        The columns are "Manual" (the name of the manual) and "Reference" (a link
        to the section or page).
        The table is given the class ``mcnp-manuals-table`` so it can be styled.

        Both columns are given the same width of 20. HTML treats column widths
        as relative proportions, and equal ones leave the layout to the browser,
        so the value doesn't matter there. The plain text builder, though, uses
        them as absolute widths in characters when wrapping, and a width as small
        as 1 makes it loop forever trying to fit "Manual" into one character.
        20 comfortably fits the longest manual name and reference.

        Parameters
        ----------
        rows : list[tuple[str, docutils.nodes.reference]]
            One ``(manual name, reference link)`` pair for each row, in the
            order to display them.

        Returns
        -------
        docutils.nodes.table
            The table.
        """
        table = nodes.table(classes=["mcnp-manuals-table"])
        tgroup = nodes.tgroup(cols=2)
        table += tgroup
        for _ in range(2):
            tgroup += nodes.colspec(colwidth=20)
        head = nodes.thead()
        head += MCNPManuals._make_row(nodes.Text("Manual"), nodes.Text("Reference"))
        tgroup += head
        body = nodes.tbody()
        for name, ref in rows:
            body += MCNPManuals._make_row(nodes.Text(name), ref)
        tgroup += body
        return table

    def run(self):
        """Parse the field list and build the nodes to insert in the document.

        Every problem is raised with ``self.error``, which Sphinx reports as an
        error with the file and line, so a build with ``-W`` fails.
        Problems detected are an empty ``mcnp_manual_versions``, no content,
        content that is not a single field list, a key that is not a known
        version plus an optional suffix (or that has no matching ``extlinks``
        role), and a value that is empty or has more than one word.

        Fields are grouped by manual version. Within a version they keep the
        order they were written in, but the versions themselves are ordered by
        ``mcnp_manual_versions`` no matter how the fields were ordered.

        The table splits the link text from ``extlinks`` (for example
        ``MCNP 6.3.1 manual § 5.2``) at `` manual `` into the manual name and the
        reference. That relies on the captions in ``conf.py`` following the
        pattern ``<name> manual <reference>``. If a caption does not contain
        `` manual ``, the whole text is used as the reference and the manual
        column is left empty.

        Returns
        -------
        list[docutils.nodes.Node]
            A bullet list for the newest manual, followed by an
            :class:`mcnp_details` node holding the table if any other manual
            has an entry.
        """
        config = self.state.document.settings.env.config
        versions = list(config.mcnp_manual_versions)
        extlinks = config.extlinks
        if not versions:
            raise self.error("mcnp_manual_versions is empty in conf.py.")
        key_re = re.compile(
            "^(%s)(%s)?$"
            % (
                "|".join(re.escape(v) for v in sorted(versions, key=len, reverse=True)),
                "|".join(SUFFIXES),
            )
        )

        if not self.content:
            raise self.error("mcnp-manuals needs at least one ':<key>: <value>' field.")
        container = nodes.Element()
        self.state.nested_parse(self.content, self.content_offset, container)
        if len(container) != 1 or not isinstance(container[0], nodes.field_list):
            raise self.error(
                "mcnp-manuals content must be only a field list, e.g. ':632sec: 5.2'."
            )

        by_version: Dict[str, list] = {}
        for field in container[0]:
            key = field[0].astext().strip()
            value = field[1].astext().strip()
            match = key_re.match(key)
            role = f"manual{key}"
            if match is None or role not in extlinks:
                raise self.error(
                    f"Unknown MCNP manual key '{key}'. Expected a version from "
                    f"{versions} plus an optional suffix from {list(SUFFIXES)}."
                )
            if not value or len(value.split()) != 1:
                raise self.error(
                    f"Key '{key}' needs exactly one section or page, got '{value}'."
                )
            url, caption = extlinks[role]
            text = caption % value
            ref = nodes.reference("", text, refuri=url % value, internal=False)
            item = nodes.list_item("", nodes.paragraph("", "", ref))
            name, sep, short = text.partition(" manual ")
            if sep:
                row = (name, nodes.reference("", short, refuri=url % value))
            else:
                row = ("", nodes.reference("", text, refuri=url % value))
            by_version.setdefault(match.group(1), []).append((item, row))

        ordered = [v for v in versions if v in by_version]
        result = []
        newest, rest = ordered[0], ordered[1:]
        result.append(nodes.bullet_list("", *[i for i, _ in by_version[newest]]))
        if rest:
            older = [e for v in rest for e in by_version[v]]
            details = mcnp_details(summary="Older manuals")
            details += self._make_table([row for _, row in older])
            result.append(details)
        return result


def setup(app: Sphinx) -> Dict[str, Any]:
    """Register the extension with Sphinx.

    This is the only part of the module Sphinx looks at, so it is the only
    public interface; everything else here is an implementation detail.

    Registers the ``mcnp_manual_versions`` config value (the manual versions,
    newest first), the ``mcnp-manuals`` directive, and the
    :class:`mcnp_details` node. The node needs a visit and a depart function
    for every builder that might encounter it: HTML gets the ``<details>``
    element, and every other builder gets :func:`_passthrough`.

    Parameters
    ----------
    app : sphinx.application.Sphinx
        The Sphinx application.

    Returns
    -------
    dict[str, Any]
        The extension metadata. The extension keeps no state between documents,
        so it is safe for parallel reading and writing.
    """
    app.add_config_value("mcnp_manual_versions", [], "env")
    app.add_directive("mcnp-manuals", MCNPManuals)
    app.add_node(
        mcnp_details,
        html=(_visit_details_html, _depart_details_html),
        **{
            builder: (_passthrough, _passthrough)
            for builder in ("latex", "text", "man", "texinfo")
        },
    )
    return {"version": "0.1.0", "parallel_read_safe": True, "parallel_write_safe": True}

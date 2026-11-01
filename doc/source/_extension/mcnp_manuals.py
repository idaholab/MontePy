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


class mcnp_details(nodes.General, nodes.Element):
    """A collapsed group of links."""


def _visit_details_html(self, node):
    self.body.append(
        '<details class="mcnp-manuals">\n<summary>'
        f"{self.encode(node['summary'])}</summary>\n"
    )


def _depart_details_html(self, node):
    self.body.append("</details>\n")


def _passthrough(self, node):
    pass


def _make_table(rows):
    """Build a two column table from ``(manual name, reference node)`` rows."""
    table = nodes.table(classes=["mcnp-manuals-table"])
    tgroup = nodes.tgroup(cols=2)
    table += tgroup
    for _ in range(2):
        tgroup += nodes.colspec(colwidth=1)
    head = nodes.thead()
    head += _row(nodes.Text("Manual"), nodes.Text("Reference"))
    tgroup += head
    body = nodes.tbody()
    for name, ref in rows:
        body += _row(nodes.Text(name), ref)
    tgroup += body
    return table


def _row(*cells):
    row = nodes.row()
    for cell in cells:
        row += nodes.entry("", nodes.paragraph("", "", cell))
    return row


class MCNPManuals(Directive):
    has_content = True
    required_arguments = 0
    optional_arguments = 0

    def run(self):
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
            # The table splits "MCNP 6.3.1 manual § 5.2" into name and reference.
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
            details += _make_table([row for _, row in older])
            result.append(details)
        return result


def setup(app: Sphinx) -> Dict[str, Any]:
    """Register the extension."""
    app.add_config_value("mcnp_manual_versions", [], "env")
    app.add_directive("mcnp-manuals", MCNPManuals)
    app.add_node(
        mcnp_details,
        html=(_visit_details_html, _depart_details_html),
        latex=(_passthrough, _passthrough),
        text=(_passthrough, _passthrough),
        man=(_passthrough, _passthrough),
        texinfo=(_passthrough, _passthrough),
    )
    return {"version": "0.1.0", "parallel_read_safe": True, "parallel_write_safe": True}

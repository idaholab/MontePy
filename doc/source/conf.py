"""Sphinx extension to inject schema.org JSON-LD structured data.

Add to conf.py:
    extensions = [..., "schema_org"]

    schema_org_configs = {
        "index": {
            "@type": "SoftwareApplication",
            "name": "MontePy",
            ...
        }
    }
"""

import json
from typing import Any, Dict

from docutils import nodes
from sphinx.application import Sphinx


def add_schema_org_data(app: Sphinx, pagename: str, templatename: str, context: Dict, doctree: Any) -> None:
    """Add schema.org JSON-LD to page if configured."""
    configs = app.config.schema_org_configs
    if not configs or pagename not in configs:
        return

    schema_data = configs[pagename]
    schema_json = json.dumps(schema_data, indent=2)
    context['schema_org_data'] = schema_json


def setup(app: Sphinx) -> Dict[str, Any]:
    """Register the extension."""
    app.add_config_value("schema_org_configs", {}, "html")
    app.connect("html-page-context", add_schema_org_data)

    return {
        "version": "0.1.0",
        "parallel_read_safe": True,
        "parallel_write_safe": True,
    }
(base)
(mgale@INL436227)-(~/dev/montepy) (seo_opt)
 ^_^->cat doc/source/_templates/page.html
{% extends "!page.html" %}

{% block body %}
  {{ super() }}
  {% if pagename == 'index' and schema_org_data %}
  <script type="application/ld+json">
  {{ schema_org_data | safe }}
  </script>
  {% endif %}
{% endblock %}
(base)
(mgale@INL436227)-(~/dev/montepy) (seo_opt)
 ^_^->cat doc/source/conf.py
# Configuration file for the Sphinx documentation builder.
#
# This file only contains a selection of the most common options. For a full
# list see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Path setup --------------------------------------------------------------

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#
import importlib.metadata
import os
import sys

sys.path.insert(0, os.path.abspath("../.."))
import montepy

# -- Project information -----------------------------------------------------

project = "MontePy"
copyright = "2021 – 2026, Battelle Energy Alliance LLC."
author = "Micah D. Gale (@micahgale), Travis J. Labossiere-Hickman (@tjlaboss)"

version = importlib.metadata.version("montepy")
release = version  # Will be true at website deployment.
# -- General configuration ---------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.autosummary",
    "sphinx.ext.napoleon",
    "sphinx.ext.intersphinx",
    "sphinx.ext.extlinks",
    "sphinx.ext.doctest",
    "sphinx.ext.mathjax",
    "sphinx_autodoc_typehints",
    "sphinx_favicon",
    "sphinx_copybutton",
    "autodocsumm",
    "jupyterlite_sphinx",
]

# Add any paths that contain templates here, relative to this directory.
templates_path = ["_templates"]
favicons = [
    "monty.svg",
    "monty-192.png",
    "monty-32.png",
    "monty-32.ico",
]
html_logo = "monty.svg"

html_baseurl = "https://www.montepy.org/en/stable/"
html_extra_path = ["robots.txt", "foo.imcnp", "LICENSE"]

# jupyter lite
jupyterlite_config = "jupyter_lite_config.json"
jupyterlite_overrides = "jupyter_lite.json"
# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = ["_contents/*"]

# autodoc
autodoc_typehints = "both"
typehints_use_signature = True
typehints_use_signature_return = True
autodoc_typehints_description_target = "all"
autodoc_member_order = "groupwise"
autodoc_type_aliases = {
    "ty.PositiveInt": "montepy.types.PositiveInt",
    "ty.NegativeInt": "montepy.types.NegativeInt",
    "ty.NonNegativeInt": "montepy.types.NonNegativeInt",
    "ty.PositiveReal": "montepy.types.PositiveReal",
    "ty.NegativeReal": "montepy.types.NegativeReal",
    "ty.NonNegativeReal": "montepy.types.NonNegativeReal",
    "ty.VersionType": "montepy.types.VersionType",
    "ty.Integral": "numbers.Integral",
    "ty.Real": "numbers.Real",
    "ty.Iterable": "collections.abc.Iterable",
}
# Display the version
display_version = True
autodoc_default_options = {
    "autosummary": True,
    "show-inheritance": True,
    "inherited-members": True,
}

linkcheck_ignore = [
    "https://nucleardata.lanl.gov/.*",
    "https://www.osti.gov/.*",  # Ignore osti.gov URLs
    # GitHub returns 429/502 for link-checkers hitting issue/PR links in CI;
    # the :issue: and :pull: extlinks are validated by the PR workflow itself.
    r"https://github\.com/idaholab/MontePy/(issues|pull)/.*",
    "https://zenodo.org/.*",
]

# -- External link configuration ---------------------------------------------
UM63 = (
    "https://mcnp.lanl.gov/pdf_files/TechReport_2022_LANL_LA-UR-22-30006"
    "Rev.1_KuleszaAdamsEtAl.pdf"
)
UM631 = (
    "https://mcnp.lanl.gov/pdf_files/TechReport_2024_LANL_LA-UR-24-24602"
    "Rev.1_KuleszaAdamsEtAl.pdf"
)
UM62 = (
    "https://mcnp.lanl.gov/pdf_files/TechReport_2017_LANL_LA-UR-17-29981"
    "_WernerArmstrongEtAl.pdf"
)
extlinks = {
    # MCNP 6.3 User's Manual
    "manual63sec": (UM63 + "#section.%s", "MCNP 6.3.0 manual § %s"),
    "manual63": (UM63 + "#subsection.%s", "MCNP 6.3.0 manual § %s"),
    "manual63part": (UM63 + "#part.%s", "MCNP 6.3.0 manual part %s"),
    "manual63chapter": (UM63 + "#chapter.%s", "MCNP 6.3.0 manual Ch. %s"),
    "manual63sub": (UM63 + "#subsubsection.%s", "MCNP 6.3.0 manual § %s"),
    # MCNP 6.3.1 User's Manual
    "manual631sec": (UM631 + "#section.%s", "MCNP 6.3.1 manual § %s"),
    "manual631": (UM631 + "#subsection.%s", "MCNP 6.3.1 manual § %s"),
    "manual631part": (UM631 + "#part.%s", "MCNP 6.3.1 manual part %s"),
    "manual631chapter": (UM631 + "#chapter.%s", "MCNP 6.3.1 manual Ch. %s"),
    "manual631sub": (UM631 + "#subsubsection.%s", "MCNP 6.3.1 manual § %s"),
    # MCNP 6.2 User's manual
    "manual62": (UM62 + "#page=%s", "MCNP 6.2 manual p. %s"),
    "issue": ("https://github.com/idaholab/MontePy/issues/%s", "#%s"),
    "pull": ("https://github.com/idaholab/MontePy/pull/%s", "#%s"),
}


# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#
github_url = "https://github.com/idaholab/MontePy"
html_theme = "pydata_sphinx_theme"
html_theme_options = {
    "navbar_start": ["navbar-logo", "project", "version"],
    "logo": {
        "alt_text": "MontePy documentation home.",
    },
    "icon_links": [
        {
            "name": "GitHub",
            "url": "https://github.com/idaholab/MontePy",
            "icon": "fa-brands fa-square-github",
            "type": "fontawesome",
        },
    ],
    "show_toc_level": 2,
}
html_sidebars = {
    "**": ["search-field.html", "sidebar-nav-bs.html", "sidebar-ethical-ads.html"]
}
apidoc_module_dir = "../../montepy"
apidoc_module_first = True
apidoc_separate_modules = True

suppress_warnings = [
    "epub.unknown_project_files",
    # autosummary.import_cycle is a cosmetic warning triggered by re-exporting
    # classes at the top-level montepy namespace (e.g. montepy.AxisPlane); safe
    # to suppress because the re-exports are intentional.
    "autosummary.import_cycle",
    # "more than one target" warnings arise because montepy.utilities re-exports
    # all exceptions from montepy.exceptions, causing every exception class to be
    # registered under both modules.  Also suppresses the ShortcutNode.type /
    # ValueNode.type ambiguity (two attributes share the same short name).
    "ref.python",
    # Forward-reference failures from get_type_hints() when a name is available
    # at runtime (via from __future__ import annotations) but not at import time
    # in Sphinx's evaluation context (e.g. MCNP_Object in cells.grab_input).
    "sphinx_autodoc_typehints.forward_reference",
]

# -- Intersphinx mapping -----------------------------------------------------
# Allows cross-references to Python stdlib, NumPy, etc.
intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
    "numpy": ("https://numpy.org/doc/stable/", None),
}

# -- Nitpicky mode -----------------------------------------------------------
# Treat broken cross-references as warnings (CI promotes them to errors via -W).
nitpicky = True

# Exact (type, target) pairs that cannot be resolved and should be ignored.
nitpick_ignore = [
    ("py:attr", "type"),
    ("py:class", "type"),
    ("py:class", "montepy.input_parser.syntax_node.ShortcutNode.type"),
    ("py:class", "montepy.input_parser.syntax_node.ValueNode.type"),
    # sly has no intersphinx inventory; all sly.* cross-refs are unresolvable
    ("py:class", "sly.Parser"),
    ("py:class", "sly.Lexer"),
    ("py:class", "sly.lex.Token"),
    ("py:class", "sly.lex.Lexer"),
    ("py:class", "sly.yacc.Parser"),
    ("py:class", "sly.yacc.ParserMeta"),
    ("py:class", "sly.yacc.YaccProduction"),
    ("py:class", "InitInput"),
    # Subpackages referenced with :mod: in docs; autodoc indexes individual classes
    # but not the package-level modules themselves
    # typing.Union is not in the Python intersphinx inventory as a py:data target
    ("py:data", "typing.Union"),
    # Particle is re-exported at montepy.Particle but Sphinx indexes it under
    # montepy.particle.Particle (the defining module).
    ("py:class", "montepy.Particle"),
    # Shorthand aliases used in docstrings that are not registered Sphinx targets.
    ("py:class", "np.ndarray"),
    # Internal type aliases in nuclide.py not exported to the public API.
    ("py:class", "MetaState"),
    ("py:class", "NuclideLike"),
    # sphinx-autodoc-typehints internal class surfaced when it can't resolve a
    # TypeAlias forward reference; harmless to suppress.
    ("py:class", "TypeAliasForwardRef"),
    # Napoleon misreads the bare Returns description in args_checked as a type;
    # the Returns section has been fixed but keep this as a safety net.
    ("py:class", "A decorated function that will do type and value checking at run time based on the annotation."),
    # Partial Annotated type string generated by sphinx-autodoc-typehints from
    # MetaState in nuclide.py docstrings.
    ("py:obj", "typing.Annotated[~numbers.Integral"),
    # Napoleon parses "optional" modifier as a standalone type in some complex
    # multi-alternative parameter type strings in _check_value.py docstrings.
    ("py:class", "optional"),
]

# Regex patterns for cross-reference targets that cannot be resolved.
nitpick_ignore_regex = [
    # sphinx_autodoc_typehints generates "self" and "self._attr" refs for some
    # return-type annotations; these cannot be resolved and are harmless
    (r"py:class", r"^self(\._\w+)?$"),
    # ty.* references arise when get_type_hints() falls back to raw annotation
    # strings and the module alias "ty" (for montepy.types) is not resolvable
    # by Sphinx even after autodoc_type_aliases remapping.
    (r"py:class", r"^ty\..+$"),
    # sphinx-autodoc-typehints expands Annotated metadata and tries to link the
    # inner validator function objects (e.g. greater_than.<locals>.wrapper).
    (r"py:class", r"^<function .+>$"),
    # autodoc_type_aliases remapping can produce quoted strings like
    # 'montepy.types.PositiveInt' when get_type_hints returns a ForwardRef.
    (r"py:class", r"^'[^']+'\s*$"),
]


# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ["_static"]


def _extract_docstring_summary(obj):
    """Extract first sentence of docstring for SEO meta description."""
    if not obj.__doc__:
        return None
    doc = obj.__doc__.strip()
    lines = doc.split("\n")
    first_line = lines[0].strip()
    if not first_line:
        first_line = next((l.strip() for l in lines if l.strip()), None)
    if first_line and len(first_line) > 5:
        return first_line[:150]
    return None


def _add_meta_descriptions(app, docname, source):
    """Inject meta directives for API docs from Python docstrings."""
    if not docname.startswith("api/generated/"):
        return

    obj_name = docname.replace("api/generated/", "")
    try:
        parts = obj_name.split(".")
        obj = montepy
        for part in parts:
            obj = getattr(obj, part)

        summary = _extract_docstring_summary(obj)
        if summary:
            meta_directive = f".. meta::\n   :description lang=en: {summary}\n\n"
            source[0] = meta_directive + source[0]
    except (AttributeError, ImportError):
        pass


def setup(app):
    app.connect("source-read", _add_meta_descriptions)

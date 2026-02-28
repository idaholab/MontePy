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
html_extra_path = ["robots.txt", "foo.imcnp"]

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
    "icon_links": [
        {
            "name": "GitHub",
            "url": "https://github.com/idaholab/MontePy",
            "icon": "fa-brands fa-square-github",
            "type": "fontawesome",
        },
    ],
}
html_sidebars = {
    "**": ["search-field.html", "sidebar-nav-bs.html", "sidebar-ethical-ads.html"]
}
apidoc_module_dir = "../../montepy"
apidoc_module_first = True
apidoc_separate_modules = True

suppress_warnings = ["epub.unknown_project_files"]

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
    # sly is not documented via intersphinx
    ("py:class", "sly.Parser"),
    ("py:class", "sly.Lexer"),
    ("py:class", "sly.lex.Token"),
    # montepy.errors is a deprecated shim; the canonical path is montepy.exceptions
    ("py:class", "montepy.errors.MalformedInputError"),
    ("py:exc", "montepy.errors.MalformedInputError"),
    # Private extension-point methods documented in the developer guide but
    # excluded from autodoc by default; keep as cross-refs for discoverability.
    ("py:func", "montepy.data_inputs.cell_modifier.CellModifierInput._format_tree"),
    ("py:func", "montepy.data_inputs.cell_modifier.CellModifierInput._check_redundant_definitions"),
    # Private internal class not exposed in the public API
    ("py:class", "montepy._singleton.SingletonGroup"),
]

# Regex patterns for cross-reference targets that cannot be resolved.
nitpick_ignore_regex = [
    # Sphinx/autodoc generates bare type names that are not valid cross-ref targets
    (r"py:class", r"^(self|self\._\w+|generator|unknown|function|Class|InitInput|MCNP_Input)$"),
    # sly Token is not in any intersphinx inventory
    (r"py:class", r"^Token$"),
    # Bare unqualified names from :type: annotations in older docstrings
    (r"py:class", r"^(Nucleus|Library|LibraryType|ListNode|MCNP_Input|enum|hexahedron|class)$"),
    (r"py:class", r"^A rectangular prism is a type$"),
    # numpy alias "np" is not in the numpy intersphinx inventory
    (r"py:class", r"^np\..*"),
    # Sphinx autosummary generates internal node type refs
    (r"py:class", r"^montepy\.input_parser\.syntax_node\.(IsotopesNode|ListNode)$"),
    # Old class names that no longer exist (renamed in refactoring)
    (r"py:class", r"^montepy\.(data_cards|mcnp_card|data_input)\..+$"),
    (r"py:func", r"^montepy\.(data_cards|mcnp_card|data_input)\..+$"),
    # Cross-refs using internal module paths (montepy.cell.Cell) instead of the
    # public API path (montepy.Cell) that autosummary uses for inventory entries.
    # These are correct conceptually; the path mismatch is a known limitation.
    # TODO: migrate all cross-refs to public API paths (montepy.Cell, etc.)
    (r"py:attr", r"^montepy\.(cell|mcnp_problem|surfaces|data_inputs)\..+$"),
    (r"py:func", r"^montepy\.(cell|cells|mcnp_problem|surfaces|data_inputs|materials|universe)\..+$"),
    (r"py:mod", r"^montepy\.surfaces$"),
]


# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ["_static"]

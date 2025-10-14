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
copyright = "2021 – 2025, Battelle Energy Alliance LLC."
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
# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = []

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


# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ["_static"]

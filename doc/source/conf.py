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
copyright = "2021 – 2024, Battelle Energy Alliance LLC."
author = "Micah D. Gale (@micahgale), Travis J. Labossiere-Hickman (@tjlaboss)"


release = importlib.metadata.version("montepy")
# -- General configuration ---------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
    "sphinx.ext.intersphinx",
    "sphinx.ext.extlinks",
    "sphinx_sitemap",
]

# Add any paths that contain templates here, relative to this directory.
templates_path = ["_templates"]
html_favicon = "monty.svg"
html_logo = "monty.svg"

html_baseurl = "https://www.montepy.org/"
html_extra_path = ["robots.txt"]
# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = []

# -- External link configuration ---------------------------------------------
UM63 = (
    "https://mcnp.lanl.gov/pdf_files/TechReport_2022_LANL_LA-UR-22-30006"
    "Rev.1_KuleszaAdamsEtAl.pdf"
)
UM62 = (
    "https://mcnp.lanl.gov/pdf_files/TechReport_2017_LANL_LA-UR-17-29981"
    "_WernerArmstrongEtAl.pdf"
)
extlinks = {
    # MCNP 6.3 User's Manual
    "manual63sec": (UM63 + "#section.%s", "MCNP 6.3 manual § %s"),
    "manual63": (UM63 + "#subsection.%s", "MCNP 6.3 manual § %s"),
    "manual63part": (UM63 + "#part.%s", "MCNP 6.3 manual § %s"),
    "manual63chapter": (UM63 + "#chapter.%s", "MCNP 6.3 manual § %s"),
    "manual62": (UM62 + "#page=%s", "MCNP 6.2 manual p. %s"),
    "issue": ("https://github.com/idaholab/MontePy/issues/%s", "#%s"),
    "pull": ("https://github.com/idaholab/MontePy/pull/%s", "#%s"),
}


# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#
html_theme = "sphinx_rtd_theme"
apidoc_module_dir = "../../montepy"
apidoc_module_first = True
apidoc_separate_modules = True


# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ["_static"]

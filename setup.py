from setuptools import setup, find_packages
from mcnpy import __version__, __author__, __email__, __maintainer__

setup(
    install_requires=[
        "numpy",
        "sly",
    ],
    # needs f string formatting
    # needs insertion ordered dicts
    # needs :=
    extras_require={
        "doc": ["sphinx", "sphinxcontrib-apidoc", "sphinx_rtd_theme"],
        "test": ["coverage"],
    },
)

from setuptools import setup, find_packages
from mcnpy import __version__, __author__, __email__, __maintainer__

setup(
    name="montepy",
    version=__version__,
    packages=find_packages(include=["montepy", "montepy.*"]),
    description="A library for reading, editing, and writing MCNP input files.",
    author=__author__,
    author_email=__email__,
    maintainer=__maintainer__,
    maintainer_email=__email__,
    url="https://github.com/idaholab/montepy",
    install_requires=[
        "numpy",
    ],
    extras_require={
        "doc": ["sphinx", "sphinxcontrib-apidoc", "sphinx_rtd_theme"],
        "test": ["coverage"],
    },
)

from setuptools import setup, find_packages
from mcnpy import __version__
setup(
    name="mcnpy",
    version=__version__,
    packages=find_packages(include=['mcnpy', 'mcnpy.*'])
)

# Copyright 2024, Battelle Energy Alliance, LLC All Rights Reserved.
""" MontePy is a library for reading, editing, and writing MCNP input files.

This creates a semantic understanding of the MCNP input file.
start by running montepy.read_input().

You will receive an MCNP_Problem object that you will interact with.
"""

from . import input_parser
from . import constants
import importlib.metadata
from .input_parser.input_reader import read_input
from montepy.cell import Cell
from montepy.mcnp_problem import MCNP_Problem
from montepy.data_inputs.material import Material
from montepy.data_inputs.transform import Transform
from montepy.geometry_operators import Operator
from montepy import geometry_operators
from montepy.input_parser.mcnp_input import Jump
from montepy.particle import Particle
from montepy.surfaces.surface_type import SurfaceType
from montepy.universe import Universe
import sys


try:
    from . import _version

    __version__ = _version.version
except ImportError:
    try:
        from setuptools_scm import get_version

        __version__ = get_version()
    except (ImportError, LookupError):
        __version__ = "Undefined"


# enable deprecated warnings for users
if not sys.warnoptions:
    import os, warnings

    warnings.simplefilter("default")  # Change the filter in this process
    os.environ["PYTHONWARNINGS"] = "default"  # Also affect subprocesses

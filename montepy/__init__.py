# Copyright 2024-2025, Battelle Energy Alliance, LLC All Rights Reserved.
"""MontePy is a library for reading, editing, and writing MCNP input files.

This creates a semantic understanding of the MCNP input file.
start by running montepy.read_input().

You will receive an MCNP_Problem object that you will interact with.
"""

from . import data_inputs
from . import input_parser
from . import constants
import importlib.metadata

from .constants import DEFAULT_VERSION as MCNP_VERSION

# data input promotion

from montepy.data_inputs.material import Material
from montepy.data_inputs.transform import Transform
from montepy.data_inputs.nuclide import Library, Nuclide
from montepy.data_inputs.element import Element
from montepy.data_inputs.lattice import LatticeType
from montepy.data_inputs.thermal_scattering import ThermalScatteringLaw
from montepy.data_inputs.data_parser import parse_data

# geometry
from montepy.geometry_operators import Operator
from montepy import geometry_operators
from montepy.surfaces.surface_type import SurfaceType
from montepy.surfaces import *

# input parser
from montepy.input_parser.mcnp_input import Jump
from .input_parser.input_reader import read_input

# top level
from montepy.particle import Particle, LibraryType
from montepy.universe import Universe
from montepy.cell import Cell
from montepy.mcnp_problem import MCNP_Problem

# collections
from montepy.cells import Cells
from montepy.materials import Materials
from montepy.universes import Universes
from montepy.surface_collection import Surfaces
from montepy.transforms import Transforms

import montepy.errors
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

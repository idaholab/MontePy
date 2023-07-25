""" MCNPy is a library for reading, editing, and writing MCNP input files.

This creates a semantic understanding of the MCNP input file.
start by running mcnpy.read_input().

You will receive an MCNP_Problem object that you will interact with.
"""

__author__ = "Micah Gale, Travis Labossiere-Hickman, Brenna Carbno"
__credits__ = [
    "Micah Gale",
    "Travis Labossiere-Hickman",
    "Austin Carter",
    "Andrew Bascom",
    "Roberto Fairhurst Agosta",
    "Brenna Carbno",
]

name = "mcnpy"
__version__ = "0.2.0.alpha3"
__maintainer__ = "Micah Gale"
__email__ = "micah.gale@inl.gov"
__status__ = "Development"
__all__ = ["cell", "surfaces", "mcnp_object.py", "input_parser"]

from . import input_parser
from . import constants
from .input_parser.input_reader import read_input
from mcnpy.cell import Cell
from mcnpy.mcnp_problem import MCNP_Problem
from mcnpy.data_inputs.material import Material
from mcnpy.data_inputs.transform import Transform
from mcnpy.geometry_operators import Operator
from mcnpy import geometry_operators
from mcnpy.input_parser.mcnp_input import Jump
from mcnpy.particle import Particle
from mcnpy.surfaces.surface_type import SurfaceType
from mcnpy.universe import Universe
import sys

# enable deprecated warnings for users
if not sys.warnoptions:
    import os, warnings

    warnings.simplefilter("default")  # Change the filter in this process
    os.environ["PYTHONWARNINGS"] = "default"  # Also affect subprocesses

""" MontePy is a library for reading, editing, and writing MCNP input files.

This creates a semantic understanding of the MCNP input file.
start by running montepy.read_input().

You will receive an MCNP_Problem object that you will interact with.
"""

__credits__ = [
    "Micah Gale",
    "Travis Labossiere-Hickman",
    "Austin Carter",
    "Andrew Bascom",
    "Roberto Fairhurst Agosta",
    "Brenna Carbno",
]

__status__ = "Development"
__all__ = ["cell", "surfaces", "mcnp_object.py", "input_parser"]

from . import input_parser
from . import constants
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

# enable deprecated warnings for users
if not sys.warnoptions:
    import os, warnings

    warnings.simplefilter("default")  # Change the filter in this process
    os.environ["PYTHONWARNINGS"] = "default"  # Also affect subprocesses

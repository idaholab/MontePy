import unittest
import numpy as np
from montepy.cell import Cell
from montepy.mcnp_problem import MCNP_Problem
from montepy.universe import Universe
from montepy.exceptions import IllegalState

class TestIssue736(unittest.TestCase):
    def test_fill_universes_setter_by_id(self):
        problem = MCNP_Problem("test")
        cell = Cell()
        cell.number = 1
        problem.cells.append(cell)
        uni1 = Universe(1)
        uni2 = Universe(2)
        problem.universes.append(uni1)
        problem.universes.append(uni2)
        # Create a 3D array for testing
        universes_to_set = np.array([[[1, 2, 0]]])
        cell.fill.universes = universes_to_set
        
        # Adjust assertions to match 3D structure
        self.assertIs(cell.fill.universes[0, 0, 0], uni1)
        self.assertIs(cell.fill.universes[0, 0, 1], uni2)
        self.assertIsNone(cell.fill.universes[0, 0, 2])

    def test_fill_universes_setter_no_problem_error(self):
        cell = Cell()
        with self.assertRaises(IllegalState):
            cell.fill.universes = np.array([[[1]]])

    def test_fill_universes_setter_bad_id_error(self):
        problem = MCNP_Problem("test")
        cell = Cell()
        cell.number = 1
        problem.cells.append(cell)
        with self.assertRaises(ValueError):
            cell.fill.universes = np.array([[[999]]])

if __name__ == "__main__":
    unittest.main()

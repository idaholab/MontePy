import mcnpy

from unittest import TestCase


class EdgeCaseTests(TestCase):
    def test_complement_edge_case(self):
        capsule = mcnpy.read_input("tests/inputs/test_complement_edge.imcnp")
        complementing_cell = capsule.cells[2]
        self.assertEqual(len(complementing_cell.complements), 2)

    def test_interp_surface_edge_case(self):
        capsule = mcnpy.read_input("tests/inputs/test_interp_edge.imcnp")
        self.assertEqual(len(capsule.cells[0].surfaces), 4)

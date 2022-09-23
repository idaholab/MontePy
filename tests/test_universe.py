from unittest import TestCase

from mcnpy.input_parser.constants import DEFAULT_VERSION
import mcnpy
from mcnpy.cell import Cell
from mcnpy.errors import *
from mcnpy.input_parser.block_type import BlockType
from mcnpy.input_parser.mcnp_input import Card, Comment, Jump
from mcnpy.universe import Universe
from mcnpy.data_cards.fill import Fill
from mcnpy.data_cards.lattice import Lattice
from mcnpy.data_cards.lattice_card import LatticeCard
from mcnpy.data_cards.universe_card import UniverseCard
import numpy as np


class TestUniverseCard(TestCase):
    def test_universe_init(self):
        card = UniverseCard(in_cell_block=True, key="U", value="5")
        self.assertEqual(card.old_number, 5)
        self.assertTrue(not card.not_truncated)
        # test bad float
        with self.assertRaises(ValueError):
            card = UniverseCard(in_cell_block=True, key="U", value="5.5")

        # test string
        with self.assertRaises(ValueError):
            card = UniverseCard(in_cell_block=True, key="U", value="hi")

        # test negative universe
        card = UniverseCard(in_cell_block=True, key="U", value="-3")
        self.assertEqual(card.old_number, 3)
        self.assertTrue(card.not_truncated)

        universes = [1, 2, 3]
        card = Card(["U " + " ".join(list(map(str, universes)))], BlockType.DATA)
        uni_card = UniverseCard(card)
        self.assertEqual(uni_card._universe, universes)

        # test jump
        card = Card(["U J"], BlockType.DATA)
        uni_card = UniverseCard(card)
        self.assertEqual(uni_card._universe[0], Jump())

        # test bad float
        with self.assertRaises(MalformedInputError):
            card = Card(["U 5.5"], BlockType.DATA)
            uni_card = UniverseCard(card)

        # test bad str
        with self.assertRaises(MalformedInputError):
            card = Card(["U hi"], BlockType.DATA)
            uni_card = UniverseCard(card)

        # test bad negative
        card = Card(["U -2"], BlockType.DATA)
        uni_card = UniverseCard(card)

    def test_str(self):
        card = UniverseCard(in_cell_block=True, key="U", value="5")
        uni = Universe(5)
        card.universe = uni
        output = str(card)
        self.assertIn("U=5", output)
        output = repr(card)
        self.assertIn("UNIVERSE", output)
        self.assertIn("set_in_block: True", output)
        self.assertIn("Universe : Universe(5)", output)

    def test_merge(self):
        card = UniverseCard(in_cell_block=True, key="U", value="5")
        with self.assertRaises(MalformedInputError):
            card.merge(card)

    def test_universe_setter(self):
        card = UniverseCard(in_cell_block=True, key="U", value="5")
        uni = Universe(5)
        card.universe = uni
        self.assertEqual(card.universe, uni)
        self.assertTrue(card.mutated)
        with self.assertRaises(TypeError):
            card.universe = 5

    def test_universe_truncate_setter(self):
        card = UniverseCard(in_cell_block=True, key="U", value="5")
        self.assertTrue(not card.not_truncated)
        card.not_truncated = True
        self.assertTrue(card.not_truncated)
        with self.assertRaises(TypeError):
            card.not_truncated = 5


class TestUniverse(TestCase):
    def test_init(self):
        universe = Universe(5)
        self.assertEqual(universe.number, 5)
        self.assertEqual(universe.old_number, 5)
        self.assertEqual(universe.class_prefix, "u")
        self.assertEqual(universe.allowed_keywords, set())

    def test_number_setter(self):
        universe = Universe(5)
        universe.number = 10
        self.assertEqual(universe.number, 10)
        with self.assertRaises(TypeError):
            universe.number = "hi"
        with self.assertRaises(ValueError):
            universe.number = -1


class TestLattice(TestCase):
    def test_lattice_init(self):
        lattice = LatticeCard(in_cell_block=True, key="lat", value="1")
        self.assertEqual(lattice.lattice, Lattice(1))
        with self.assertRaises(ValueError):
            lattice = LatticeCard(in_cell_block=True, key="lat", value="hi")
        with self.assertRaises(ValueError):
            lattice = LatticeCard(in_cell_block=True, key="lat", value="5")
        lattices = [1, 2, Jump(), Jump()]
        card = Card(["Lat " + " ".join(list(map(str, lattices)))], BlockType.DATA)
        lattice = LatticeCard(card)
        for answer, lattice in zip(lattices, lattice._lattice):
            if isinstance(answer, int):
                self.assertEqual(answer, lattice.value)
            else:
                self.assertEqual(answer, lattice)
        with self.assertRaises(MalformedInputError):
            card = Card(["Lat 3"], BlockType.DATA)
            LatticeCard(card)
        with self.assertRaises(MalformedInputError):
            card = Card(["Lat str"], BlockType.DATA)
            LatticeCard(card)

    def test_lattice_setter(self):
        lattice = LatticeCard(in_cell_block=True, key="lat", value="1")
        lattice.lattice = Lattice(2)
        self.assertEqual(Lattice(2), lattice.lattice)
        lattice.lattice = 1
        self.assertEqual(Lattice(1), lattice.lattice)
        lattice.lattice = None
        self.assertIsNone(lattice.lattice)
        with self.assertRaises(TypeError):
            lattice.lattice = "hi"

        with self.assertRaises(ValueError):
            lattice.lattice = -1

    def test_lattice_deleter(self):
        lattice = LatticeCard(in_cell_block=True, key="lat", value="1")
        del lattice.lattice
        self.assertIsNone(lattice.lattice)

    def test_lattice_merge(self):
        lattice = LatticeCard(in_cell_block=True, key="lat", value="1")
        with self.assertRaises(MalformedInputError):
            lattice.merge(lattice)

    def test_lattice_cell_format(self):
        lattice = LatticeCard(in_cell_block=True, key="lat", value="1")
        output = lattice.format_for_mcnp_input(DEFAULT_VERSION)
        self.assertIn("LAT=1", output[0])
        lattice.lattice = None
        output = lattice.format_for_mcnp_input(DEFAULT_VERSION)
        self.assertEqual(output, [])

    def test_lattice_repr(self):
        lattice = LatticeCard(in_cell_block=True, key="lat", value="1")
        out = repr(lattice)
        self.assertIn("in_cell: True", out)
        self.assertIn("set_in_block: True", out)
        self.assertIn("Lattice_values : Lattice.HEXAHEDRA", out)


class TestFill(TestCase):
    def test_complex_transform_fill_init(self):
        fill = Fill(in_cell_block=True, key="*fill", value="1 (1.5 0.0 0.0)")
        self.assertTrue(fill.hidden_transform)
        self.assertEqual(fill.old_universe_number, 1)
        self.assertEqual(len(fill.transform.displacement_vector), 3)
        self.assertTrue(fill.transform.is_in_degrees)
        fill = Fill(in_cell_block=True, key="fill", value="1 (1.5 0.0 0.0)")
        self.assertTrue(not fill.transform.is_in_degrees)
        fill = Fill(in_cell_block=True, key="fill", value="5 (3)")
        self.assertTrue(not fill.hidden_transform)
        self.assertEqual(fill.old_universe_number, 5)
        self.assertEqual(fill.old_transform_number, 3)
        # test bad string
        with self.assertRaises(ValueError):
            fill = Fill(in_cell_block=True, key="fill", value="hi")
        with self.assertRaises(ValueError):
            fill = Fill(in_cell_block=True, key="fill", value="1 (hi)")
        # test negative universe
        with self.assertRaises(ValueError):
            fill = Fill(in_cell_block=True, key="fill", value="-5")
        with self.assertRaises(ValueError):
            fill = Fill(in_cell_block=True, key="fill", value="5 (-5)")
        with self.assertRaises(ValueError):
            fill = Fill(in_cell_block=True, key="fill", value="5 1 0 0")

    def test_complicated_lattice_fill_init(self):
        fill = Fill(in_cell_block=True, key="fill", value="0:1 0:1 0:1 1 2 3 4 5 6 7 8")
        self.assertEqual(fill.min_index[0], 0)
        self.assertEqual(fill.max_index[2], 1)
        answer = np.array([[[1, 2], [3, 4]], [[5, 6], [7, 8]]])
        self.assertTrue((fill.old_universe_number == answer).all())
        # test string universe
        with self.assertRaises(ValueError):
            fill = Fill(in_cell_block=True, key="fill", value="0:1 0:1 0:1 hi")
        # test string index
        with self.assertRaises(ValueError):
            fill = Fill(in_cell_block=True, key="fill", value="0:1 hi:1 0:1 hi")
        # test negative universe
        with self.assertRaises(ValueError):
            fill = Fill(in_cell_block=True, key="fill", value="0:1 0:1 0:1 -1")
        # test inverted bounds
        with self.assertRaises(ValueError):
            fill = Fill(
                in_cell_block=True, key="fill", value="1:0 0:1 0:1 1 2 3 4 5 6 7 8"
            )

    def test_data_fill_init(self):
        card = Card(["FiLl 1 2 3 4"], BlockType.DATA)
        fill = Fill(card)
        answer = [1, 2, 3, 4]
        self.assertEqual(fill.old_universe_number, answer)
        # jump
        card = Card(["FiLl 1 2J 4"], BlockType.DATA)
        fill = Fill(card)
        answer = [1, Jump(), Jump(), 4]
        self.assertEqual(fill.old_universe_number, answer)
        # test negative universe
        with self.assertRaises(MalformedInputError):
            card = Card(["FiLl 1 -2 3 4"], BlockType.DATA)
            fill = Fill(card)
        # test string universe
        with self.assertRaises(MalformedInputError):
            card = Card(["FiLl 1 foo"], BlockType.DATA)
            fill = Fill(card)

    def test_fill_universe_setter(self):
        fill = Fill(in_cell_block=True, key="fill", value="5")
        uni = mcnpy.Universe(6)
        fill.universe = uni
        self.assertEqual(fill.universe.number, uni.number)
        self.assertTrue(fill.mutated)
        fill.universe = None
        self.assertIsNone(fill.universe)
        fill.universe = uni
        del fill.universe
        self.assertIsNone(fill.universe)
        with self.assertRaises(TypeError):
            fill.universe = "hi"

    def test_fill_merge(self):
        card = Card(["FiLl 1 2 3 4"], BlockType.DATA)
        fill1 = Fill(card)
        fill2 = Fill(card)
        with self.assertRaises(MalformedInputError):
            fill1.merge(fill2)

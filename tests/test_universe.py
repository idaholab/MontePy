from unittest import TestCase

from mcnpy.input_parser.constants import DEFAULT_VERSION
from mcnpy.input_parser import syntax_node
import mcnpy
from mcnpy.cell import Cell
from mcnpy.errors import *
from mcnpy.input_parser.block_type import BlockType
from mcnpy.input_parser.mcnp_input import Input, Jump
from mcnpy.universe import Universe
from mcnpy.data_inputs.fill import Fill
from mcnpy.data_inputs.lattice import Lattice
from mcnpy.data_inputs.lattice_input import LatticeInput
from mcnpy.data_inputs.universe_input import UniverseInput
import numpy as np


class TestUniverseInput(TestCase):
    def test_universe_card_init(self):
        key = syntax_node.ValueNode("U", str)
        value = syntax_node.ValueNode("5", float)
        card = UniverseInput(in_cell_block=True, key=key, value=value)
        self.assertEqual(card.old_number, 5)
        self.assertTrue(not card.not_truncated)
        # test bad float
        with self.assertRaises(ValueError):
            card = UniverseInput(in_cell_block=True, key="U", value="5.5")

        # test string
        with self.assertRaises(ValueError):
            card = UniverseInput(in_cell_block=True, key="U", value="hi")

        # test negative universe
        card = UniverseInput(in_cell_block=True, key="U", value="-3")
        self.assertEqual(card.old_number, 3)
        self.assertTrue(card.not_truncated)

        universes = [1, 2, 3]
        card = Card(["U " + " ".join(list(map(str, universes)))], BlockType.DATA)
        uni_card = UniverseInput(card)
        self.assertEqual(uni_card._universe, universes)

        # test jump
        card = Card(["U J"], BlockType.DATA)
        uni_card = UniverseInput(card)
        self.assertEqual(uni_card._universe[0], Jump())

        # test bad float
        with self.assertRaises(MalformedInputError):
            card = Card(["U 5.5"], BlockType.DATA)
            uni_card = UniverseInput(card)

        # test bad str
        with self.assertRaises(MalformedInputError):
            card = Card(["U hi"], BlockType.DATA)
            uni_card = UniverseInput(card)

        # test bad negative
        card = Card(["U -2"], BlockType.DATA)
        uni_card = UniverseInput(card)

    def test_universe_init(self):
        uni = Universe(5)
        self.assertEqual(uni.number, 5)
        with self.assertRaises(TypeError):
            Universe("hi")
        with self.assertRaises(ValueError):
            Universe(-1)

    def test_str(self):
        card = UniverseInput(in_cell_block=True, key="U", value="5")
        uni = Universe(5)
        card.universe = uni
        output = str(card)
        self.assertIn("U=5", output)
        output = repr(card)
        self.assertIn("UNIVERSE", output)
        self.assertIn("set_in_block: True", output)
        self.assertIn("Universe : Universe(5)", output)

    def test_merge(self):
        card = UniverseInput(in_cell_block=True, key="U", value="5")
        with self.assertRaises(MalformedInputError):
            card.merge(card)

    def test_universe_setter(self):
        card = UniverseInput(in_cell_block=True, key="U", value="5")
        uni = Universe(5)
        card.universe = uni
        self.assertEqual(card.universe, uni)
        with self.assertRaises(TypeError):
            card.universe = 5

    def test_universe_truncate_setter(self):
        card = UniverseInput(in_cell_block=True, key="U", value="5")
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
        lattice = LatticeInput(in_cell_block=True, key="lat", value="1")
        self.assertEqual(lattice.lattice, Lattice(1))
        with self.assertRaises(ValueError):
            lattice = LatticeInput(in_cell_block=True, key="lat", value="hi")
        with self.assertRaises(ValueError):
            lattice = LatticeInput(in_cell_block=True, key="lat", value="5")
        lattices = [1, 2, Jump(), Jump()]
        card = Card(["Lat " + " ".join(list(map(str, lattices)))], BlockType.DATA)
        lattice = LatticeInput(card)
        for answer, lattice in zip(lattices, lattice._lattice):
            if isinstance(answer, int):
                self.assertEqual(answer, lattice.value)
            else:
                self.assertEqual(answer, lattice)
        with self.assertRaises(MalformedInputError):
            card = Card(["Lat 3"], BlockType.DATA)
            LatticeInput(card)
        with self.assertRaises(MalformedInputError):
            card = Card(["Lat str"], BlockType.DATA)
            LatticeInput(card)

    def test_lattice_setter(self):
        lattice = LatticeInput(in_cell_block=True, key="lat", value="1")
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
        lattice = LatticeInput(in_cell_block=True, key="lat", value="1")
        del lattice.lattice
        self.assertIsNone(lattice.lattice)

    def test_lattice_merge(self):
        lattice = LatticeInput(in_cell_block=True, key="lat", value="1")
        with self.assertRaises(MalformedInputError):
            lattice.merge(lattice)

    def test_lattice_cell_format(self):
        lattice = LatticeInput(in_cell_block=True, key="lat", value="1")
        output = lattice.format_for_mcnp_input(DEFAULT_VERSION)
        self.assertIn("LAT=1", output[0])
        lattice.lattice = None
        output = lattice.format_for_mcnp_input(DEFAULT_VERSION)
        self.assertEqual(output, [])

    def test_lattice_repr(self):
        lattice = LatticeInput(in_cell_block=True, key="lat", value="1")
        out = repr(lattice)
        self.assertIn("in_cell: True", out)
        self.assertIn("set_in_block: True", out)
        self.assertIn("Lattice_values : Lattice.HEXAHEDRA", out)


class TestFill(TestCase):
    def test_complex_transform_fill_init(self):
        fill = Fill(in_cell_block=True, key="*fill", value="1 (1.5 0.0 0.0)")
        self.assertTrue(fill.hidden_transform)
        self.assertIsNone(fill.universes)
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
        self.assertIsNone(fill.universe)
        self.assertEqual(fill.min_index[0], 0)
        self.assertEqual(fill.max_index[2], 1)
        answer = np.array([[[1, 2], [3, 4]], [[5, 6], [7, 8]]])
        self.assertTrue((fill.old_universe_numbers == answer).all())
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
        list_node = syntax_node.ListNode("num")
        list_node.append(syntax_node.ValueNode("5", float))
        value = syntax_node.SyntaxNode(
            "fill",
            {
                "classifier": "",
                "seperator": syntax_node.ValueNode("=", str),
                "data": list_node,
            },
        )
        fill = Fill(in_cell_block=True, key="fill", value=value)
        uni = mcnpy.Universe(6)
        fill.universe = uni
        self.assertEqual(fill.universe.number, uni.number)
        self.assertIsNone(fill.universes)
        fill.universe = None
        self.assertIsNone(fill.universe)
        fill.universe = uni
        del fill.universe
        self.assertIsNone(fill.universe)
        with self.assertRaises(TypeError):
            fill.universe = "hi"
        with self.assertRaises(TypeError):
            fill.multiple_universes = "hi"
        fill.multiple_universes = True
        with self.assertRaises(ValueError):
            fill.universe = uni

    def test_fill_universes_setter(self):
        input = Input(["1 0 -1 fill=0:1 0:1 0:1 1 2 3 4 5 6 7 8"], BlockType.CELL)
        cell = Cell(input)
        fill = cell.fill
        uni = mcnpy.Universe(10)
        fill_array = np.array([[[uni, uni], [uni, uni]], [[uni, uni], [uni, uni]]])
        fill.universes = fill_array
        self.assertTrue((fill.universes == fill_array).all())
        del fill.universes
        self.assertIsNone(fill.universes)
        with self.assertRaises(TypeError):
            fill.universes = "hi"
        fill.multiple_universes = False
        with self.assertRaises(ValueError):
            fill.universes = fill_array

    def test_fill_str(self):
        fill = Fill(in_cell_block=True, key="fill", value="0:1 0:1 0:1 1 2 3 4 5 6 7 8")
        output = str(fill)
        self.assertIn("Fill", output)
        output = repr(fill)
        self.assertIn("Fill", output)

    def test_fill_merge(self):
        card = Card(["FiLl 1 2 3 4"], BlockType.DATA)
        fill1 = Fill(card)
        fill2 = Fill(card)
        with self.assertRaises(MalformedInputError):
            fill1.merge(fill2)

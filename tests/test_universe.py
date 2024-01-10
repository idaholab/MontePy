# Copyright 2024, Battelle Energy Alliance, LLC All Rights Reserved.
from unittest import TestCase

import copy
from montepy.constants import DEFAULT_VERSION
from montepy.input_parser import syntax_node
import montepy
from montepy.cell import Cell
from montepy.constants import DEFAULT_VERSION
from montepy.errors import *
from montepy.input_parser.block_type import BlockType
from montepy.input_parser.mcnp_input import Input, Jump
from montepy.universe import Universe
from montepy.data_inputs.fill import Fill
from montepy.data_inputs.lattice import Lattice
from montepy.data_inputs.lattice_input import LatticeInput
from montepy.data_inputs.universe_input import UniverseInput
import numpy as np


class TestUniverseInput(TestCase):
    def setUp(self):
        list_node = syntax_node.ListNode("numbers")
        list_node.append(syntax_node.ValueNode("5", float))
        classifier = syntax_node.ClassifierNode()
        classifier.prefix = "u"
        tree = syntax_node.SyntaxNode(
            "lattice",
            {
                "classifier": classifier,
                "seperator": syntax_node.ValueNode("=", str),
                "data": list_node,
            },
        )
        self.tree = tree
        self.universe = UniverseInput(in_cell_block=True, key="u", value=tree)

    def test_universe_card_init(self):
        card = self.universe
        self.assertEqual(card.old_number, 5)
        self.assertTrue(not card.not_truncated)
        # test bad float
        with self.assertRaises(ValueError):
            tree = copy.deepcopy(self.tree)
            tree["data"].nodes.pop()
            tree["data"].append(syntax_node.ValueNode("5.5", float))
            card = UniverseInput(in_cell_block=True, key="U", value=tree)

        # test string
        with self.assertRaises(ValueError):
            tree["data"].nodes.pop()
            tree["data"].append(syntax_node.ValueNode("hi", str))
            card = UniverseInput(in_cell_block=True, key="U", value=tree)

        # test negative universe
        tree["data"].nodes.pop()
        tree["data"].append(syntax_node.ValueNode("-3", float))
        card = UniverseInput(in_cell_block=True, key="U", value=tree)
        self.assertEqual(card.old_number, 3)
        self.assertTrue(card.not_truncated)

        universes = [1, 2, 3]
        card = Input(["U " + " ".join(list(map(str, universes)))], BlockType.DATA)
        uni_card = UniverseInput(card)
        self.assertEqual(uni_card.old_numbers, universes)

        # test jump
        card = Input(["U J"], BlockType.DATA)
        uni_card = UniverseInput(card)
        self.assertEqual(uni_card.old_numbers[0], None)

        # test bad float
        with self.assertRaises(MalformedInputError):
            card = Input(["U 5.5"], BlockType.DATA)
            uni_card = UniverseInput(card)

        # test bad str
        with self.assertRaises(MalformedInputError):
            card = Input(["U hi"], BlockType.DATA)
            uni_card = UniverseInput(card)

        # test bad negative
        card = Input(["U -2"], BlockType.DATA)
        uni_card = UniverseInput(card)

    def test_str(self):
        card = copy.deepcopy(self.universe)
        uni = Universe(5)
        card.universe = uni
        output = str(card)
        self.assertIn("u=5", output)
        output = repr(card)
        self.assertIn("UNIVERSE", output)
        self.assertIn("set_in_block: True", output)
        self.assertIn("Universe : Universe(5)", output)

    def test_merge(self):
        card = copy.deepcopy(self.universe)
        with self.assertRaises(MalformedInputError):
            card.merge(card)

    def test_universe_setter(self):
        card = copy.deepcopy(self.universe)
        uni = Universe(5)
        card.universe = uni
        self.assertEqual(card.universe, uni)
        with self.assertRaises(TypeError):
            card.universe = 5

    def test_universe_truncate_setter(self):
        card = copy.deepcopy(self.universe)
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
        with self.assertRaises(TypeError):
            Universe("hi")
        with self.assertRaises(ValueError):
            Universe(-1)

    def test_number_setter(self):
        universe = Universe(5)
        universe.number = 10
        self.assertEqual(universe.number, 10)
        with self.assertRaises(TypeError):
            universe.number = "hi"
        with self.assertRaises(ValueError):
            universe.number = -1


class TestLattice(TestCase):
    def setUp(self):
        list_node = syntax_node.ListNode("numbers")
        list_node.append(syntax_node.ValueNode("1", float))
        classifier = syntax_node.ClassifierNode()
        classifier.prefix = "lat"
        tree = syntax_node.SyntaxNode(
            "lattice",
            {
                "classifier": classifier,
                "seperator": syntax_node.ValueNode("=", str),
                "data": list_node,
            },
        )
        self.tree = tree
        self.lattice = LatticeInput(in_cell_block=True, key="lat", value=tree)

    def test_lattice_init(self):
        lattice = self.lattice
        self.assertEqual(lattice.lattice, Lattice(1))
        tree = copy.deepcopy(self.tree)
        with self.assertRaises(ValueError):
            tree["data"].nodes.pop()
            tree["data"].append(syntax_node.ValueNode("hi", str))
            lattice = LatticeInput(in_cell_block=True, key="lat", value=tree)
        with self.assertRaises(ValueError):
            tree["data"].nodes.pop()
            tree["data"].append(syntax_node.ValueNode("5", float))
            lattice = LatticeInput(in_cell_block=True, key="lat", value=tree)
        lattices = [1, 2, None, None]
        input = Input(["Lat " + " ".join(list(map(str, lattices)))], BlockType.DATA)
        lattice = LatticeInput(input)
        for answer, lattice in zip(lattices, lattice._lattice):
            self.assertEqual(Lattice(answer), lattice.value)
        with self.assertRaises(MalformedInputError):
            card = Input(["Lat 3"], BlockType.DATA)
            LatticeInput(card)
        with self.assertRaises(MalformedInputError):
            card = Input(["Lat str"], BlockType.DATA)
            LatticeInput(card)

    def test_lattice_setter(self):
        lattice = copy.deepcopy(self.lattice)
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
        lattice = self.lattice
        del lattice.lattice
        self.assertIsNone(lattice.lattice)

    def test_lattice_merge(self):
        lattice = self.lattice
        with self.assertRaises(MalformedInputError):
            lattice.merge(lattice)

    def test_lattice_cell_format(self):
        lattice = self.lattice
        output = lattice.format_for_mcnp_input(DEFAULT_VERSION)
        self.assertIn("lat=1", output[0])
        lattice.lattice = None
        output = lattice.format_for_mcnp_input(DEFAULT_VERSION)
        self.assertEqual(output, [])

    def test_lattice_repr(self):
        lattice = self.lattice
        out = repr(lattice)
        self.assertIn("in_cell: True", out)
        self.assertIn("set_in_block: True", out)
        self.assertIn("Lattice_values : Lattice.HEXAHEDRA", out)


class TestFill(TestCase):
    def setUp(self):
        list_node = syntax_node.ListNode("num")
        list_node.append(syntax_node.ValueNode("5", float))
        tree = syntax_node.SyntaxNode(
            "fill",
            {
                "classifier": "",
                "seperator": syntax_node.ValueNode("=", str),
                "data": list_node,
            },
        )
        self.tree = tree
        self.simple_fill = Fill(in_cell_block=True, key="fill", value=tree)

    def test_complex_transform_fill_init(self):
        input = Input(["1 0 -1 *fill=1 (1.5 0.0 0.0)"], BlockType.CELL)
        cell = Cell(input)
        fill = cell.fill
        self.assertTrue(fill.hidden_transform)
        self.assertIsNone(fill.universes)
        self.assertEqual(fill.old_universe_number, 1)
        self.assertEqual(len(fill.transform.displacement_vector), 3)
        self.assertTrue(fill.transform.is_in_degrees)
        input = Input(["1 0 -1 fill=1 (1.5 0.0 0.0)"], BlockType.CELL)
        cell = Cell(input)
        fill = cell.fill
        self.assertTrue(not fill.transform.is_in_degrees)
        input = Input(["1 0 -1 fill=5 (3)"], BlockType.CELL)
        cell = Cell(input)
        fill = cell.fill
        self.assertTrue(not fill.hidden_transform)
        self.assertEqual(fill.old_universe_number, 5)
        self.assertEqual(fill.old_transform_number, 3)
        # test bad string
        with self.assertRaises(ValueError):
            input = Input(["1 0 -1 fill=hi"], BlockType.CELL)
            cell = Cell(input)
            fill = cell.fill
        with self.assertRaises(ValueError):
            input = Input(["1 0 -1 fill=1 (hi)"], BlockType.CELL)
            cell = Cell(input)
            fill = cell.fill
        # test negative universe
        with self.assertRaises(ValueError):
            input = Input(["1 0 -1 fill=-5"], BlockType.CELL)
            cell = Cell(input)
            fill = cell.fill
        with self.assertRaises(ValueError):
            input = Input(["1 0 -1 fill=5 (-5)"], BlockType.CELL)
            cell = Cell(input)
            fill = cell.fill
        with self.assertRaises(ValueError):
            input = Input(["1 0 -1 fill=5 1 0 0"], BlockType.CELL)
            cell = Cell(input)
            fill = cell.fill

    def test_complicated_lattice_fill_init(self):
        input = Input(["1 0 -1 fill=0:1 0:1 0:1 1 2 3 4 5 6 7 8"], BlockType.CELL)
        cell = Cell(input)
        fill = cell.fill
        self.assertIsNone(fill.universe)
        self.assertEqual(fill.min_index[0], 0)
        self.assertEqual(fill.max_index[2], 1)
        answer = np.array([[[1, 2], [3, 4]], [[5, 6], [7, 8]]])
        self.assertTrue((fill.old_universe_numbers == answer).all())
        # test string universe
        with self.assertRaises(ValueError):
            input = Input(["1 0 -1 fill=0:1 0:1 0:1 hi"], BlockType.CELL)
            cell = Cell(input)
            fill = cell.fill
        # test string index
        with self.assertRaises(ValueError):
            input = Input(["1 0 -1 fill=0:1 hi:1 0:1 hi"], BlockType.CELL)
            cell = Cell(input)
            fill = cell.fill
        # test negative universe
        with self.assertRaises(ValueError):
            input = Input(["1 0 -1 fill=0:1 0:1 0:1 -1"], BlockType.CELL)
            cell = Cell(input)
            fill = cell.fill
        # test inverted bounds
        with self.assertRaises(ValueError):
            input = Input(["1 0 -1 fill=0:1 1:0 0:1 1 2 3 4 5 6 7 8"], BlockType.CELL)
            cell = Cell(input)
            fill = cell.fill
        # test float bounds
        with self.assertRaises(ValueError):
            input = Input(["1 0 -1 fill=0:1 0:1.5 0:1 1 2 3 4 5 6 7 8"], BlockType.CELL)
            cell = Cell(input)
            fill = cell.fill

    def test_data_fill_init(self):
        card = Input(["FiLl 1 2 3 4"], BlockType.DATA)
        fill = Fill(card)
        answer = [1, 2, 3, 4]
        self.assertEqual(fill.old_universe_numbers, answer)
        # jump
        card = Input(["FiLl 1 2J 4"], BlockType.DATA)
        fill = Fill(card)
        answer = [1, None, None, 4]
        self.assertEqual(fill.old_universe_numbers, answer)
        # test negative universe
        with self.assertRaises(MalformedInputError):
            card = Input(["FiLl 1 -2 3 4"], BlockType.DATA)
            fill = Fill(card)
        # test string universe
        with self.assertRaises(MalformedInputError):
            card = Input(["FiLl 1 foo"], BlockType.DATA)
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
        fill = copy.deepcopy(self.simple_fill)
        uni = montepy.Universe(6)
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
        uni = montepy.Universe(10)
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
        input = Input(["1 0 -1 fill=0:1 0:1 0:1 1 2 3 4 5 6 7 8"], BlockType.CELL)
        cell = Cell(input)
        fill = cell.fill
        output = str(fill)
        self.assertIn("Fill", output)
        output = repr(fill)
        self.assertIn("Fill", output)

    def test_fill_merge(self):
        card = Input(["FiLl 1 2 3 4"], BlockType.DATA)
        fill1 = Fill(card)
        fill2 = Fill(card)
        with self.assertRaises(MalformedInputError):
            fill1.merge(fill2)

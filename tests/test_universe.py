from unittest import TestCase

import mcnpy
from mcnpy.cell import Cell
from mcnpy.errors import *
from mcnpy.input_parser.block_type import BlockType
from mcnpy.input_parser.mcnp_input import Card, Comment, Jump
from mcnpy.universe import Universe
from mcnpy.data_cards.universe_card import UniverseCard


class TestUniverseCard(TestCase):
    def test_universe_init(self):
        card = UniverseCard(in_cell_block=True, key="U", value="5")
        self.assertEqual(card.old_number, 5)
        # test bad float
        with self.assertRaises(ValueError):
            card = UniverseCard(in_cell_block=True, key="U", value="5.5")

        # test string
        with self.assertRaises(ValueError):
            card = UniverseCard(in_cell_block=True, key="U", value="hi")

        # test negative universe
        with self.assertRaises(ValueError):
            card = UniverseCard(in_cell_block=True, key="U", value="-3")
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
        with self.assertRaises(MalformedInputError):
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


class TestUniverse(TestCase):
    pass


class TestLattice(TestCase):
    pass


class TestFill(TestCase):
    pass

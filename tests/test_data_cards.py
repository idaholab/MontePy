from unittest import TestCase

import mcnpy

from mcnpy.cell_data_control import CellDataPrintController
from mcnpy.data_cards.data_card import DataCard
from mcnpy.data_cards import material, thermal_scattering, transform
from mcnpy.data_cards.data_parser import parse_data
from mcnpy.input_parser.mcnp_input import Card, Comment
from mcnpy.input_parser.block_type import BlockType


class testDataCardClass(TestCase):
    def test_data_card_init(self):
        in_str = "m1 1001.80c 1.0"
        input_card = Card([in_str], BlockType.DATA)
        comment = Comment(["C foo", "c bar"], ["foo", "bar"])
        data_card = DataCard(input_card, comment)
        words = in_str.split()
        for i, word in enumerate(data_card.words):
            self.assertEqual(word, words[i])
        self.assertEqual(comment, data_card.comments[0])

    def test_data_card_empty_constructor(self):
        card = DataCard()
        self.assertIsInstance(card.words, list)

    def test_data_card_str(self):
        in_str = "m1 1001.80c 1.0"
        input_card = Card([in_str], BlockType.DATA)
        data_card = DataCard(input_card)
        self.assertEqual(str(data_card), "DATA CARD: " + str(in_str.split()))

    def test_data_card_format_mcnp(self):
        in_str = "m1 1001.80c 1.0"
        input_card = Card([in_str], BlockType.DATA)
        comment = Comment(["c foo", "c bar"], ["foo", "bar"])
        data_card = DataCard(input_card, comment)
        answer = ["C foo", "C bar", "m1 1001.80c 1.0"]
        output = data_card.format_for_mcnp_input((6, 2, 0))
        self.assertEqual(len(answer), len(output))
        for i, line in enumerate(output):
            self.assertEqual(answer[i], line)

    def test_comment_setter(self):
        in_str = "m1 1001.80c 1.0"
        input_card = Card([in_str], BlockType.DATA)
        comment = Comment(["c foo", "c bar"], ["foo", "bar"])
        data_card = DataCard(input_card)
        data_card.comment = comment
        self.assertEqual(comment, data_card.comment)

    def test_data_parser(self):
        identifiers = {
            "m235": material.Material,
            "mt235": thermal_scattering.ThermalScatteringLaw,
            "tr601": transform.Transform,
            "ksrc": DataCard,
        }
        in_strs = {
            "m235": "m235 1001.80c 1.0",
            "mt235": "mt235 grph.29t",
            "tr601": "tr601 0.0 0.0 10.",
            "ksrc": "ksrc 1.0 0.0 0.0",
        }

        for identifier, w in in_strs.items():
            for ident in [identifier, identifier.upper()]:
                input_card = Card([w], BlockType.DATA)
                card = parse_data(input_card)
                self.assertIsInstance(card, identifiers[ident.lower()])

    def test_data_card_words_setter(self):
        in_str = "IMP:N 1 1"
        input_card = Card([in_str], BlockType.DATA)
        input_card = DataCard(input_card)
        new_words = input_card.words + ["0"]
        input_card.words = new_words
        self.assertEqual(new_words, input_card.words)
        with self.assertRaises(TypeError):
            input_card.words = 5
        with self.assertRaises(TypeError):
            input_card.words = [5]

    def test_data_card_mutate_print(self):
        in_str = "IMP:N 1 1"
        input_card = Card([in_str], BlockType.DATA)
        input_card = DataCard(input_card)
        input_card._mutated = True
        output = input_card.format_for_mcnp_input((6, 2, 0))
        self.assertEqual(output, [in_str])

    def test_print_in_data_block(self):
        cell_controller = CellDataPrintController()
        cell_controller["imp"] = True
        cell_controller["Imp"] = True
        self.assertTrue(cell_controller["IMP"])
        with self.assertRaises(TypeError):
            cell_controller[5] = True
        with self.assertRaises(TypeError):
            cell_controller["imp"] = 5
        with self.assertRaises(TypeError):
            cell_controller[5]
        with self.assertRaises(KeyError):
            cell_controller["a"] = True
        with self.assertRaises(KeyError):
            cell_controller["a"]

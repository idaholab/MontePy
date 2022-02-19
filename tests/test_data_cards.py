from unittest import TestCase

import mcnpy

from mcnpy.data_cards.data_card import DataCard
from mcnpy.data_cards import material, thermal_scattering, transform
from mcnpy.data_cards.data_parser import parse_data
from mcnpy.input_parser.mcnp_input import Card, Comment
from mcnpy.input_parser.block_type import BlockType


class testDataCardClass(TestCase):
    def test_data_card_init(self):
        words = ["m1", "1001.80c", "1.0"]
        input_card = Card(BlockType.DATA, words)
        comment = Comment(["foo", "bar"])
        data_card = DataCard(input_card, comment)
        for i, word in enumerate(data_card.words):
            self.assertEqual(word, words[i])
        self.assertEqual(comment, data_card.comment)

    def test_data_card_str(self):
        words = ["m1", "1001.80c", "1.0"]
        input_card = Card(BlockType.DATA, words)
        data_card = DataCard(input_card)
        self.assertEqual(str(data_card), "DATA CARD: " + str(words))

    def test_data_card_format_mcnp(self):
        words = ["m1", "1001.80c", "1.0"]
        input_card = Card(BlockType.DATA, words)
        comment = Comment(["foo", "bar"])
        data_card = DataCard(input_card, comment)
        answer = ["C foo", "C bar", "m1 1001.80c 1.0"]
        output = data_card.format_for_mcnp_input((6.2, 0))
        self.assertEqual(len(answer), len(output))
        for i, line in enumerate(output):
            self.assertEqual(answer[i], line)

    def test_comment_setter(self):
        words = ["m1", "1001.80c", "1.0"]
        input_card = Card(BlockType.DATA, words)
        comment = Comment(["foo", "bar"])
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
        words = {
            "m235": ["m235", "1001.80c", "1.0"],
            "mt235": ["mt235", "grph.29t"],
            "tr601": ["tr601", "0.0", "0.0", "10."],
            "ksrc": ["ksrc", "1.0", "0.0", "0.0"],
        }

        for identifier, w in words.items():
            for ident in [identifier, identifier.upper()]:
                input_card = Card(BlockType.DATA, w)
                card = parse_data(input_card)
                self.assertIsInstance(card, identifiers[ident])

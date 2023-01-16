from unittest import TestCase

import mcnpy

from mcnpy.cell_data_control import CellDataPrintController
from mcnpy.data_inputs.data_input import DataInput
from mcnpy.data_inputs import material, thermal_scattering, transform, volume
from mcnpy.data_inputs.data_parser import parse_data
from mcnpy.errors import *
from mcnpy.input_parser.mcnp_input import Input, Comment, Jump
from mcnpy.input_parser.block_type import BlockType
from mcnpy.mcnp_problem import MCNP_Problem


class testDataInputClass(TestCase):
    def test_data_card_init(self):
        in_str = "m1 1001.80c 1.0"
        input_card = Input([in_str], BlockType.DATA)
        comment = Comment(["C foo", "c bar"], ["foo", "bar"])
        data_card = DataInput(input_card, comment)
        words = in_str.split()
        for i, word in enumerate(data_card.words):
            self.assertEqual(word, words[i])
        self.assertEqual(comment, data_card.comments[0])

    def test_data_card_empty_constructor(self):
        card = DataInput()
        self.assertIsInstance(card.words, list)

    def test_data_card_str(self):
        in_str = "m1 1001.80c 1.0"
        input_card = Input([in_str], BlockType.DATA)
        data_card = DataInput(input_card)
        self.assertEqual(str(data_card), "DATA INPUT: " + str(in_str.split()))

    def test_data_card_format_mcnp(self):
        in_str = "m1 1001.80c 1.0"
        input_card = Input([in_str], BlockType.DATA)
        comment = Comment(["c foo", "c bar"], ["foo", "bar"])
        data_card = DataInput(input_card, comment)
        answer = ["C foo", "C bar", "m1 1001.80c 1.0"]
        output = data_card.format_for_mcnp_input((6, 2, 0))
        self.assertEqual(len(answer), len(output))
        for i, line in enumerate(output):
            self.assertEqual(answer[i], line)

    def test_comment_setter(self):
        in_str = "m1 1001.80c 1.0"
        input_card = Input([in_str], BlockType.DATA)
        comment = Comment(["c foo", "c bar"], ["foo", "bar"])
        data_card = DataInput(input_card)
        data_card.comment = comment
        self.assertEqual(comment, data_card.comment)

    def test_data_parser(self):
        identifiers = {
            "m235": material.Material,
            "mt235": thermal_scattering.ThermalScatteringLaw,
            "tr601": transform.Transform,
            "ksrc": DataInput,
        }
        in_strs = {
            "m235": "m235 1001.80c 1.0",
            "mt235": "mt235 grph.29t",
            "tr601": "tr601 0.0 0.0 10.",
            "ksrc": "ksrc 1.0 0.0 0.0",
        }

        for identifier, w in in_strs.items():
            for ident in [identifier, identifier.upper()]:
                input_card = Input([w], BlockType.DATA)
                card = parse_data(input_card)
                self.assertIsInstance(card, identifiers[ident.lower()])

    def test_data_card_words_setter(self):
        in_str = "IMP:N 1 1"
        input_card = Input([in_str], BlockType.DATA)
        input_card = DataInput(input_card)
        new_words = input_card.words + ["0"]
        input_card.words = new_words
        self.assertEqual(new_words, input_card.words)
        with self.assertRaises(TypeError):
            input_card.words = 5
        with self.assertRaises(TypeError):
            input_card.words = [5]

    def test_data_card_mutate_print(self):
        in_str = "IMP:N 1 1"
        input_card = Input([in_str], BlockType.DATA)
        input_card = DataInput(input_card)
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

    def test_volume_init_cell(self):
        vol = 1.0
        card = volume.Volume(key="VoL", value=str(vol), in_cell_block=True)
        self.assertEqual(card.volume, vol)
        self.assertTrue(card.in_cell_block)
        self.assertTrue(card.set_in_cell_block)
        self.assertTrue(not card.is_mcnp_calculated)
        self.assertTrue(card.set)
        card = volume.Volume(in_cell_block=True)
        self.assertTrue(card.is_mcnp_calculated)
        with self.assertRaises(ValueError):
            card = volume.Volume(key="VoL", value="s", in_cell_block=True)
        with self.assertRaises(ValueError):
            card = volume.Volume(key="VoL", value="-1", in_cell_block=True)

    def test_volume_init_data(self):
        in_str = "VOL 1 1 2J 0"
        input_card = Input([in_str], BlockType.DATA)
        vol_card = parse_data(input_card)
        answers = [1.0, 1.0, Jump, Jump, 0.0]
        for i, vol in enumerate(vol_card._volume):
            if isinstance(answers[i], float):
                self.assertAlmostEqual(vol, answers[i])
            else:
                self.assertIsInstance(vol, Jump)
        in_str = "VOL NO 1 1 2J 0"
        input_card = Input([in_str], BlockType.DATA)
        vol_card = parse_data(input_card)
        self.assertTrue(not vol_card.is_mcnp_calculated)
        # invalid number
        in_str = "VOL NO s 1 2J 0"
        input_card = Input([in_str], BlockType.DATA)
        with self.assertRaises(MalformedInputError):
            vol_card = parse_data(input_card)
        # negative volume
        in_str = "VOL NO -1 1 2J 0"
        input_card = Input([in_str], BlockType.DATA)
        with self.assertRaises(MalformedInputError):
            vol_card = parse_data(input_card)

    def test_volumes_for_only_some_cells(self):
        cells = [
            mcnpy.Cell(Input([f"{i + 1} 0 -1 u=3"], BlockType.CELL)) for i in range(10)
        ]
        prob = MCNP_Problem(None)
        prob.cells = cells
        vol_card = Input(["VOL 1 1 2 3 5"], BlockType.DATA)
        vol_data = volume.Volume(vol_card, in_cell_block=False)
        vol_data.link_to_problem(prob)
        vol_data.push_to_cells()
        is_set = [cell.volume_is_set for cell in cells]
        reference = [True] * 5 + [False] * 5
        self.assertListEqual(is_set, reference)

    def test_volume_setter(self):
        vol = 1.0
        card = volume.Volume(key="VoL", value=str(vol), in_cell_block=True)
        card.volume = 5.0
        self.assertEqual(card.volume, 5.0)
        with self.assertRaises(TypeError):
            card.volume = "hi"
        with self.assertRaises(ValueError):
            card.volume = -5.0

    def test_volume_deleter(self):
        vol = 1.0
        card = volume.Volume(key="VoL", value=str(vol), in_cell_block=True)
        del card.volume
        self.assertIsNone(card.volume)

    def test_volume_merge(self):
        vol = 1.0
        card = volume.Volume(key="VoL", value=str(vol), in_cell_block=True)
        card2 = volume.Volume(key="VoL", value=str(vol), in_cell_block=True)
        with self.assertRaises(MalformedInputError):
            card.merge(card2)

    def test_volume_repr(self):
        vol = 1.0
        card = volume.Volume(key="VoL", value=str(vol), in_cell_block=True)
        self.assertIn("VOLUME", repr(card))

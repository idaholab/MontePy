# Copyright 2024, Battelle Energy Alliance, LLC All Rights Reserved.
import montepy
from montepy.errors import *
import os

from unittest import TestCase


class EdgeCaseTests(TestCase):
    def test_complement_edge_case(self):
        capsule = montepy.read_input("tests/inputs/test_complement_edge.imcnp")
        complementing_cell = capsule.cells[61482]
        self.assertEqual(len(complementing_cell.complements), 2)

    def test_surface_edge_case(self):
        capsule = montepy.read_input("tests/inputs/test_complement_edge.imcnp")
        problem_cell = capsule.cells[61441]
        self.assertEqual(len(set(problem_cell.surfaces)), 6)

    def test_interp_surface_edge_case(self):
        capsule = montepy.read_input("tests/inputs/test_interp_edge.imcnp")
        self.assertEqual(len(capsule.cells[10214].surfaces), 4)

    def test_excess_mt(self):
        with self.assertRaises(MalformedInputError):
            montepy.read_input(os.path.join("tests", "inputs", "test_excess_mt.imcnp"))

    def test_missing_mat_for_mt(self):
        with self.assertRaises(MalformedInputError):
            montepy.read_input(
                os.path.join("tests", "inputs", "test_missing_mat_for_mt.imcnp")
            )

    def test_orphaning_mt(self):
        problem = montepy.read_input(os.path.join("tests", "inputs", "test.imcnp"))
        card = montepy.input_parser.mcnp_input.Card(
            ["MT5 lwtr.01t"],
            montepy.input_parser.block_type.BlockType.DATA,
        )
        problem.data_cards.append(montepy.data_cards.data_parser.parse_data(card))
        try:
            with self.assertRaises(MalformedInputError):
                problem.write_to_file("out")
        finally:
            if os.path.exists("out"):
                pass
                os.remove("out")

    def test_shortcuts_in_special_comment(self):
        in_str = "fc247 experiment in I24 Cell Specific Heating"
        card = montepy.input_parser.mcnp_input.Card(
            [in_str], montepy.input_parser.block_type.BlockType.DATA
        )
        self.assertEqual(card.words, in_str.split())
        in_str = in_str.replace("fc247", "sc247")
        card = montepy.input_parser.mcnp_input.Card(
            [in_str], montepy.input_parser.block_type.BlockType.DATA
        )
        self.assertEqual(card.words, in_str.split())

    def test_long_lines(self):
        with self.assertWarns(montepy.errors.LineOverRunWarning):
            problem = montepy.read_input(
                "tests/inputs/test_long_lines.imcnp", (5, 1, 60)
            )
            comment = problem.cells[1].comments[0]
            self.assertTrue(len(comment.lines[0]) <= 80)
            self.assertEqual(len(problem.surfaces), 3)

    def test_confused_key_word(self):
        # this came from Andrew Bascom's Issue #99
        in_strs = [
            "29502 30002 2.53E-02 ( 500020 -500023  -500060 ):  $ Outer Capsule Lower Endcap",
            "          ( 500023 -500024 500062 -500060 ):  $ Outer Capsule Lower Endcap",
            "          ( 500024 -500025 500062 -500061 )  $ Outer Capsule Lower Endcap",
            "                u= 106 $ Outer Capsule Lower Endcap",
        ]
        input = montepy.input_parser.mcnp_input.Card(
            in_strs, montepy.input_parser.block_type.BlockType.CELL
        )
        cell = montepy.Cell(input)
        self.assertNotIn("", cell.parameters)
        self.assertEqual(len(cell.parameters), 0)

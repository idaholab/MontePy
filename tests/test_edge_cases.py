import mcnpy
from mcnpy.errors import *
import os

from unittest import TestCase


class EdgeCaseTests(TestCase):
    def test_complement_edge_case(self):
        capsule = mcnpy.read_input("tests/inputs/test_complement_edge.imcnp")
        complementing_cell = capsule.cells[61482]
        self.assertEqual(len(complementing_cell.complements), 2)

    def test_surface_edge_case(self):
        capsule = mcnpy.read_input("tests/inputs/test_complement_edge.imcnp")
        problem_cell = capsule.cells[61441]
        self.assertEqual(len(set(problem_cell.surfaces)), 6)

    def test_interp_surface_edge_case(self):
        capsule = mcnpy.read_input("tests/inputs/test_interp_edge.imcnp")
        self.assertEqual(len(capsule.cells[10214].surfaces), 4)

    def test_excess_mt(self):
        with self.assertRaises(MalformedInputError):
            mcnpy.read_input(os.path.join("tests", "inputs", "test_excess_mt.imcnp"))

    def test_missing_mat_for_mt(self):
        with self.assertRaises(MalformedInputError):
            mcnpy.read_input(
                os.path.join("tests", "inputs", "test_missing_mat_for_mt.imcnp")
            )

    def test_orphaning_mt(self):
        problem = mcnpy.read_input(os.path.join("tests", "inputs", "test.imcnp"))
        card = mcnpy.input_parser.mcnp_input.Input(
            ["MT5 lwtr.01t"],
            mcnpy.input_parser.block_type.BlockType.DATA,
        )
        problem.data_inputs.append(mcnpy.data_inputs.data_parser.parse_data(card))
        try:
            with self.assertRaises(MalformedInputError):
                problem.write_to_file("out")
        finally:
            if os.path.exists("out"):
                pass
                os.remove("out")

    def test_shortcuts_in_special_comment(self):
        in_str = "fc247 experiment in I24 Cell Specific Heating"
        card = mcnpy.input_parser.mcnp_input.Input(
            [in_str], mcnpy.input_parser.block_type.BlockType.DATA
        )
        self.assertEqual(card.input_lines, [in_str])
        in_str = in_str.replace("fc247", "sc247")
        card = mcnpy.input_parser.mcnp_input.Input(
            [in_str], mcnpy.input_parser.block_type.BlockType.DATA
        )
        self.assertEqual(card.input_lines, [in_str])

    def test_long_lines(self):
        with self.assertWarns(mcnpy.errors.LineOverRunWarning):
            problem = mcnpy.read_input("tests/inputs/test_long_lines.imcnp", (5, 1, 60))
            comment = problem.cells[1].comments[0]
            self.assertTrue(len(comment.contents[0]) <= 80)
            self.assertEqual(len(problem.surfaces), 3)

    def test_confused_key_word(self):
        # this came from Andrew Bascom's Issue #99
        in_strs = [
            "29502 30002 2.53E-02 ( 500020 -500023  -500060 ):  $ Outer Capsule Lower Endcap",
            "          ( 500023 -500024 500062 -500060 ):  $ Outer Capsule Lower Endcap",
            "          ( 500024 -500025 500062 -500061 )  $ Outer Capsule Lower Endcap",
            "                u= 106 $ Outer Capsule Lower Endcap",
        ]
        input = mcnpy.input_parser.mcnp_input.Input(
            in_strs, mcnpy.input_parser.block_type.BlockType.CELL
        )
        cell = mcnpy.Cell(input)
        self.assertNotIn("", cell.parameters)
        print(cell.parameters)
        allowed_keys = {"u", "imp:n", "fill", "lat", "vol"}
        self.assertEqual(len(cell.parameters), 5)
        self.assertEqual(cell.parameters.nodes.keys(), allowed_keys)

    def test_confused_union_geometry(self):
        # based on issue #122
        in_strs = [
            "9800     10    -0.123000 +101 -200 -905 +213 (-216:+217)",
        ]
        input = mcnpy.input_parser.mcnp_input.Input(
            in_strs, mcnpy.input_parser.block_type.BlockType.CELL
        )
        cell = mcnpy.Cell(input)

    def test_confused_trcl(self):
        for line in [
            "340 0 (94 -209 -340) fill=2 trcl=(0 0 0  0.7071 -0.7071 0  0.7071 0.7071 0  0 0 1)",
            "340 0 (94 -209 -340) fill=2 trcl=(0 0 0  0.7071 -0.7071 0  0.7071 0.7071 0  0 0 1)  $ Comment",
        ]:
            input = mcnpy.input_parser.mcnp_input.Input(
                [line],
                mcnpy.input_parser.block_type.BlockType.CELL,
            )
            cell = mcnpy.Cell(input)

    def test_space_after_equals(self):
        lines = [
            "35000 3690   0.01000    35100   -35105",
            "                        35110   -35115",
            "                        35150   -35155   U = 35100",
        ]
        input = mcnpy.input_parser.mcnp_input.Input(
            lines,
            mcnpy.input_parser.block_type.BlockType.CELL,
        )
        cell = mcnpy.Cell(input)

    def test_interpolate_geometry(self):
        lines = [
            "10234   30  1.2456780      -3103  3104 -3133  3136",
            "                            3201  15i   3217",
            "                            u=20",
        ]
        input = mcnpy.input_parser.mcnp_input.Input(
            lines,
            mcnpy.input_parser.block_type.BlockType.CELL,
        )
        cell = mcnpy.Cell(input)

# Copyright 2024 - 2025, Battelle Energy Alliance, LLC All Rights Reserved.

import copy
import io
import numpy as np
import pytest
import os
from pathlib import Path
import montepy
from montepy.exceptions import *


def test_complement_edge_case():
    capsule = montepy.read_input("tests/inputs/test_complement_edge.imcnp")
    complementing_cell = capsule.cells[61482]
    assert len(complementing_cell.complements) == 2


def test_surface_edge_case():
    capsule = montepy.read_input("tests/inputs/test_complement_edge.imcnp")
    problem_cell = capsule.cells[61441]
    assert len(problem_cell.surfaces) == 6


def test_interp_surface_edge_case():
    capsule = montepy.read_input("tests/inputs/test_interp_edge.imcnp")
    assert len(capsule.cells[10214].surfaces) == 4


def test_excess_mt():
    with pytest.raises(MalformedInputError):
        montepy.read_input(os.path.join("tests", "inputs", "test_excess_mt.imcnp"))


def test_missing_mat_for_mt():
    with pytest.raises(MalformedInputError):
        montepy.read_input(
            os.path.join("tests", "inputs", "test_missing_mat_for_mt.imcnp")
        )


def test_orphaning_mt():
    problem = montepy.read_input(os.path.join("tests", "inputs", "test.imcnp"))
    input_obj = montepy.input_parser.mcnp_input.Input(
        ["MT5 lwtr.01t"],
        montepy.input_parser.block_type.BlockType.DATA,
    )
    problem.data_inputs.append(montepy.data_inputs.data_parser.parse_data(input_obj))
    with io.StringIO() as stream:
        with pytest.raises(MalformedInputError):
            problem.write_problem(stream)


def test_shortcuts_in_special_comment():
    in_str = "fc247 experiment in I24 Cell Specific Heating"
    input_obj = montepy.input_parser.mcnp_input.Input(
        [in_str], montepy.input_parser.block_type.BlockType.DATA
    )
    assert input_obj.input_lines == [in_str]
    in_str = in_str.replace("fc247", "sc247")
    input_obj = montepy.input_parser.mcnp_input.Input(
        [in_str], montepy.input_parser.block_type.BlockType.DATA
    )
    assert input_obj.input_lines == [in_str]


def test_long_lines():
    with pytest.warns(montepy.exceptions.LineOverRunWarning):
        problem = montepy.read_input("tests/inputs/test_long_lines.imcnp", (5, 1, 60))
        comment = problem.cells[1].comments[0]
        assert len(comment.contents[0]) <= 80
        assert len(problem.surfaces) == 3


def test_confused_key_word():
    # this came from Andrew Bascom's Issue #99
    in_strs = [
        "29502 30002 2.53E-02 ( 500020 -500023  -500060 ):  $ Outer Capsule Lower Endcap",
        "          ( 500023 -500024 500062 -500060 ):  $ Outer Capsule Lower Endcap",
        "          ( 500024 -500025 500062 -500061 )  $ Outer Capsule Lower Endcap",
        "                u= 106 $ Outer Capsule Lower Endcap",
    ]
    input_obj = montepy.input_parser.mcnp_input.Input(
        in_strs, montepy.input_parser.block_type.BlockType.CELL
    )
    cell = montepy.Cell(input_obj)
    assert "" not in cell.parameters
    print(cell.parameters)
    allowed_keys = {"u", "imp:n", "fill", "lat", "vol"}
    assert len(cell.parameters) == 5
    assert set(cell.parameters.nodes.keys()) == allowed_keys


def test_void_cell_set_material():
    in_strs = ["2 0 -63 -62 64  imp:n=1 $ COBALT_TARGET_PELLET2"]
    input_obj = montepy.input_parser.mcnp_input.Input(
        in_strs, montepy.input_parser.block_type.BlockType.CELL
    )
    base_cell = montepy.Cell(input_obj)
    in_strs = ["m171 1001.80c 1E-24"]
    input_obj = montepy.input_parser.mcnp_input.Input(
        in_strs, montepy.input_parser.block_type.BlockType.CELL
    )
    material = montepy.data_inputs.material.Material(input_obj)
    base_cell.material = material
    for dens_value in {5.0, 1.235e-6, 1.245e23}:
        cell = copy.deepcopy(base_cell)
        print(dens_value)
        cell.mass_density = dens_value
        with pytest.warns(LineExpansionWarning):
            output = cell.format_for_mcnp_input((6, 2, 0))
        print(output)
        parts = output[0].split()
        assert abs(float(parts[2]) + dens_value) < 1e-9


def test_geometry_comments():
    in_strs = """21073   130 0.010000   (-11516    97  -401 )  $ C 1 Lower water
      :(-11526    97  -401 )  $ C 2 Lower water
      :(-11536    97  -401 )  $ C 3 Lower water
      :(-11546    97  -401 )  $ C 4 Lower water
      :(-11556    97  -401 )  $ C 5 Lower water
      :(-11576    97  -401 ) imp:n=1 $ C 7 Lower water""".split(
        "\n"
    )
    input_obj = montepy.input_parser.mcnp_input.Input(
        in_strs, montepy.input_parser.block_type.BlockType.CELL
    )
    cell = montepy.Cell(input_obj)
    # this step caused an error for #163
    cell.comments
    cell._tree.format()


def test_bad_read():
    montepy.read_input(os.path.join("tests", "inputs", "readEdgeCase.imcnp"))


def test_material_float():
    in_strs = ["m171 1001.80c 1E-24"]
    input_obj = montepy.input_parser.mcnp_input.Input(
        in_strs, montepy.input_parser.block_type.BlockType.CELL
    )
    _ = montepy.data_inputs.material.Material(input_obj)


@pytest.mark.parametrize(
    "lines",
    [
        # issue #122
        [
            "9800     10    -0.123000 +101 -200 -905 +213 (-216:+217)",
        ],
        [
            "340 0 (94 -209 -340) fill=2 trcl=(0 0 0  0.7071 -0.7071 0  0.7071 0.7071 0  0 0 1)",
        ],
        [
            "340 0 (94 -209 -340) fill=2 trcl=(0 0 0  0.7071 -0.7071 0  0.7071 0.7071 0  0 0 1)  $ Comment",
        ],
        [
            "35000 3690   0.01000    35100   -35105",
            "                        35110   -35115",
            "                        35150   -35155   U = 35100",
        ],
        [
            "10234   30  1.2456780      -3103  3104 -3133  3136",
            "                            3201  15i   3217",
            "                            u=20",
        ],
        # issue #461
        [
            "43    0",
            "      (                 $ a dollar comment here",
            "        -1 2",
            "      )",
            "      IMP:N=1.000000 IMP:P=1.000000",
        ],
        [
            "1    0  3 -2",
            "    IMP:N=1.000000  IMP:P=1.000000",
            "    *FILL=1  ( 0.000        0.000  0.000",
            "           30.000      120.000 90.000",
            "           60.000       30.000 90.000",
            "           90.000       90.000  0.000)",
        ],
    ],
)
def test_complex_cell_parsing(lines):
    input = montepy.input_parser.mcnp_input.Input(
        lines,
        montepy.input_parser.block_type.BlockType.CELL,
    )
    montepy.Cell(input)


def test_the_dissapearing_parens():
    in_file = os.path.join("tests", "inputs", "test_paren_groups.imcnp")
    problem = montepy.read_input(in_file)
    parens_count = 0
    with open(in_file, "r") as fh:
        for line in fh:
            parens_count += line.count("(") + line.count(")")
    fh = io.StringIO()
    problem.write_problem(fh)
    new_parens_count = 0
    fh.seek(0)
    with open(in_file, "r") as gold_fh:
        for line, gold_line in zip(fh, gold_fh):
            print(line.rstrip())
            new_parens_count += line.count("(") + line.count(")")
            assert line.rstrip() == gold_line.rstrip()
    assert new_parens_count == parens_count


@pytest.mark.filterwarnings("ignore")
def test_universe_after_comment():
    problem = montepy.read_input(
        os.path.join("tests", "inputs", "test_universe_data.imcnp")
    )
    problem.print_in_data_block["u"] = False
    problem.print_in_data_block["vol"] = False
    universes = [cell.universe.number for cell in problem.cells]
    try:
        out_file = "universe_after_comment"
        problem.write_to_file(out_file)
        found = False
        with open(out_file, "r") as fh:
            for line in fh:
                print(line.rstrip())
                assert "c IMP:n=0.0" not in line
                if "U=" in line:
                    found = True
        assert found
        problem = montepy.read_input(out_file)
        new_universes = [cell.universe.number for cell in problem.cells]
        assert universes == new_universes
    finally:
        try:
            os.remove(out_file)
        except FileNotFoundError:
            pass


def test_trailing_comment_edge():
    problem = montepy.read_input(
        Path("tests") / "inputs" / "test_trail_comment_edge.imcnp"
    )
    assert len(problem.cells[2].leading_comments) == 3


@pytest.mark.filterwarnings("ignore")
def test_expanding_new_line():
    problem = montepy.read_input(Path("tests") / "inputs" / "test_universe.imcnp")
    fill = problem.cells[1].fill
    universes = [montepy.Universe(n) for n in range(300)]
    fill.universes = np.array([[universes]])
    with io.StringIO() as fh, pytest.warns(LineExpansionWarning):
        problem.write_problem(fh)

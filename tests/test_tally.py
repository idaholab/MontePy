# Copyright 2024-2025, Battelle Energy Alliance, LLC All Rights Reserved.
import pytest

import montepy
from montepy.data_inputs.data_parser import parse_data
from montepy.data_inputs.tally import (
    EnergyDepositionTally,
    F1Tally,
    F4Tally,
    F6Tally,
    ParticleFilter,
    SpatialFilter,
)
from montepy.data_inputs.tally_type import Score, TallyType
from montepy.input_parser.block_type import BlockType
from montepy.input_parser.mcnp_input import Input
from montepy.input_parser.tally_parser import TallyParser
from montepy.input_parser.tokens import TallyLexer


class TestTallyParser:
    @pytest.mark.parametrize(
        "line",
        [
            "F4:n (1 3i 5) T",
            "F4:n (1 2 3 4 5) T",
            "F4:n 1 2 3",
            "F4:n (1 3i 5) (7 8 9) T",
            "f4:n (1 3i 5) (7 8 9)",
            "F7 (1 3i 5) (7 8 9)",
            "F7 (1 3i 5) (7 8 9) ",
        ],
    )
    def test_parsing_tally_groups(_, line):
        data = parse_data(line)
        assert data.prefix == "f"

    def test_parsing_tally_print(_):
        input = Input(["Fq4 f p e"], BlockType.DATA)
        data = parse_data(input)
        assert data.prefix == "fq"

    @pytest.mark.parametrize(
        "test",
        [
            "fm904   (1.0) (1.0 961 103)",
            "fm3064 (1.0 361001 444) $ 1.0=mult",
        ],
    )
    def test_parsing_tally_multiplier(_, test):
        test_lines = {
            "fm904   (1.0) (1.0 961 103)",
            "fm3064 (1.0 361001 444) $ 1.0=mult",
        }
        for test in test_lines:
            print(test)
            input = Input([test], BlockType.DATA)
            data = parse_data(input)

    @pytest.mark.parametrize(
        "line",
        [
            "fs14 -123",
            "fs12 -456 t",
            "fs11 -1 -2",
            "fs16 +1 +2 c",
            "fs17 -1 -2 t c",
        ],
    )
    def test_tally_segment_init(_, line):
        input = Input([line], BlockType.DATA)
        data = parse_data(input)

    @pytest.mark.parametrize("line", ["de4 log 1 2 3 4"])
    def test_de_parsing_jail(_, line):
        data = parse_data(line)
        assert data.mcnp_str() == line
        with pytest.raises(montepy.exceptions.UnsupportedFeature):
            data.data


class TestTallyPathSyntax:
    """Tests for complex MCNP tally path syntax (universe paths, lattice elements)."""

    _parser = TallyParser()
    _lexer = TallyLexer()

    @pytest.mark.parametrize(
        "line",
        [
            "f64:n (1<1)",
            "f74:n (1<1< 2)",
            "f84:n (1[0 0 0]<2)",
            "f94:n (1[0 0 0]<2<3)",
            "F154:n,p  (1 < (2[0 0 0] 2[0 1 0]) < 5)",
            "F1464:n  (1 < 2[0:1 0:1 0:0] < 5)",
            "F174:n  (1 < (2[0:1 0:1 0:0]) < 5)",
            "F184:n  (1 < 2[0 0 0, 0 1 0] < 5)",
            "F194:n  (1 < 2 < 5)",
            "F104:n  ((u=1) < 2[0 0 0] < 5)",
            "F114:n  (u=1 < 2[0 0 0] < 5)",
        ],
    )
    def test_tally_path_parsing(self, line):
        result = self._parser.parse(self._lexer.tokenize(line))
        assert result is not None, f"TallyParser failed to parse: {line}"


class TestFmesh:
    # this is hacky; just makes sure it doesn't crash
    @pytest.mark.parametrize("line", ["fmesh14:n vec=0 0 0", "fmesh14:n vec=0, 0, 0"])
    def test_fmesh_parse(_, line):
        parse_data(line)


@pytest.fixture
def tally_problem():
    return montepy.read_input("tests/inputs/test_tally.imcnp")


class TestTallyObject:
    """Tests for the Tally object model: clone, clone_as, scores, filters."""

    def test_clone_same_type(self, tally_problem):
        f4 = tally_problem.tallies[4]
        clone = f4.clone()
        assert clone.number != f4.number
        assert clone.number % 10 == 4
        assert clone in tally_problem.tallies
        assert list(clone.cells.numbers) == list(f4.cells.numbers)

    def test_clone_as_class(self, tally_problem):
        f4 = tally_problem.tallies[4]
        new = f4.clone_as(F6Tally)
        assert isinstance(new, EnergyDepositionTally)
        assert new.number % 10 == 6
        assert new in tally_problem.tallies
        assert list(new.cells.numbers) == list(f4.cells.numbers)
        assert new.scores == [Score.ENERGY_DEPOSITION]

    def test_clone_as_enum(self, tally_problem):
        f4 = tally_problem.tallies[4]
        new = f4.clone_as(TallyType.ENERGY_DEPOSITION)
        assert isinstance(new, EnergyDepositionTally)
        assert new.number % 10 == 6
        assert new in tally_problem.tallies

    def test_clone_as_incompatible_category(self, tally_problem):
        f1 = tally_problem.tallies[1]
        with pytest.raises(ValueError):
            f1.clone_as(F4Tally)

    def test_clone_as_bad_type(self, tally_problem):
        f4 = tally_problem.tallies[4]
        with pytest.raises(TypeError):
            f4.clone_as("f6")

    @pytest.mark.parametrize(
        "number, expected",
        [
            (1, [Score.CURRENT]),
            (2, [Score.FLUX]),
            # not 4: it has a linked fm4 card, tested in test_tally_multiplier.py
            (34, [Score.FLUX]),
            (6, [Score.ENERGY_DEPOSITION]),
            (7, [Score.FISSION_ENERGY_DEPOSITION]),
            (8, [Score.PULSE_HEIGHT]),
        ],
    )
    def test_scores_default(self, tally_problem, number, expected):
        assert tally_problem.tallies[number].scores == expected

    def test_filters_default(self, tally_problem):
        f1 = tally_problem.tallies[1]  # f1:n,p 1000
        filters = f1.filters
        assert len(filters) == 2
        particle_filter, spatial_filter = filters
        assert isinstance(particle_filter, ParticleFilter)
        assert isinstance(spatial_filter, SpatialFilter)
        assert set(particle_filter.particles) == set(f1.particle_classifiers)
        assert spatial_filter.groups == f1.groups

    def test_add_cell_before_full_parse_preserves_existing_groups(self, tally_problem):
        # Regression test: add_cell/add_group/add_path_group must trigger a
        # full parse *before* mutating _groups, or the mutation is silently
        # lost the next time a @needs_full_ast getter forces a full parse.
        f4 = tally_problem.tallies[4]  # f4:n 1 2 3
        assert not f4.fully_parsed
        new_cell = tally_problem.cells[1].clone()
        f4.add_cell(new_cell)
        assert f4.fully_parsed
        numbers = list(f4.cells.numbers)
        assert {1, 2, 3}.issubset(set(numbers))
        assert new_cell.number in numbers

    def test_from_input_invalid_tally_type_digit(self):
        with pytest.raises(montepy.exceptions.MalformedInputError):
            parse_data(Input(["f3:n 1 2 3"], BlockType.DATA))

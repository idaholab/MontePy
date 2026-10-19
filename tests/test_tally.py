# Copyright 2024-2026, Battelle Energy Alliance, LLC All Rights Reserved.
import io
import warnings

import pytest

import montepy
from montepy.data_inputs.data_parser import parse_data
from montepy.data_inputs.tally import (
    CellFluxTally,
    ChargeDepositionTally,
    CollisionHeatingTally,
    EnergyDepositionTally,
    EnergyDetectorPulseTally,
    F1Tally,
    F4Tally,
    F6Tally,
    FlatGroup,
    LatticeIndex,
    ParticleFilter,
    PathGroup,
    SpatialFilter,
    Tally,
    TallyGroup,
)
from montepy.data_inputs.tally_type import Score, TallyType
from montepy.input_parser.block_type import BlockType
from montepy.input_parser.mcnp_input import Input
from montepy.input_parser import syntax_node
from montepy.input_parser.tally_parser import TallyMultiplierParser, TallyParser
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

    @staticmethod
    def _parse(parser_class, line):
        tokens = Input([line], BlockType.DATA).tokenize(lexer_class=TallyLexer)
        return parser_class().parse(tokens)

    @staticmethod
    def _children(node):
        if isinstance(node, syntax_node.SyntaxNode):
            return list(node.nodes.values())
        return list(node.nodes)

    @staticmethod
    def _value_nodes(node):
        # Every numeric ValueNode, including the values a shortcut expands to.
        for n in TestTallyParser._children(node):
            if isinstance(n, syntax_node.ShortcutNode):
                yield from (v for v in n.nodes if v.value is not None)
            elif isinstance(n, syntax_node.ValueNode):
                if isinstance(n.value, (int, float)):
                    yield n
            elif isinstance(n, (syntax_node.ListNode, syntax_node.SyntaxNode)):
                yield from TestTallyParser._value_nodes(n)

    @pytest.mark.parametrize(
        "line",
        [
            "f4:n 1 3i 5",
            "f4:n 1 2r",
            "f4:n (1 3i 5) (6 7)",
            "f4:n (1 < 2[-1:1 0:1 0] < 3)",
            "f104:n ((u=1) < 2[0 0 0] < 5)",
        ],
    )
    def test_f_numbers_are_int(_, line):
        tree = TestTallyParser._parse(TallyParser, line)
        values = list(TestTallyParser._value_nodes(tree["data"]["tally"]))
        assert values
        for v in values:
            assert v.type is int
            # A shortcut's virtual values need int tokens, not "2.0".
            assert "." not in str(v._token)

    @staticmethod
    def _runs(node):
        for n in TestTallyParser._children(node):
            if type(n) is syntax_node.ListNode and n.name == "tally number run":
                yield n
            elif isinstance(n, syntax_node.SyntaxNode):
                yield from TestTallyParser._runs(n)

    @pytest.mark.parametrize(
        "line, runs",
        [
            ("f4:n 1 3i 5 (6 7) 8", [[1, 2, 3, 4, 5], [6, 7], [8]]),
            ("f4:n (1 < 2 3i 6[0 0 0] < u=3)", [[1], [2, 3, 4, 5, 6]]),
            ("f4:n 1 2r 3i 5", [[1, 1, 1, 2, 3, 4, 5]]),
        ],
    )
    def test_f_numbers_grouped_into_runs(_, line, runs):
        # Each run holds only numbers and shortcuts, and owns its shortcuts,
        # so update_with_new_values can re-zip it without touching the
        # parens, "<", lattice, or u= around it.
        tree = TestTallyParser._parse(TallyParser, line)
        found = list(TestTallyParser._runs(tree["data"]["tally"]))
        assert [[v.value for v in run] for run in found] == runs
        for run in found:
            for n in run.nodes:
                assert isinstance(n, (syntax_node.ValueNode, syntax_node.ShortcutNode))
            assert run._shortcuts == [
                n for n in run.nodes if isinstance(n, syntax_node.ShortcutNode)
            ]
        assert tree["data"].format() == line[len("f4:n ") :]

    def test_f_bins_and_groups_are_keyed_syntax_nodes(_):
        # ListNodes only at the leaves; structure is keyed SyntaxNodes.
        tree = TestTallyParser._parse(TallyParser, "f4:n 1 3i 5 (6 < 7[0 0 0]) 8")
        bins = tree["data"]["tally"]
        assert isinstance(bins, syntax_node.SyntaxNode)
        assert list(bins.nodes) == [("run", 0), ("group", 0), ("run", 1)]
        group = bins[("group", 0)]
        assert isinstance(group, syntax_node.SyntaxNode)
        # The grammar gives a path its levels, and a lattice index its cell.
        assert list(group.nodes) == [
            "start_pad",
            ("level", 0),
            ("sep", 0),
            ("level", 1),
            "end_pad",
        ]
        assert list(group[("level", 0)].nodes) == [("run", 0)]
        assert list(group[("level", 1)].nodes) == [("cell", 0)]
        cell = group[("level", 1)][("cell", 0)]
        assert list(cell.nodes) == [("run", 0), "lattice"]
        assert cell["lattice"].format() == "[0 0 0]"

    def test_next_key_never_reuses_a_number(_):
        from montepy.input_parser.tally_parser import _next_key

        parent = syntax_node.SyntaxNode("tally bins", {})
        for _i in range(3):
            parent.nodes[_next_key(parent, "run")] = syntax_node.ListNode("r")
        del parent.nodes[("run", 0)]
        # One past the highest in use, not the count of children.
        assert _next_key(parent, "run") == ("run", 3)
        assert _next_key(parent, "group") == ("group", 0)

    def test_fm_numbers_stay_float(_):
        tree = TestTallyParser._parse(TallyMultiplierParser, "fm14 (1.0 1 -6)")
        values = list(TestTallyParser._value_nodes(tree["data"]["tally"]))
        assert values and all(v.type is float for v in values)

    @pytest.mark.parametrize(
        "line, numbers",
        [
            ("f4:n 1 2m", [1, 2]),
            ("f4:n 1 1ilog 100", [1, 10, 100]),
            ("f4:n 1 2ilog 1000", [1, 10, 100, 1000]),
            ("f4:n 1 3i 5", [1, 2, 3, 4, 5]),
        ],
    )
    def test_f_shortcuts_with_integral_values(_, line, numbers):
        t = Tally.from_input(line, jit_parse=False)
        assert [g.old_numbers[0] for g in t.groups] == numbers
        assert t.mcnp_str() == line

    @pytest.mark.parametrize("line", ["f4:n 1 2i 5", "f4:n 1 2ilog 10"])
    def test_f_shortcut_with_non_integral_values_raises(_, line):
        with pytest.raises(montepy.exceptions.MalformedInputError, match="non-integer"):
            Tally.from_input(line, jit_parse=False)

    @pytest.mark.parametrize(
        "line",
        [
            # FM reaction-list operators aren't valid in F groups.
            "f4:n (1:2)",
            "f4:n (1 # 2)",
        ],
    )
    def test_f_parser_rejects(_, line):
        assert TestTallyParser._parse(TallyParser, line) is None

    @pytest.mark.parametrize(
        "line", ["fm4 (1.0 1 < 2)", "fm4 (1.0 1[0 0 0])", "fm4 (1.0 u=1)"]
    )
    def test_fm_parser_rejects_path_syntax(_, line):
        assert TestTallyParser._parse(TallyMultiplierParser, line) is None

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
            "F184:n  (1 < 2[0 0 0,0 1 0] < 5)",  # comma with no trailing padding
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


class TestTallyTypeShape:
    """TallyType's value is (mnemonic, modulo, modifier), not a bare digit,
    so it can represent +Fn variants (and eventually FMESH/TMESH) without
    another redesign."""

    @pytest.mark.parametrize(
        "member, mnemonic, modulo, modifier",
        [
            (TallyType.CELL_FLUX, "F", 4, None),
            (TallyType.ENERGY_DEPOSITION, "F", 6, None),
            (TallyType.COLLISION_HEATING, "F", 6, "+"),
            (TallyType.ENERGY_DETECTOR_PULSE, "F", 8, None),
            (TallyType.CHARGE_DEPOSITION, "F", 8, "+"),
            (TallyType.CELL_ENERGY_FLUX, "F", 4, "*"),
            (TallyType.ENERGY_DEPOSITION_JERKS, "F", 6, "*"),
            (TallyType.DETECTOR_ENERGY_DEPOSITION, "F", 8, "*"),
        ],
    )
    def test_mnemonic_modulo_modifier(self, member, mnemonic, modulo, modifier):
        assert member.mnemonic == mnemonic
        assert member.modulo == modulo
        assert member.modifier == modifier

    def test_plain_and_modifier_variants_are_distinct_members(self):
        assert TallyType.ENERGY_DEPOSITION != TallyType.COLLISION_HEATING
        assert TallyType.ENERGY_DETECTOR_PULSE != TallyType.CHARGE_DEPOSITION

    def test_repr_is_friendly(self):
        assert repr(TallyType.CELL_FLUX) == "<TallyType.CELL_FLUX: 4>"
        assert repr(TallyType.COLLISION_HEATING) == "<TallyType.COLLISION_HEATING: +6>"

    def test_score_new_members(self):
        assert Score.COLLISION_HEATING != Score.ENERGY_DEPOSITION
        assert Score.CHARGE_DEPOSITION != Score.PULSE_HEIGHT


@pytest.fixture
def tally_problem():
    return montepy.read_input("tests/inputs/test_tally.imcnp")


@pytest.fixture
def shortcut_problem():
    return montepy.read_input("tests/inputs/test_tally_shortcuts.imcnp")


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

    def test_direct_tally_construction_invalid_digit(self):
        # Tally() bypasses from_input's dispatch-time digit check, so
        # _parse_tally_body must catch it too, once fully parsed.
        from montepy.data_inputs.tally import Tally

        t = Tally(Input(["f3:n 1 2 3"], BlockType.DATA), jit_parse=True)
        with pytest.raises(montepy.exceptions.MalformedInputError):
            t.groups

    @pytest.mark.parametrize(
        "line",
        [
            "f5:n 0 0 0 0.5",
            "F15:p 1 2 3 -0.5 4 5 6 0.1",
            "*f25:p 0 0 0 1",
            "fm5 (1 10 -2)",
        ],
    )
    def test_detector_tally_read_as_plain_data_input(self, line):
        # Review feedback (PR #1005): F5 detector tallies have their own
        # syntax and aren't supported yet (see #1024), so they, and FM cards
        # for them, are parsed like any unimplemented data input.
        data = parse_data(Input([line], BlockType.DATA))
        assert type(data) is montepy.data_inputs.data_input.DataInput
        assert data.mcnp_str() == line
        # A full parse must work too, e.g. for read_input(jit_parse=False):
        # the tally parser read detector coordinates as integers.
        data.full_parse()
        assert data.mcnp_str() == line

    def test_detector_tally_from_input_unsupported(self):
        with pytest.raises(montepy.exceptions.UnsupportedFeature):
            Tally.from_input("f5:n 0 0 0 0.5")

    def test_detector_tally_and_multiplier_round_trip_in_problem(self, tmp_path):
        tally_lines = ["F4:n 1", "F5:n 0 0 0 0.5", "FM5 (1 10 -2)"]
        path = tmp_path / "f5.imcnp"
        path.write_text(
            "\n".join(
                ["F5 test", "1 0 -1 imp:n=1", "2 0 1 imp:n=0", "", "1 so 5", ""]
                + ["m10 1001.80c 1"]
                + tally_lines
            )
            + "\n"
        )
        problem = montepy.read_input(path)
        assert [t.number for t in problem.tallies] == [4]
        assert list(montepy.read_input(path, jit_parse=False).tallies.numbers) == [4]
        assert [d.mcnp_str() for d in problem.data_inputs][1:] == tally_lines
        out = tmp_path / "out.imcnp"
        problem.write_problem(out)
        assert out.read_text().splitlines()[7:10] == tally_lines

    def test_dispatch_class_uses_actual_mnemonic_not_hardcoded_f(self):
        # Regression test: _dispatch_class used to hard-bake the "F"
        # mnemonic internally, so it could never distinguish a real F-card
        # digit/modifier combination from the same combination under a
        # different (currently hypothetical) mnemonic.
        with pytest.raises(montepy.exceptions.MalformedInputError):
            Tally._dispatch_class("f4:n 1", 4, mnemonic="G")
        assert Tally._dispatch_class("f4:n 1", 4, mnemonic="F") is CellFluxTally

    def test_jump_in_tally_numbers_is_skipped(self):
        t = F4Tally(Input(["f4:n 1 J 3"], BlockType.DATA))
        assert [g.old_numbers[0] for g in t.groups] == [1, 3]

    def test_universe_spec_nested_in_bare_group(self):
        # A universe designator wrapped in its own parens, inside a group
        # with no `<` path separator at all, is a nested union: of any cell
        # in universe 2.
        t = F4Tally(Input(["f4:n (5 (u=2) 7)"], BlockType.DATA))
        nested = t.groups[0].members[1]
        assert nested.universe_spec == 2
        assert nested.is_grouped
        assert t.groups[0].universe_spec is None

    @pytest.mark.parametrize("line", ["f", "f4:n( 1", "f4:n,1 1"])
    def test_from_input_malformed_classifier_raises_parsing_error(self, line):
        # The light parser fails on these with a bare exception (or, for
        # "f", returns no number); from_input must surface the full
        # parser's ParsingError instead.
        with pytest.raises(montepy.exceptions.ParsingError):
            parse_data(Input([line], BlockType.DATA))

    @pytest.mark.parametrize(
        "line, tally_type",
        [
            ("f6:n 1", "ENERGY_DEPOSITION"),
            ("*f6:n 1", "ENERGY_DEPOSITION_JERKS"),
            ("+f6:n 1", "COLLISION_HEATING"),
        ],
    )
    def test_tally_type_without_full_parse(self, line, tally_type):
        # tally_type and tally_units come from the classifier, so they don't
        # need a full parse, but must still be right for a "*" or "+" tally.
        tally = Tally.from_input(line)
        assert tally.tally_type is TallyType[tally_type]
        assert tally.tally_units is TallyType[tally_type].units
        assert not tally.fully_parsed

    def test_scores_fully_parses_multiplier(self, tally_problem):
        tally = tally_problem.tallies[4]
        multiplier = tally.multiplier
        assert not multiplier.fully_parsed
        assert tally.scores == [score for b in multiplier.bins for score in b.scores]
        assert multiplier.fully_parsed

    def test_from_input_rejects_two_particle_lists(self):
        # Regression test: the full parser accepted "f4:n:p" by silently
        # dropping the "n".
        with pytest.raises(montepy.exceptions.ParsingError):
            parse_data(Input(["f4:n:p 1"], BlockType.DATA))

    def test_clone_as_non_tally_type_raises_type_error(self, tally_problem):
        f34 = tally_problem.tallies[34]
        with pytest.raises(TypeError):
            f34.clone_as(str)

    def test_clone_as_custom_subclass_outside_category_raises(self, tally_problem):
        from montepy.data_inputs.tally import Tally

        class CustomTally(Tally):
            _TALLY_TYPE = TallyType.CELL_FLUX

        f34 = tally_problem.tallies[34]
        with pytest.raises(ValueError):
            f34.clone_as(CustomTally)

    def test_repr_on_uninitialized_tally(self):
        # __new__ bypasses __init__ entirely, leaving no _number/_groups --
        # exactly the partially-constructed state __repr__'s except branch
        # exists to report gracefully.
        from montepy.data_inputs.tally import Tally

        t = Tally.__new__(Tally)
        assert repr(t) == "TALLY: (unparsed)"

    def test_all_fixture_tallies_fully_parse(self, tally_problem):
        # Force a full parse of every tally in the fixture, including the
        # path/lattice/universe forms (104, 114, 154, 1464, 174, 184, 194)
        # that no other test touches directly.
        for t in tally_problem.tallies:
            groups = t.groups
            assert groups is not None
            assert len(groups) > 0
            _ = t.include_total

    def test_include_total(self, tally_problem):
        assert tally_problem.tallies[24].include_total is True
        assert tally_problem.tallies[34].include_total is True
        assert tally_problem.tallies[1].include_total is False

    def test_contains_linked_flat_group(self, tally_problem):
        f34 = tally_problem.tallies[34]
        assert tally_problem.cells[1] in f34
        assert tally_problem.cells[99] not in f34

    def test_contains_linked_path_group(self, tally_problem):
        f64 = tally_problem.tallies[64]
        assert tally_problem.cells[1] in f64

    def test_contains_forces_full_parse(self, tally_problem):
        # __contains__ is @needs_full_ast: membership must be checked
        # against real data, not silently read as False while still JIT.
        f34 = tally_problem.tallies[34]
        assert not f34.fully_parsed
        assert tally_problem.cells[1] in f34
        assert f34.fully_parsed

    def test_contains_unlinked_flat_group_by_number_only(self):
        t = F4Tally(Input(["f4:n 1 2 3"], BlockType.DATA))

        class FakeCellByNumber:
            number = 2

        assert FakeCellByNumber() in t

    def test_contains_unlinked_flat_group_by_old_number(self):
        t = F4Tally(Input(["f4:n 1 2 3"], BlockType.DATA))

        class FakeCellByOldNumber:
            old_number = 2

        assert FakeCellByOldNumber() in t

    def test_number_validator_rejects_wrong_digit(self, tally_problem):
        f34 = tally_problem.tallies[34]
        with pytest.raises(ValueError):
            f34.number = 16

    def test_clone_unlinked_tally(self):
        t = F4Tally(Input(["f4:n 1 2 3"], BlockType.DATA))
        clone = t.clone()
        assert clone.number != t.number
        assert clone.number % 10 == 4

    def test_clone_as_unlinked_tally(self):
        t = F4Tally(Input(["f4:n 1 2 3"], BlockType.DATA))
        new = t.clone_as(F6Tally)
        assert isinstance(new, EnergyDepositionTally)
        assert new.number % 10 == 6

    def test_clone_as_same_type_delegates_to_clone(self, tally_problem):
        f34 = tally_problem.tallies[34]
        new = f34.clone_as(type(f34))
        assert new.number % 10 == 4
        assert new in tally_problem.tallies

    def test_clone_starting_number_needs_alignment(self, tally_problem):
        # starting_number's digit (9) doesn't match the tally type's digit
        # (4), forcing _align_to_type's "aligned < start" +10 branch.
        f34 = tally_problem.tallies[34]
        new = f34.clone(starting_number=9)
        assert new.number % 10 == 4
        assert new.number >= 14

    def test_tallies_step_defaults_to_10(self, tally_problem):
        # Review feedback (PR #1005): Tallies.step should default to 10,
        # since _next_number_for_type's candidates must always be spaced by
        # a multiple of 10 to preserve the trailing type digit.
        assert tally_problem.tallies.step == 10

    def test_tallies_step_rejects_non_multiple_of_10(self, tally_problem):
        with pytest.raises(ValueError):
            tally_problem.tallies.step = 3

    def test_next_number_for_type_honors_explicit_step(self, tally_problem):
        # Regression test: _next_number_for_type used to multiply the
        # collection's step by 10 internally (candidate += step * 10),
        # silently doubling the effective spacing whenever step was set to
        # anything other than its old default of 1. Now that step's
        # docstring-promised meaning ("the gap between successive
        # candidates") is literal, setting step=20 should space candidates
        # by 20, not 200. Every multiple-of-20 candidate from 14 up through
        # 254 is already taken in the fixture; 274 is the first free one.
        tally_problem.tallies.step = 20
        f34 = tally_problem.tallies[34]
        new = f34.clone(starting_number=14)
        assert new.number == 274

    def test_blank_tally_construction(self):
        t = F4Tally()
        assert t.groups == []

    def test_cell_tallies_skips_full_parse_of_non_referencing_tallies(
        self, tally_problem
    ):
        # Cell.tallies used to scan every tally in the problem and force a
        # full parse of each one (via `self in t`) just to check
        # membership -- catastrophic for a problem with many still-JIT
        # tallies. It should now pre-filter with a cheap raw-text search
        # first, and only fully parse tallies that could plausibly match.
        c1 = tally_problem.cells[1]
        non_referencing = tally_problem.tallies[2]  # f2:p 1005 -- no cell 1
        referencing = tally_problem.tallies[4]  # f4:n 1 2 3
        assert not non_referencing.fully_parsed
        assert not referencing.fully_parsed

        found = {t.number for t in c1.tallies}

        assert not non_referencing.fully_parsed
        assert referencing.fully_parsed
        assert 4 in found
        assert 2 not in found


class TestTallyBuilders:
    """Tests for the from-scratch tally-building API: add_surface, add_group,
    add_path_group, and PathGroup.inside chaining."""

    @pytest.mark.parametrize("hundreds", [0, 10, 123])
    @pytest.mark.parametrize(
        "cls",
        [
            montepy.SurfaceCurrentTally,
            montepy.SurfaceFluxTally,
            montepy.CellFluxTally,
            montepy.EnergyDepositionTally,
            montepy.FissionEnergyDepositionTally,
            montepy.EnergyDetectorPulseTally,
            montepy.data_inputs.tally.CollisionHeatingTally,
            montepy.data_inputs.tally.ChargeDepositionTally,
            montepy.SurfaceEnergyCurrentTally,
            montepy.SurfaceEnergyFluxTally,
            montepy.CellEnergyFluxTally,
            montepy.DetectorEnergyDepositionTally,
        ],
    )
    def test_from_scratch_classifier_formatting(self, cls, hundreds):
        # The default number placeholder must not leave stray padding once
        # a real number of any width is assigned.
        tally_type = cls._TALLY_TYPE
        number = hundreds * 10 + tally_type.modulo
        t = cls()
        t.number = number
        if issubclass(cls, montepy.data_inputs.tally.CellTally):
            t.add_cell(montepy.Cell(number=5))
        else:
            surf = montepy.surfaces.Surface()
            surf.number = 5
            t.add_surface(surf)
        assert t.mcnp_str().startswith(f"{tally_type.modifier or ''}F{number} 5")

    def test_surface_tally_add_surface_and_group(self, tally_problem):
        f1 = tally_problem.tallies[1]  # f1:n,p 1000 -- only surface 1000 so far
        s = tally_problem.surfaces[1005]
        f1.add_surface(s)
        assert s in f1.surfaces
        assert f1.groups[-1].old_numbers == [s.number]

        s_already_present = tally_problem.surfaces[1000]
        s_new = tally_problem.surfaces[1010]
        f1.add_group(s_already_present, s_new)
        assert f1.groups[-1].is_grouped
        assert set(f1.groups[-1].old_numbers) == {
            s_already_present.number,
            s_new.number,
        }
        assert s_new in f1.surfaces

    def test_surface_tally_add_path_group_and_inside_chaining(self, tally_problem):
        f1 = tally_problem.tallies[1]
        s1, s2 = tally_problem.surfaces[1000], tally_problem.surfaces[1005]
        pg = f1.add_path_group(s1)
        assert isinstance(pg, PathGroup)
        pg.inside(s2, lattice=[0, 0, 0])
        assert pg in f1.groups
        assert len(pg.levels) == 2

        # Re-linking must resolve the newly added PathGroup too -- but only
        # its innermost (scored) level; s2 is a containment level (per the
        # MCNP manual's Si/Ci distinction), never itself "in" .surfaces.
        f1.link_to_problem(tally_problem)
        assert s1 in f1.surfaces
        assert s2 not in f1.surfaces

    def test_link_group_surfaces_raises_on_missing_surface(self, tally_problem):
        # Regression test: update_pointers used to silently skip a number
        # with no matching surface (continue past the KeyError). It should
        # now raise a clear BrokenObjectLinkError instead, matching
        # UnitHalfSpace.update_pointers' error handling.
        f1 = tally_problem.tallies[1]
        _ = f1.surfaces  # force full parse
        f1._groups.append(FlatGroup([99999], is_grouped=False))
        with pytest.raises(montepy.exceptions.BrokenObjectLinkError):
            f1.link_to_problem(tally_problem)

    def test_link_group_cells_raises_on_missing_cell(self, tally_problem):
        f34 = tally_problem.tallies[34]
        _ = f34.cells  # force full parse
        f34._groups.append(FlatGroup([99999], is_grouped=False))
        with pytest.raises(montepy.exceptions.BrokenObjectLinkError):
            f34.link_to_problem(tally_problem)

    def test_add_cell_adds_each_as_its_own_bin(self, tally_problem):
        tally = tally_problem.tallies[34]
        cells = [tally_problem.cells[n] for n in (7, 8, 99)]
        groups_before = len(tally.groups)
        tally.add_cell(*cells)
        new_groups = tally.groups[groups_before:]
        assert [g.old_numbers for g in new_groups] == [[7], [8], [99]]
        assert not any(g.is_grouped for g in new_groups)
        assert all(c in tally.cells for c in cells)

    def test_add_surface_adds_each_as_its_own_bin(self, tally_problem):
        tally = tally_problem.tallies[1]
        surfaces = [tally_problem.surfaces[n] for n in (1005, 1010)]
        tally.add_surface(*surfaces)
        assert [g.old_numbers for g in tally.groups[-2:]] == [[1005], [1010]]

    @pytest.mark.parametrize("method", ["add_cell", "add_group"])
    def test_cell_builders_need_a_cell(self, method):
        tally = F4Tally()
        with pytest.raises(ValueError):
            getattr(tally, method)()
        assert tally.groups == []

    def test_cell_tally_add_group(self, tally_problem):
        f34 = tally_problem.tallies[34]  # cells 1,2,3,5 -- 99 is new
        c_already_present = tally_problem.cells[1]
        c_new = tally_problem.cells[99]
        f34.add_group(c_already_present, c_new)
        assert f34.groups[-1].is_grouped
        assert set(f34.groups[-1].old_numbers) == {
            c_already_present.number,
            c_new.number,
        }
        assert c_new in f34.cells

    def test_cell_tally_add_path_group_and_inside_chaining(self, tally_problem):
        f34 = tally_problem.tallies[34]
        c1, c2 = tally_problem.cells[1], tally_problem.cells[2]
        pg = f34.add_path_group(c1)
        assert isinstance(pg, PathGroup)
        pg.inside(c2)
        assert pg in f34.groups
        assert len(pg.levels) == 2


def verify_export(tally):
    """Format ``tally`` to MCNP text, re-parse it standalone, and confirm
    the result is equivalent. Mirrors the ``verify_export`` convention in
    ``tests/test_surfaces.py``/``tests/test_cell_problem.py``."""
    output = tally.format_for_mcnp_input((6, 3, 0))
    joined = "\n".join(output)
    assert joined == tally.mcnp_str((6, 3, 0))
    new_tally = type(tally)(joined)
    assert new_tally.number == tally.number
    assert new_tally.tally_type == tally.tally_type
    assert new_tally.include_total == tally.include_total
    assert len(new_tally.groups) == len(tally.groups)
    for old_group, new_group in zip(tally.groups, new_tally.groups):
        assert isinstance(new_group, type(old_group))
        if isinstance(old_group, FlatGroup):
            assert old_group.is_grouped == new_group.is_grouped
    return new_tally


def verify_prob_export(problem, tally):
    """Write the whole ``problem`` out and re-read it, returning the
    equivalent tally from the new problem. The only test shape that can
    catch bugs in problem/collection-level registration (e.g. an FM card
    silently missing from ``data_inputs``), since a per-object
    :func:`verify_export` check never sees the problem at all."""
    with io.StringIO() as fh:
        problem.write_problem(fh)
        fh.seek(0)
        new_problem = montepy.read_input(fh)
    return new_problem.tallies[tally.number]


class TestPlusModifierTallies:
    """+F6 (collision heating) and +F8 (charge deposition) are distinct
    Tally subclasses from plain F6/F8, distinguished only by a leading
    ``+`` in the classifier -- not by tally-type digit."""

    @pytest.mark.parametrize("jit_parse", [True, False])
    @pytest.mark.parametrize(
        "line, expected_class, expected_score",
        [
            ("+F6:n 1 2 3", CollisionHeatingTally, Score.COLLISION_HEATING),
            ("+F8:p 1", ChargeDepositionTally, Score.CHARGE_DEPOSITION),
        ],
    )
    def test_dispatch(self, jit_parse, line, expected_class, expected_score):
        t = Tally.from_input(line, jit_parse=jit_parse)
        assert isinstance(t, expected_class)
        assert t.scores == [expected_score]

    def test_invalid_modifier_digit_combination_raises(self):
        with pytest.raises(montepy.exceptions.MalformedInputError):
            Tally.from_input("+F4:n 1 2 3", jit_parse=False)

    @pytest.mark.parametrize("line", ["+f6:n 1 2 3", "+f8:p 1"])
    def test_round_trip(self, line):
        t = Tally.from_input(line, jit_parse=False)
        assert t.mcnp_str() == line
        verify_export(t)

    def test_from_scratch_construction_writes_modifier(self):
        t = CollisionHeatingTally(number=16)
        t.add_cell(montepy.Cell(number=1))
        with warnings.catch_warnings():
            warnings.simplefilter("error")
            text = t.mcnp_str()
        assert text.strip().startswith("+F16")

    def test_clone_as_adds_modifier(self):
        flux = F4Tally(Input(["f4:n 1 2 3"], BlockType.DATA), jit_parse=False)
        heat = flux.clone_as(CollisionHeatingTally)
        assert isinstance(heat, CollisionHeatingTally)
        assert "+" in heat.mcnp_str()

    def test_clone_as_removes_modifier(self):
        heat = Tally.from_input("+F6:n 1 2 3", jit_parse=False)
        back = heat.clone_as(EnergyDepositionTally)
        assert isinstance(back, EnergyDepositionTally)
        # The empty modifier isn't padded to the width of the old "+".
        assert back.mcnp_str().startswith("F")

    @pytest.mark.parametrize(
        "cls, prefix", [(F4Tally, "F"), (CollisionHeatingTally, "+F")]
    )
    @pytest.mark.parametrize("number", [None, 104, 12344])
    def test_from_scratch_number_formatting(self, cls, prefix, number):
        if number is not None:
            number = number - number % 10 + cls._TALLY_TYPE.modulo
        with warnings.catch_warnings():
            warnings.simplefilter("error")
            tally = cls() if number is None else cls(number=number)
            # An unnumbered tally is the smallest number of its type.
            expected = cls._TALLY_TYPE.modulo if number is None else number
            assert tally.number == expected
            assert tally.mcnp_str().rstrip() == f"{prefix}{expected}"

    @pytest.mark.parametrize("jit_parse", [True, False])
    def test_parsed_tally_without_modifier_writes(self, jit_parse):
        tally = Tally.from_input("F4:n 1", jit_parse=jit_parse)
        tally.add_cell(montepy.Cell(number=5))
        assert tally.mcnp_str().startswith("F4:n 1 5")

    @pytest.mark.parametrize(
        "cls", [CellFluxTally, CollisionHeatingTally, montepy.CellEnergyFluxTally]
    )
    def test_from_scratch_tally_has_modifier_node(self, cls):
        tally = cls(number=cls._TALLY_TYPE.modulo)
        assert tally._classifier.modifier.value == (cls._TALLY_TYPE.modifier or "")

    def test_clone_as_bare_tally_type_works(self):
        flux = F4Tally(Input(["f4:n 1 2 3"], BlockType.DATA), jit_parse=False)
        heat = flux.clone_as(TallyType.COLLISION_HEATING)
        assert isinstance(heat, CollisionHeatingTally)

    def test_fixture_file_dispatch(self, tally_problem):
        assert isinstance(tally_problem.tallies[16], CollisionHeatingTally)
        assert isinstance(tally_problem.tallies[18], ChargeDepositionTally)


class TestGroupRoundTrip:
    """Mutating a Tally's groups through the public API must be reflected in
    mcnp_str(), not just in the in-memory Python state. These lock in the
    Tally._update_values / FlatGroup/PathGroup node-generation layer."""

    def test_unmodified_tally_round_trips_exactly(self, tally_problem):
        for number in (4, 14, 24, 34, 44, 54, 64, 74, 84, 94):
            tally = tally_problem.tallies[number]
            before = tally.mcnp_str()
            tally.full_parse()
            assert tally.mcnp_str() == before
            verify_export(tally)

    def test_add_cell_reflected_in_mcnp_str(self):
        t = F4Tally(Input(["f4:n 1 2 3"], BlockType.DATA), jit_parse=False)
        cell = montepy.Cell()
        cell.number = 99
        t.add_cell(cell)
        assert "99" in t.mcnp_str()
        assert "1" in t.mcnp_str() and "2" in t.mcnp_str() and "3" in t.mcnp_str()
        verify_export(t)

    def test_blank_tally_add_cell_writes_valid_card(self):
        t = F4Tally()
        t.number = 4
        cell = montepy.Cell()
        cell.number = 1
        t.add_cell(cell)
        text = t.mcnp_str()
        assert "1" in text
        # the unfixed bug wrote out only 'F 4 ', with no cell number at all
        assert text.strip() != "F 4"

    def test_add_group_reflected_in_mcnp_str(self):
        t = F4Tally(Input(["f4:n 1 2 3"], BlockType.DATA), jit_parse=False)
        c1, c2 = montepy.Cell(), montepy.Cell()
        c1.number = 10
        c2.number = 11
        t.add_group(c1, c2)
        text = t.mcnp_str()
        assert "10" in text and "11" in text
        assert "(" in text and ")" in text
        verify_export(t)

    def test_renumbered_cell_reflected_in_mcnp_str(self):
        t = F4Tally(Input(["f4:n 1 2 3"], BlockType.DATA), jit_parse=False)
        cell = montepy.Cell()
        cell.number = 99
        t.add_cell(cell)
        cell.number = 199
        text = t.mcnp_str()
        assert "199" in text
        assert "99" not in text.replace("199", "")
        verify_export(t)

    @pytest.mark.parametrize(
        "collection, old, new, tally_number, expected",
        [
            ("cells", 3, 300, 4, "f4:n 1 2 300"),
            ("cells", 3, 300, 8, "f8:p 300"),
            ("surfaces", 1005, 1500, 2, "f2:p 1500"),
        ],
    )
    def test_renumber_reaches_still_jit_tally(
        self, tally_problem, collection, old, new, tally_number, expected
    ):
        # Regression test: a still-JIT tally writes its raw input lines, so
        # renumbering a cell/surface it references must force it to fully
        # parse first (via _parent_collections), or it writes the old number.
        t = tally_problem.tallies[tally_number]
        assert not t.fully_parsed
        getattr(tally_problem, collection)[old].number = new
        assert t.mcnp_str() == expected

    @pytest.mark.parametrize("jit_parse", [True, False])
    def test_renumber_follows_path_outer_levels(self, jit_parse):
        # Regression test: a path's outer levels and its U=N weren't linked,
        # so they kept the numbers they were read with after a renumber.
        problem = montepy.read_input(
            "tests/inputs/test_tally.imcnp", jit_parse=jit_parse
        )
        problem.cells[2].number = 22
        problem.cells[5].number = 55
        problem.universes[1].number = 11
        assert problem.tallies[104].mcnp_str() == "F104:n  ((u=11) < 22[0 0 0] < 55)"
        assert problem.tallies[114].mcnp_str() == "F114:n  (u=11 < 22[0 0 0] < 55)"
        group = problem.tallies[114].groups[0]
        assert group.levels[0].universe_spec is problem.universes[11]

    def test_renumber_universe_reaches_still_jit_tally(self, tally_problem):
        tally = tally_problem.tallies[114]
        assert not tally.fully_parsed
        tally_problem.universes[1].number = 11
        assert tally.mcnp_str() == "F114:n  (u=11 < 2[0 0 0] < 5)"

    def test_renumber_reaches_still_jit_tally_through_shortcut(self, tally_problem):
        # Regression test: "1 3i 5" scores cell 2 without "2" in its text, so
        # the text search didn't parse it before cell 2 was renumbered, and
        # it then couldn't find cell 2.
        tally = tally_problem.tallies[34]  # f34:n (1 3i 5) T
        assert not tally.fully_parsed
        tally_problem.cells[2].number = 20
        numbers = [c.number for c in tally.groups[0].cells_or_surfaces]
        assert numbers == [1, 20, 3, 4, 5]

    def test_cell_tallies_finds_tally_through_shortcut(self):
        jit = montepy.read_input("tests/inputs/test_tally.imcnp")
        full = montepy.read_input("tests/inputs/test_tally.imcnp", jit_parse=False)
        found = {t.number for t in jit.cells[2].tallies}
        assert found == {t.number for t in full.cells[2].tallies}
        assert {34, 44, 54} <= found

    def test_include_total_settable(self):
        t = F4Tally(Input(["f4:n 1 2 3"], BlockType.DATA), jit_parse=False)
        assert not t.include_total
        t.include_total = True
        assert t.include_total
        assert t.mcnp_str().strip().endswith("T")
        t.include_total = False
        assert not t.include_total
        assert not t.mcnp_str().strip().endswith("T")

    def test_include_total_parses_lazily(self):
        # include_total's backing attribute is set before parsing, so the
        # getter must still force a full parse rather than return it as is.
        t = CellFluxTally(Input(["f4:n 1 2 t"], BlockType.DATA))
        assert not t.fully_parsed
        assert t.include_total is True

    def test_include_total_rejects_non_bool(self):
        t = CellFluxTally(Input(["f4:n 1 2"], BlockType.DATA))
        with pytest.raises(TypeError):
            t.include_total = 1

    def test_untouched_lowercase_total_flag_round_trips_exactly(self):
        # Regression test: _update_values used to unconditionally rewrite
        # the total-bin flag as uppercase "T" on every write, silently
        # clobbering a parsed lowercase "t" even when include_total was
        # never touched.
        line = "f24:n (1 2) (3) t"
        t = CellFluxTally(Input([line], BlockType.DATA), jit_parse=False)
        assert t.include_total
        assert t.mcnp_str() == line

    def test_changed_include_total_writes_uppercase(self):
        # A genuine value change (not merely touching the setter) always
        # writes a fresh, normalized-uppercase node.
        t = CellFluxTally(Input(["f24:n (1 2) (3) t"], BlockType.DATA), jit_parse=False)
        t.include_total = False
        assert t.mcnp_str().strip() == "f24:n (1 2) (3)"
        t.include_total = True
        assert t.mcnp_str().strip().endswith(" T")

    @pytest.mark.parametrize(
        "line, expected",
        [
            ("f4:n 1 2", "f4:n 1 2 T"),
            ("f4:n (1 2)", "f4:n (1 2) T"),
            ("f4:n 1 3i 5", "f4:n 1 3i 5 T"),
            ("f4:n (1 < 2)", "f4:n (1 < 2) T"),
        ],
    )
    def test_added_total_flag_not_glued_to_last_bin(self, line, expected):
        # Regression test: with no padding after the last bin, setting
        # include_total wrote "f4:n 1 2T".
        t = CellFluxTally(Input([line], BlockType.DATA), jit_parse=False)
        t.include_total = True
        assert t.mcnp_str().strip() == expected
        assert Tally.from_input(t.mcnp_str()).include_total

    def test_removed_total_flag_keeps_trailing_comment(self):
        # Regression test: removing the "t" also dropped the comment after it.
        t = CellFluxTally(Input(["f4:n 1 2 t $ hi"], BlockType.DATA), jit_parse=False)
        t.include_total = False
        assert t.mcnp_str() == "f4:n 1 2   $ hi"
        assert not Tally.from_input(t.mcnp_str()).include_total
        t.include_total = True
        assert t.mcnp_str() == "f4:n 1 2 T $ hi"

    def test_added_total_flag_after_trailing_comment(self):
        # The padding added so "T" isn't glued to the last bin must not go
        # after a comment, which would put the "T" inside it.
        t = CellFluxTally(Input(["f4:n 1 2 $ c"], BlockType.DATA), jit_parse=False)
        t.include_total = True
        assert Tally.from_input(t.mcnp_str()).include_total

    @pytest.mark.parametrize("number", [1, 4])
    def test_link_to_problem_forwards_deepcopy(self, tally_problem, number):
        # Regression test: SurfaceTally/CellTally's link_to_problem
        # overrides accepted a deepcopy kwarg but never forwarded it to
        # super().link_to_problem(), silently dropping it. Every concrete
        # Tally eventually bottoms out at MCNP_Object.link_to_problem
        # regardless of how many CellTally/SurfaceTally levels sit between
        # them, so spying there catches all of them.
        import unittest.mock

        t = tally_problem.tallies[number]
        with unittest.mock.patch.object(
            montepy.mcnp_object.MCNP_Object, "link_to_problem", autospec=True
        ) as spy:
            t.link_to_problem(tally_problem, deepcopy=True)
        spy.assert_called_once_with(t, tally_problem, deepcopy=True)

    def test_renumbering_cell_in_shortcut_group(self, tally_problem):
        # Renumbering a cell inside a shortcut used to raise IllegalState;
        # the shortcut is now re-zipped around the new value.
        t = tally_problem.tallies[44]  # f44:n (1 3i 5) (7 8 9)
        t.full_parse()
        assert t.mcnp_str() == "f44:n (1 3i 5) (7 8 9)"
        tally_problem.cells[5].number = 50
        assert t.mcnp_str() == "f44:n (1 2i 4 50) (7 8 9)"

    def test_untouched_shortcut_group_still_round_trips(self, tally_problem):
        t = tally_problem.tallies[44]
        t.full_parse()
        assert t.mcnp_str() == "f44:n (1 3i 5) (7 8 9)"
        # Renumbering a cell that this tally doesn't reference leaves it alone.
        tally_problem.cells[99].number = 990
        assert t.mcnp_str() == "f44:n (1 3i 5) (7 8 9)"

    @pytest.mark.parametrize(
        "number, line",
        [
            (4, "f4:n 1 3i 5"),
            (14, "f14:n 1 2r"),
            (24, "f24:n (1 3i 5) (6 7)"),
            (34, "f34:n (1 2r 5)"),
        ],
    )
    def test_untouched_shortcut_round_trips(self, shortcut_problem, number, line):
        t = shortcut_problem.tallies[number]
        t.full_parse()
        assert t.mcnp_str() == line
        shortcut_problem.cells[8].number = 80
        assert t.mcnp_str() == line

    @pytest.mark.parametrize(
        "line",
        [
            # Re-zipping an unchanged run would absorb the 6 ("1 4i 6").
            "f4:n 1 3i 5 6",
            "f4:n (1 3i 5 6)",
            "f4:n 1 2r 3i 5",
            "f4:n 1 J 3",
        ],
    )
    def test_unchanged_run_keeps_its_text(self, line):
        assert Tally.from_input(line, jit_parse=False).mcnp_str() == line

    @pytest.mark.parametrize(
        "old, new, number, expected",
        [
            (3, 30, 4, "f4:n 1 2 30 4 5"),
            (3, 30, 24, "f24:n (1 2 30 4 5) (6 7)"),
            (5, 50, 4, "f4:n 1 2i 4 50"),
            (1, 100, 14, "f14:n 100 2r"),
            (1, 100, 34, "f34:n (100 2r 5)"),
            # Only the part of the shortcut that no longer fits changes.
            (5, 50, 34, "f34:n (1 2r 50)"),
        ],
    )
    def test_renumber_inside_shortcut(
        self, shortcut_problem, old, new, number, expected
    ):
        t = shortcut_problem.tallies[number]
        shortcut_problem.cells[old].number = new
        assert t.mcnp_str() == expected

    def test_renumber_inside_shortcut_twice(self, shortcut_problem):
        t = shortcut_problem.tallies[24]
        shortcut_problem.cells[3].number = 30
        assert t.mcnp_str() == "f24:n (1 2 30 4 5) (6 7)"
        shortcut_problem.cells[30].number = 300
        assert t.mcnp_str() == "f24:n (1 2 300 4 5) (6 7)"

    def test_add_cell_after_top_level_shortcut_rezips(self, shortcut_problem):
        t = shortcut_problem.tallies[4]
        t.add_cell(shortcut_problem.cells[6])
        assert t.mcnp_str().rstrip() == "f4:n 1 4i 6"

    def test_add_cell_keeps_grouped_shortcut(self, shortcut_problem):
        t = shortcut_problem.tallies[24]
        t.add_cell(shortcut_problem.cells[8])
        assert t.mcnp_str().startswith("f24:n (1 3i 5) (6 7)")

    def test_remove_from_top_level_shortcut_rezips(self, shortcut_problem):
        t = shortcut_problem.tallies[4]
        t.full_parse()
        t.remove_group(t.groups[-1])
        assert t.mcnp_str() == "f4:n 1 2i 4"

    def test_remove_group_leaves_other_run_alone(self):
        t = Tally.from_input("f4:n 1 3i 5 6 (7 8)", jit_parse=False)
        t.remove_group(t.groups[-1])
        assert t.mcnp_str().rstrip() == "f4:n 1 3i 5 6"

    @pytest.mark.parametrize(
        "lattice, written",
        [
            ([0, 0, 0], "(1 < (2[0 0 0] 3 ))"),
            ([(0, 1), 0, 0], "(1 < (2[0:1 0 0] 3 ))"),
        ],
    )
    def test_lattice_written_right_after_its_cell(self, lattice, written):
        # Regression test: a path built from scratch wrote "2 [0 0 0]3",
        # but MCNP requires the brackets to immediately follow the cell.
        tally = montepy.CellFluxTally(number=314)
        cells = [montepy.Cell(number=i) for i in (1, 2, 3)]
        pg = tally.add_path_group(cells[0])
        pg.inside(cells[1], cells[2], lattice=lattice)
        assert tally.mcnp_str().endswith(written)
        reread = Tally.from_input(tally.mcnp_str())
        assert reread.groups[0].levels[1].lattice_indices[0].elements == (
            tuple(lattice),
        )

    def test_lattice_after_shortcut_attaches_to_its_last_value(self):
        # Regression test: a lattice index right after a shortcut was dropped.
        t = Tally.from_input("f4:n (1 < 2 3i 6[0 0 0] < 7)", jit_parse=False)
        indices = t.groups[0].levels[1].lattice_indices
        assert [None if i is None else i.elements for i in indices] == [
            None,
            None,
            None,
            None,
            ((0, 0, 0),),
        ]

    def test_remove_cell_reflected_in_mcnp_str(self):
        t = F4Tally(Input(["f4:n 1 2 3"], BlockType.DATA), jit_parse=False)
        cell = montepy.Cell()
        cell.number = 99
        t.add_cell(cell)
        assert "99" in t.mcnp_str()
        t.remove_cell(cell)
        assert "99" not in t.mcnp_str()
        assert cell not in t.cells

    def test_remove_cell_removes_it_from_unions_too(self):
        # Review feedback (PR #1005): remove_cell used to only remove a
        # single-cell bin, leaving the cell in unions, so "cell in tally"
        # was still True afterwards.
        t = F4Tally(Input(["f4:n 1 2 3"], BlockType.DATA), jit_parse=False)
        cell = montepy.Cell()
        cell.number = 99
        other = montepy.Cell()
        other.number = 98
        t.add_cell(cell)
        t.add_group(cell, other)
        t.remove_cell(cell)
        assert cell not in t
        assert cell not in t.cells
        assert other in t.cells
        reread = Tally.from_input(t.mcnp_str())
        assert [(g.old_numbers, g.is_grouped) for g in reread.groups] == [
            ([1], False),
            ([2], False),
            ([3], False),
            ([98], True),
        ]

    def test_remove_cell_raises_if_not_in_tally(self):
        t = F4Tally(Input(["f4:n 1 2 3"], BlockType.DATA), jit_parse=False)
        cell = montepy.Cell()
        cell.number = 99
        with pytest.raises(ValueError):
            t.remove_cell(cell)

    def test_remove_group_reflected_in_mcnp_str(self):
        t = F4Tally(Input(["f4:n 1 2 3"], BlockType.DATA), jit_parse=False)
        c1, c2 = montepy.Cell(), montepy.Cell()
        c1.number = 10
        c2.number = 11
        t.add_group(c1, c2)
        group = t.groups[-1]
        t.remove_group(group)
        text = t.mcnp_str()
        assert "10" not in text and "11" not in text
        assert c1 not in t.cells and c2 not in t.cells

    def test_remove_surface_reflected_in_mcnp_str(self, tally_problem):
        f1 = tally_problem.tallies[1]
        s = tally_problem.surfaces[1005]
        f1.add_surface(s)
        assert "1005" in f1.mcnp_str()
        f1.remove_surface(s)
        assert "1005" not in f1.mcnp_str()
        assert s not in f1.surfaces

    def test_path_group_contains_only_innermost_level(self, tally_problem):
        # Locks in a deliberate design decision (documented on
        # PathGroup.__contains__): only the innermost/scored level is
        # considered "in" the group, not any outer containment level.
        t = tally_problem.tallies[194]  # F194:n (1 < 2 < 5)
        g = t.groups[0]
        assert isinstance(g, PathGroup)
        assert tally_problem.cells[1] in g
        assert tally_problem.cells[2] not in g
        assert tally_problem.cells[5] not in g

    def test_path_group_numbers_and_objects_cover_all_levels(self, tally_problem):
        group = tally_problem.tallies[194].groups[0]  # F194:n (1 < 2 < 5)
        cells = tally_problem.cells
        assert group.old_numbers == [1, 2, 5]
        assert group.inner_old_numbers == [1]
        assert group.cells_or_surfaces == [cells[1], cells[2], cells[5]]
        assert group.inner_cells_or_surfaces == [cells[1]]

    def test_remove_group_is_not_quadratic(self):
        # Regression test: remove_group's own cleanup loop used to
        # re-scan every remaining group once per still-linked cell (via
        # Tally.__contains__) -- an O(N*M) cost per call that, called once
        # per group as groups are removed one at a time, made bulk removal
        # super-quadratic overall. Confirmed empirically before the fix:
        # N=800 took ~10s; N=400 already took ~1.3s. After the fix, N=800
        # takes well under a tenth of a second (the remaining O(N^2) comes
        # entirely from NumberedObjectCollection.remove()'s own O(N)
        # linear-list removal, a separate, pre-existing, out-of-scope cost
        # -- this test isolates just the containment-check fix).
        import time

        t = F4Tally(Input(["f4:n 1"], BlockType.DATA), jit_parse=False)
        cells = []
        for i in range(2, 802):
            cell = montepy.Cell()
            cell.number = i
            cells.append(cell)
            t.add_cell(cell)
        groups = list(t.groups[1:])  # skip the original "f4:n 1" group
        start = time.perf_counter()
        for group in groups:
            t.remove_group(group)
        elapsed = time.perf_counter() - start
        assert (
            elapsed < 2.0
        ), f"remove_group took {elapsed:.2f}s for N=800 -- likely quadratic"
        assert len(t.groups) == 1
        assert len(t.cells) == 0


class TestReprAndEquality:
    """Smoke tests for __repr__ and __eq__-against-wrong-type on the small
    standalone value objects in tally.py. Coverage only counts a line as hit
    if it executes, and pytest only reprs on assertion *failure*, so these
    branches need explicit exercising."""

    def test_lattice_index(self):
        li = LatticeIndex([[1, (2, 3)]])
        assert li.elements == ((1, (2, 3)),)
        assert "LatticeIndex" in repr(li)

    @pytest.mark.parametrize(
        "lattice, elements",
        [
            ("[0 0 0]", ((0, 0, 0),)),
            ("[5]", ((5,),)),
            ("[-1:1 0:1 0]", (((-1, 1), (0, 1), 0),)),
            ("[0 0 0, 0 1 0]", ((0, 0, 0), (0, 1, 0))),
            ("[0 0 0,0 1 0]", ((0, 0, 0), (0, 1, 0))),
            ("[0:1 0 0, 2 0:1 0]", (((0, 1), 0, 0), (2, (0, 1), 0))),
        ],
    )
    def test_lattice_index_elements(self, lattice, elements):
        t = Tally.from_input(f"F4:n (1 < 2{lattice} < 3)")
        li = t.groups[0].levels[1].lattice_indices[0]
        assert li.elements == elements
        # Rebuilding from the data model must give back the same elements.
        assert LatticeIndex.parse_input_node(li.node).elements == elements

    def test_lattice_index_node_writes_commas(self):
        li = LatticeIndex([[0, 0, 0], [(0, 1), 1, 0]])
        assert li.node.format() == "[0 0 0, 0:1 1 0]"

    def test_tally_group_is_abstract(self):
        # Review feedback (PR #1005): TallyGroup's docstring called itself
        # "Abstract base for..." but didn't inherit ABC, unlike every other
        # "abstract base" class in the codebase.
        with pytest.raises(TypeError):
            TallyGroup()

    def test_particle_filter_eq_wrong_type_and_repr(self):
        obj = ParticleFilter([montepy.Particle.NEUTRON])
        assert obj != "not a filter"
        assert "ParticleFilter" in repr(obj)

    def test_spatial_filter_eq_wrong_type_and_repr(self):
        obj = SpatialFilter([FlatGroup([1], is_grouped=False)])
        assert obj != "not a filter"
        assert "SpatialFilter" in repr(obj)

    def test_flat_group_properties_and_repr(self):
        fg = FlatGroup([1, 2], is_grouped=True, universe_spec=3)
        assert fg.old_numbers == [1, 2]
        assert fg.is_grouped is True
        assert fg.universe_spec == 3
        assert "FlatGroup" in repr(fg)

    def test_flat_group_cells_and_surfaces_typed_accessors(self):
        # Unresolved (raw numbers): neither typed accessor applies yet.
        unresolved = FlatGroup([1, 2], is_grouped=False)
        assert unresolved.cells is None
        assert unresolved.surfaces is None

        # Resolved to Cell objects: .cells returns them, .surfaces is None.
        c1, c2 = montepy.Cell(), montepy.Cell()
        c1.number, c2.number = 1, 2
        cell_group = FlatGroup([c1, c2], is_grouped=False)
        assert cell_group.cells == [c1, c2]
        assert cell_group.surfaces is None

        # Resolved to Surface objects: the reverse.
        s = montepy.SphereAtOrigin(number=1000)
        surface_group = FlatGroup([s], is_grouped=False)
        assert surface_group.surfaces == [s]
        assert surface_group.cells is None

    def test_path_group_levels_and_repr(self):
        pg = PathGroup([FlatGroup([1], is_grouped=False)])
        assert len(pg.levels) == 1
        assert "PathGroup" in repr(pg)

    def test_path_group_old_numbers_and_cells_or_surfaces_empty_levels(self):
        pg = PathGroup([])
        assert pg.old_numbers == []
        assert pg.cells_or_surfaces == []

    def test_path_group_empty_levels_contains(self):
        assert 1 not in PathGroup([])

    def test_tally_parent_collections(self):
        from montepy.data_inputs.tally import Tally

        assert Tally._parent_collections() == ()


class TestRemoveScored:
    """remove_cell/remove_surface remove an item from everywhere it is scored,
    so that afterwards it is not ``in`` the tally (review feedback, PR #1005)."""

    @staticmethod
    def _remove(line, number):
        t = Tally.from_input(line, jit_parse=False)
        t.remove_cell(montepy.Cell(number=number))
        return t

    @pytest.mark.parametrize(
        "line, number, expected",
        [
            ("f4:n (1 2 3)", 2, "f4:n (1 3)"),
            ("f4:n (1 2[0 0 0] 3)", 2, "f4:n (1 3)"),
            ("f4:n (1 2[0 0 0])", 2, "f4:n (1)"),
            ("f4:n (1[0 0 0] 2)", 1, "f4:n (2)"),
            ("f4:n (1 3i 5) 6", 5, "f4:n (1 2i 4) 6"),
            ("f4:n (1 2 3) 4", 3, "f4:n (1 2) 4"),
            # A union keeps its parens with one member left.
            ("f4:n (1 2)", 1, "f4:n (2)"),
            ("f4:n 3 (3 4)", 3, "f4:n (4)"),
            ("f4:n ((1 2) < 5)", 1, "f4:n ((2) < 5)"),
            # A bin or path left with nothing to score is removed.
            ("f4:n (4 < 5) 6", 4, "f4:n 6"),
            ("f4:n ((1 2) < 5) 6", 1, "f4:n ((2) < 5) 6"),
        ],
    )
    def test_removed_from_where_it_is_scored(self, line, number, expected):
        t = self._remove(line, number)
        assert montepy.Cell(number=number) not in t
        assert t.mcnp_str().strip() == expected

    def test_removed_from_shortcut_in_union(self):
        t = self._remove("f4:n (1 3i 5)", 3)
        reread = Tally.from_input(t.mcnp_str())
        assert reread.groups[0].old_numbers == [1, 2, 4, 5]
        assert reread.groups[0].is_grouped

    def test_last_union_member_removes_the_union(self):
        t = self._remove("f4:n (2) 6", 2)
        assert [g.old_numbers for g in t.groups] == [[6]]

    def test_only_in_path_raises(self):
        t = Tally.from_input("f4:n (2 < 5)", jit_parse=False)
        with pytest.raises(montepy.exceptions.OnlyInPathError):
            t.remove_cell(montepy.Cell(number=5))
        assert t.mcnp_str() == "f4:n (2 < 5)"

    def test_only_in_path_is_a_value_error(self):
        assert issubclass(montepy.exceptions.OnlyInPathError, ValueError)

    def test_also_in_path_warns(self):
        t = Tally.from_input("f4:n 3 (1 < 3)", jit_parse=False)
        with pytest.warns(montepy.exceptions.PathContainmentWarning):
            t.remove_cell(montepy.Cell(number=3))
        assert t.mcnp_str().strip() == "f4:n (1 < 3)"

    def test_not_in_tally_raises_value_error(self):
        t = Tally.from_input("f4:n 1 2", jit_parse=False)
        with pytest.raises(ValueError) as e:
            t.remove_cell(montepy.Cell(number=9))
        assert not isinstance(e.value, montepy.exceptions.OnlyInPathError)

    def test_linked_cell_removed_from_union(self, tally_problem):
        t = tally_problem.tallies[24]
        cell = tally_problem.cells[1]
        assert cell in t
        t.remove_cell(cell)
        assert cell not in t
        assert cell not in t.cells

    def test_remove_surface_from_union_and_path(self):
        t = Tally.from_input("f2:n (1 2) ((1 3) < 5)", jit_parse=False)
        surface = montepy.surfaces.surface_builder.parse_surface("1 so 1")
        t.remove_surface(surface)
        assert t.mcnp_str().strip() == "f2:n (2) ((3) < 5)"
        with pytest.raises(montepy.exceptions.OnlyInPathError):
            t.remove_surface(montepy.surfaces.surface_builder.parse_surface("5 so 1"))

    @pytest.mark.parametrize("tally_cls", [F4Tally, F1Tally])
    def test_add_path_group_updates_scored_collection(self, tally_cls):
        # Regression test: add_path_group didn't add its innermost items to
        # cells/surfaces until link_to_problem rebuilt them, so an item
        # could be "in" the tally but not in tally.cells.
        if tally_cls is F4Tally:
            items = [montepy.Cell(number=n) for n in (1, 2)]
        else:
            items = [
                montepy.surfaces.surface_builder.parse_surface(f"{n} so 1")
                for n in (1, 2)
            ]
        t = tally_cls()
        pg = t.add_path_group(items[0])
        pg.inside(items[1])
        scored = t.cells if tally_cls is F4Tally else t.surfaces
        assert items[0] in t
        assert items[0] in scored
        # The containment level isn't scored.
        assert items[1] not in scored
        t.remove_group(pg)
        assert items[0] not in scored

    def test_remove_group_keeps_items_other_groups_score(self):
        cells = [montepy.Cell(number=n) for n in (1, 2, 3)]
        t = F4Tally()
        t.add_group(*cells[:2])
        t.add_path_group(cells[1], cells[2])
        t.remove_group(t.groups[0])
        assert cells[0] not in t.cells
        assert cells[1] in t.cells
        assert cells[2] in t.cells


class TestStarModifier:
    """The ``*`` tally modifier (review feedback, PR #1005). Where it changes
    the quantity tallied (``*F1``, ``*F2``, ``*F4``, ``*F8``) it is its own
    class; for ``*F6``/``*F7`` it only changes the units, set by
    ``tally_units``."""

    @pytest.mark.parametrize(
        "line, cls, tally_type, units",
        [
            (
                "*f1:n 1",
                montepy.SurfaceEnergyCurrentTally,
                TallyType.ENERGY_CURRENT,
                "MEV",
            ),
            (
                "*f2:n 1",
                montepy.SurfaceEnergyFluxTally,
                TallyType.SURFACE_ENERGY_FLUX,
                "MEV_PER_CM2",
            ),
            (
                "*f4:n 1",
                montepy.CellEnergyFluxTally,
                TallyType.CELL_ENERGY_FLUX,
                "MEV_PER_CM2",
            ),
            (
                "*f6:n 1",
                montepy.EnergyDepositionTally,
                TallyType.ENERGY_DEPOSITION_JERKS,
                "JERKS_PER_G",
            ),
            (
                "*f7:n 1",
                montepy.FissionEnergyDepositionTally,
                TallyType.FISSION_ENERGY_DEPOSITION_JERKS,
                "JERKS_PER_G",
            ),
            (
                "*f8:p 1",
                montepy.DetectorEnergyDepositionTally,
                TallyType.DETECTOR_ENERGY_DEPOSITION,
                "MEV",
            ),
            (
                "f6:n 1",
                montepy.EnergyDepositionTally,
                TallyType.ENERGY_DEPOSITION,
                "MEV_PER_G",
            ),
            (
                "f8:p 1",
                montepy.EnergyDetectorPulseTally,
                TallyType.ENERGY_DETECTOR_PULSE,
                "PULSES",
            ),
        ],
    )
    def test_dispatch(self, line, cls, tally_type, units):
        t = Tally.from_input(line)
        assert type(t) is cls
        assert t.tally_type is tally_type
        assert t.tally_units is montepy.TallyUnits[units]
        assert t.mcnp_str() == line

    def test_every_tally_type_has_a_class_and_units(self):
        from montepy.data_inputs.tally import _TALLY_TYPE_MAP

        for tally_type in TallyType:
            cls = _TALLY_TYPE_MAP[tally_type]
            assert tally_type in (cls._TALLY_TYPE, *cls._OTHER_TALLY_TYPES)
            assert isinstance(tally_type.units, montepy.TallyUnits)

    @pytest.mark.parametrize("line", ["f6:n 1", "f7:n 1"])
    def test_set_units_switches_star(self, line):
        t = Tally.from_input(line)
        t.tally_units = montepy.TallyUnits.JERKS_PER_G
        assert t.mcnp_str() == "*" + line
        assert (
            Tally.from_input(t.mcnp_str()).tally_units is montepy.TallyUnits.JERKS_PER_G
        )
        t.tally_units = montepy.TallyUnits.MEV_PER_G
        assert t.mcnp_str() == line

    def test_set_units_from_scratch(self):
        t = montepy.EnergyDepositionTally(number=16)
        t.tally_units = montepy.TallyUnits.JERKS_PER_G
        t.add_cell(montepy.Cell(number=1))
        assert t.mcnp_str().startswith("*F16 1")

    @pytest.mark.parametrize(
        "line, units",
        [("f4:n 1", "MEV_PER_CM2"), ("f6:n 1", "MEV"), ("*f8:p 1", "PULSES")],
    )
    def test_set_units_rejects_other_quantities(self, line, units):
        t = Tally.from_input(line)
        with pytest.raises(ValueError):
            t.tally_units = montepy.TallyUnits[units]

    def test_star_with_plus_is_invalid(self):
        with pytest.raises(montepy.exceptions.MalformedInputError):
            Tally.from_input("*+f8:e 1")

    def test_wrong_modifier_for_class_is_invalid(self):
        with pytest.raises(montepy.exceptions.MalformedInputError):
            montepy.CellFluxTally(Input(["*f4:n 1"], BlockType.DATA), jit_parse=False)

    def test_clone_as_uses_target_default_units(self):
        t = Tally.from_input("*f6:n 1")
        new = t.clone_as(montepy.FissionEnergyDepositionTally)
        assert new.tally_units is montepy.TallyUnits.MEV_PER_G
        assert new.mcnp_str().startswith("f7:n")

    @pytest.mark.parametrize(
        "line, new_type, expected",
        [
            # Another class, by type
            ("f4:n 1", "ENERGY_DEPOSITION_JERKS", "*f6:n 1"),
            ("f4:n 1", "FISSION_ENERGY_DEPOSITION_JERKS", "*f7:n 1"),
            # The same class, by type
            ("f6:n 1", "ENERGY_DEPOSITION_JERKS", "*f16:n 1"),
            ("*f6:n 1", "ENERGY_DEPOSITION", "f16:n 1"),
            # A class gives its default type, even for the same class
            ("*f6:n 1", montepy.EnergyDepositionTally, "f16:n 1"),
        ],
    )
    def test_clone_as_keeps_requested_type(self, line, new_type, expected):
        t = Tally.from_input(line)
        if isinstance(new_type, str):
            new_type = TallyType[new_type]
        new = t.clone_as(new_type)
        expected_type = (
            new_type if isinstance(new_type, TallyType) else new_type._TALLY_TYPE
        )
        assert new.tally_type is expected_type
        assert new.tally_units is expected_type.units
        assert new.mcnp_str() == expected

    @pytest.mark.parametrize(
        "line, target",
        [("+f6:n 1", "EnergyDepositionTally"), ("*f6:n 1", "CellFluxTally")],
    )
    def test_removed_modifier_leaves_no_space(self, line, target):
        # Regression test: removing a modifier padded the classifier to the
        # modifier's old width, writing " f16:n 1".
        t = Tally.from_input(line)
        new = t.clone_as(getattr(montepy.data_inputs.tally, target))
        assert new.mcnp_str()[0] == "f"


class TestNestedUnions:
    """A union nested in a union or a path level, e.g. ``(1 (2 3) < 5)``
    (review feedback, PR #1005). These used to be silently dropped from the
    object model."""

    @staticmethod
    def _tally(line):
        return Tally.from_input(line, jit_parse=False)

    @pytest.mark.parametrize(
        "line, numbers",
        [
            ("f4:n (1 (2 3))", [1, 2, 3]),
            ("f4:n ((1 2) (3 4))", [1, 2, 3, 4]),
            ("f4:n (1 (2 (3 4)))", [1, 2, 3, 4]),
        ],
    )
    def test_nested_in_union(self, line, numbers):
        t = self._tally(line)
        group = t.groups[0]
        assert group.is_grouped
        assert group.old_numbers == numbers
        assert all(montepy.Cell(number=n) in t for n in numbers)
        assert t.mcnp_str() == line

    def test_nested_members(self):
        group = self._tally("f4:n (1 (2 3))").groups[0]
        first, nested = group.members
        assert first == 1
        assert isinstance(nested, FlatGroup)
        assert nested.is_grouped
        assert nested.old_numbers == [2, 3]

    def test_nested_in_path_level(self):
        t = self._tally("f4:n (1 (2 3) < 5)")
        inner = t.groups[0].levels[0]
        assert not inner.is_grouped
        assert inner.old_numbers == [1, 2, 3]
        assert montepy.Cell(number=2) in t
        assert montepy.Cell(number=5) not in t
        assert t.mcnp_str() == "f4:n (1 (2 3) < 5)"

    def test_nested_lattice_indices_parallel_old_numbers(self):
        level = self._tally("f4:n (1 < (2[0 0 0] 3) 4 < 5)").groups[0].levels[1]
        assert level.old_numbers == [2, 3, 4]
        assert [i and i.elements for i in level.lattice_indices] == [
            ((0, 0, 0),),
            None,
            None,
        ]

    def test_nested_linked_and_renumbered(self, tally_problem):
        t = Tally.from_input("f44:n (1 (2 3))", jit_parse=False)
        t.link_to_problem(tally_problem)
        assert tally_problem.cells[2] in t.cells
        tally_problem.cells[2].number = 22
        assert t.mcnp_str() == "f44:n (1 (22 3))"

    @pytest.mark.parametrize(
        "line, numbers, expected",
        [
            ("f4:n (1 (2 3))", [2], "f4:n (1 (3))"),
            ("f4:n (1 (2 3))", [2, 3], "f4:n (1)"),
            ("f4:n ((2 3) 1)", [2, 3], "f4:n (1)"),
            ("f4:n (1 (2 3) < 5)", [3], "f4:n (1 (2) < 5)"),
            ("f4:n (1 (2 3) < 5) 6", [1, 2, 3], "f4:n 6"),
        ],
    )
    def test_remove_from_nested(self, line, numbers, expected):
        t = self._tally(line)
        for n in numbers:
            t.remove_cell(montepy.Cell(number=n))
        assert t.mcnp_str().strip() == expected
        assert Tally.from_input(t.mcnp_str()).mcnp_str() == t.mcnp_str()

    def test_path_nested_in_group_unsupported(self):
        with pytest.raises(montepy.exceptions.UnsupportedFeature):
            self._tally("f4:n ((1 < 2) 3)").groups

    @staticmethod
    def _cells(*numbers):
        return [montepy.Cell(number=n) for n in numbers]

    def test_add_group_with_nested_union(self):
        c1, c2, c3, c4, c5 = self._cells(1, 2, 3, 4, 5)
        t = F4Tally()
        t.add_group(c1, [c2, c3], (c4, [c5]))
        group = t.groups[0]
        assert group.old_numbers == [1, 2, 3, 4, 5]
        assert isinstance(group.members[1], FlatGroup)
        assert list(t.cells.numbers) == [1, 2, 3, 4, 5]
        assert all(c in t for c in (c1, c2, c3, c4, c5))
        reread = Tally.from_input(t.mcnp_str())
        nested = reread.groups[0].members
        assert nested[0] == 1
        assert nested[1].old_numbers == [2, 3]
        assert nested[2].old_numbers == [4, 5]
        assert nested[2].members[1].old_numbers == [5]

    def test_add_group_nested_union_is_not_glued(self):
        c1, c2, c3 = self._cells(1, 2, 3)
        t = F4Tally()
        t.add_group([c1, c2], c3)
        assert ") 3" in t.mcnp_str()

    def test_add_group_nested_surfaces(self):
        surfaces = [
            montepy.surfaces.surface_builder.parse_surface(f"{n} so 1")
            for n in (1, 2, 3)
        ]
        t = montepy.SurfaceFluxTally()
        t.add_group(surfaces[0], [surfaces[1], surfaces[2]])
        assert list(t.surfaces.numbers) == [1, 2, 3]
        reread = Tally.from_input(t.mcnp_str())
        assert reread.groups[0].members[1].old_numbers == [2, 3]

    def test_remove_from_built_nested_union(self):
        c1, c2, c3 = self._cells(1, 2, 3)
        t = F4Tally()
        t.add_group(c1, [c2, c3])
        t.remove_cell(c2)
        t.remove_cell(c3)
        assert c2 not in t.cells and c3 not in t.cells
        assert Tally.from_input(t.mcnp_str()).groups[0].members == [1]

    @pytest.mark.parametrize("members", [[], [[]], ["a"], [1]])
    def test_add_group_rejects_bad_members(self, members):
        t = F4Tally()
        with pytest.raises((TypeError, ValueError)):
            t.add_group(*members)
        assert t.groups == []

    def test_add_group_rejects_wrong_kind(self):
        t = montepy.SurfaceFluxTally()
        with pytest.raises(TypeError):
            t.add_group(*self._cells(1))


class TestInsideParsedPath:
    """PathGroup.inside on a path read from an input. It used to add the level
    to the object, but not to the written text."""

    @pytest.mark.parametrize(
        "line, numbers, lattice, expected_levels",
        [
            ("f4:n (1 < 2)", [9], None, [[1], [2], [9]]),
            ("f4:n (1<2)", [9], None, [[1], [2], [9]]),
            ("f4:n (1 < 2) 3", [9, 8], None, [[1], [2], [9, 8]]),
            ("f4:n ((1 2) < (3 4))", [9], [0, 0, 0], [[1, 2], [3, 4], [9]]),
            ("f4:n (1 < 2[0 0 0])", [9], None, [[1], [2], [9]]),
            ("f4:n (1 < u=2)", [9], None, [[1], [], [9]]),
        ],
    )
    def test_inside_is_written(self, line, numbers, lattice, expected_levels):
        t = Tally.from_input(line, jit_parse=False)
        t.groups[0].inside(*[montepy.Cell(number=n) for n in numbers], lattice=lattice)
        reread = Tally.from_input(t.mcnp_str())
        assert [
            level.old_numbers for level in reread.groups[0].levels
        ] == expected_levels
        if lattice is not None:
            index = reread.groups[0].levels[-1].lattice_indices[0]
            assert index.elements == (tuple(lattice),)
        # The rest of the input is unchanged.
        assert t.mcnp_str().startswith(line.split(")")[0])

    def test_inside_on_path_then_remove(self):
        t = Tally.from_input("f4:n (1 < 2)", jit_parse=False)
        t.groups[0].inside(montepy.Cell(number=9))
        t.remove_cell(montepy.Cell(number=1))
        assert t.groups == []

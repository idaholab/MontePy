# Copyright 2024-2025, Battelle Energy Alliance, LLC All Rights Reserved.
import io
import warnings

import pytest

import montepy
from montepy.data_inputs.data_parser import parse_data
from montepy.data_inputs.tally_multiplier import (
    AttenuatorLayer,
    AttenuatorSet,
    MultiplierBin,
    MultiplierScore,
    MultiplierSet,
    Reaction,
    SpecialMultiplierSet,
    TallyMultiplier,
)
from montepy.data_inputs.tally_multiplier_type import (
    ReactionOperator,
    SpecialMultiplier,
)
from montepy.data_inputs.tally_type import Score
from montepy.input_parser.block_type import BlockType
from montepy.input_parser.mcnp_input import Input


@pytest.fixture
def tally_problem():
    return montepy.read_input("tests/inputs/test_tally.imcnp")


# Every "fm" line currently in tests/inputs/test_tally.imcnp, kept in sync
# with that fixture so the grammar round-trip test below actually exercises
# what's on disk.
FM_FIXTURE_LINES = [
    "fm4 (1.0)",
    "fm14 (1.0 1 -6)",
    "fm44 (1.0 1 444)",
    "fm54:n (1.0 26 (16) (103))",
    "fm64:n ((1.0 26 16) (2.0 27 102))",
    "fm74:n (1.0 26 16 103)",
    "fm84:n (1.0 26 16:103)",
    "fm94:n (1.0 26 16#103)",
    "fm104:n (1.0 26 16 103 : 104)",
    "fm204:n (1.0 26 16 : 103 104)",
    "fm214:n (1.0 26 16 103 : 104 105)",
    "fm224:n (1.0 26 16 # 103 104)",
    "fm234:n (1.0 26 16 103 # 104)",
    "fm244:n (1.0 26 16 : 103 # 104 105)",
    "fm254:n (1.0 26 16 103 : 104 # 105 106)",
    "fm264:n (1.0 26 16 # 103 : 104 105)",
    "fm114:n (1.0 -1 26 0.5)",
    "fm124:n (1.0 -1 26 0.5 27 -0.3)",
    "fm134:n ((1.0 26 16) (2.0 27 102) (3.0 -1 28 0.1))",
    "fm144:n (-1.0 26 103)",
    "fm154:n 1 -1",
    "fm164:n (1 -2)",
    "fm174:n (1 -3)",
    "fm184:n (1.0 26 16) (2.0 27 102) T",
    "fm194:n (1.0 26 16) (2.0 27 102) C",
]


class TestGrammar:
    """Locks in the tally_parser.py grammar fix: reaction-list operators
    (space/colon/COMPLEMENT) and the C (cumulative) end flag must parse
    outside of lattice-index brackets.
    """

    @pytest.mark.parametrize("line", FM_FIXTURE_LINES)
    def test_fm_line_full_parses(self, line):
        data = parse_data(Input([line], BlockType.DATA))
        data.full_parse()  # must not raise ParsingError
        assert isinstance(data, TallyMultiplier)

    def test_mixed_particle_classifier(self):
        # fm4 has no particle designator; fm54:n does. DataInputAbstract's
        # __enforce_name rejects a classifier mismatch, so both must be
        # legal -- regression test for _has_classifier() == 1, not 0.
        for line in ["fm4 (1.0)", "fm54:n (1.0 26 (16) (103))"]:
            data = parse_data(Input([line], BlockType.DATA))
            data.full_parse()


class TestReactionExpressionPrecedence:
    @pytest.mark.parametrize(
        "number, expected",
        [
            (104, Reaction(16) * Reaction(103) + Reaction(104)),
            (204, Reaction(16) + Reaction(103) * Reaction(104)),
            (214, Reaction(16) * Reaction(103) + Reaction(104) * Reaction(105)),
            (224, Reaction(16) - Reaction(103) * Reaction(104)),
            (234, Reaction(16) * Reaction(103) - Reaction(104)),
            (244, Reaction(16) + Reaction(103) - Reaction(104) * Reaction(105)),
            (
                254,
                Reaction(16) * Reaction(103)
                + Reaction(104)
                - Reaction(105) * Reaction(106),
            ),
            (264, Reaction(16) - Reaction(103) + Reaction(104) * Reaction(105)),
        ],
    )
    def test_precedence_matches_hand_built_expression(
        self, tally_problem, number, expected
    ):
        fm = tally_problem.tallies[number].multiplier
        [reaction] = fm.bins[0].terms[0].reactions
        assert reaction == expected


class TestOperatorOverloading:
    def test_multiply_binds_tighter_than_add(self):
        expr = Reaction(16) * Reaction(103) + Reaction(104)
        assert expr.left == Reaction(16) * Reaction(103)
        assert expr.operator == ReactionOperator.ADD
        assert expr.right == Reaction(104)

    def test_int_first_forms(self):
        assert 16 * Reaction(103) == Reaction(16) * Reaction(103)
        assert 16 + Reaction(103) == Reaction(16) + Reaction(103)

    def test_rsub_swaps_operand_order(self):
        # 16 - Reaction(103) must be Reaction(16) - Reaction(103), not the reverse.
        expr = 16 - Reaction(103)
        assert expr.left == Reaction(16)
        assert expr.right == Reaction(103)

    def test_rand_builds_multiplier_set(self):
        built = 26 & Reaction.CAPTURE
        assert built == MultiplierSet(1.0, 26, [Reaction.CAPTURE])

    def test_rand_with_material_object(self):
        mat = montepy.Material()
        mat.number = 26
        built = mat & Reaction.CAPTURE
        assert built == MultiplierSet(1.0, 26, [Reaction.CAPTURE])

    def test_rmul_scales_constant(self):
        built = 1.5 * (26 & Reaction.CAPTURE)
        assert built == MultiplierSet(1.5, 26, [Reaction.CAPTURE])

    def test_named_reaction_constants_compose(self):
        expr = Reaction.TOTAL - Reaction.CAPTURE - Reaction.INELASTIC_SCATTER
        assert expr.left == Reaction.TOTAL - Reaction.CAPTURE
        assert expr.right == Reaction.INELASTIC_SCATTER
        assert expr.operator == ReactionOperator.SUBTRACT

    def test_named_reaction_constants_are_unique(self):
        constants = {
            name: obj
            for name, obj in vars(Reaction).items()
            if isinstance(obj, Reaction)
        }
        # sanity: this should have picked up more than just a handful,
        # confirming the Appendix B transcription actually landed.
        assert len(constants) > 400
        numbers_seen = {}
        for name, reaction in constants.items():
            if reaction.number in numbers_seen:
                pytest.fail(
                    f"Reaction.{name} (MT {reaction.number}) collides with "
                    f"Reaction.{numbers_seen[reaction.number]}"
                )
            numbers_seen[reaction.number] = name


class TestAttenuator:
    def test_and_chains_layers(self):
        att = AttenuatorSet(1.0, [AttenuatorLayer(3, 0.05)])
        att = att & AttenuatorLayer(4, 0.1, is_atom_density=False)
        assert att.layers == [
            AttenuatorLayer(3, 0.05),
            AttenuatorLayer(4, 0.1, is_atom_density=False),
        ]

    def test_and_chains_attenuator_sets(self):
        left = AttenuatorSet(1.0, [AttenuatorLayer(3, 0.05)])
        right = AttenuatorSet(1.0, [AttenuatorLayer(4, 0.1)])
        combined = left & right
        assert combined.layers == [AttenuatorLayer(3, 0.05), AttenuatorLayer(4, 0.1)]

    def test_single_layer_from_fixture(self, tally_problem):
        fm = tally_problem.tallies[114].multiplier
        assert fm.bins[0].attenuator == AttenuatorSet(1.0, [AttenuatorLayer(26, 0.5)])

    def test_multi_layer_from_fixture_normalizes_sign(self, tally_problem):
        fm = tally_problem.tallies[124].multiplier
        attenuator = fm.bins[0].attenuator
        assert attenuator.layers[0] == AttenuatorLayer(26, 0.5, is_atom_density=True)
        assert attenuator.layers[1] == AttenuatorLayer(27, 0.3, is_atom_density=False)
        # sign is normalized away -- areal_density is always positive
        assert attenuator.layers[1].areal_density == 0.3


class TestCompanionCardLinking:
    def test_multiplier_is_linked(self, tally_problem):
        assert tally_problem.tallies[4].multiplier is not None
        assert (
            tally_problem.tallies[4].multiplier.parent_tally is tally_problem.tallies[4]
        )

    def test_multiplier_is_none_without_fm(self, tally_problem):
        assert tally_problem.tallies[1].multiplier is None
        assert tally_problem.tallies[2].multiplier is None
        assert tally_problem.tallies[6].multiplier is None

    def test_orphaned_fm_raises(self):
        problem = montepy.MCNP_Problem(None)
        fm = TallyMultiplier(Input(["fm999 (1.0)"], BlockType.DATA), jit_parse=False)
        problem.tallies.append(fm)
        with pytest.raises(montepy.exceptions.MalformedInputError):
            problem.tallies.finalize_init()

    def test_appended_fm_registers_in_data_inputs(self):
        problem = montepy.MCNP_Problem(None)
        tally = parse_data(Input(["f4:n 1 2 3"], BlockType.DATA))
        problem.tallies.append(tally)
        fm = TallyMultiplier(
            Input(["fm4 (1.0 26 16)"], BlockType.DATA), jit_parse=False
        )
        problem.tallies.append(fm)
        assert fm in problem.data_inputs
        assert fm in problem.tallies.multipliers
        assert tally.multiplier is fm
        assert fm.parent_tally is tally

    def test_multiplier_setter_registers_in_data_inputs(self):
        problem = montepy.MCNP_Problem(None)
        tally = parse_data(Input(["f4:n 1 2 3"], BlockType.DATA))
        problem.tallies.append(tally)
        fm = TallyMultiplier(
            Input(["fm4 (1.0 26 16)"], BlockType.DATA), jit_parse=False
        )
        tally.multiplier = fm
        assert fm in problem.data_inputs
        assert fm.parent_tally is tally

    def test_appended_fm_survives_full_problem_export(self):
        problem = montepy.MCNP_Problem(None)
        problem.title = "test problem"
        tally = parse_data(Input(["f4:n 1 2 3"], BlockType.DATA))
        problem.tallies.append(tally)
        fm = TallyMultiplier(
            Input(["fm4 (1.0 26 16)"], BlockType.DATA), jit_parse=False
        )
        problem.tallies.append(fm)
        with io.StringIO() as fh:
            problem.write_problem(fh)
            fh.seek(0)
            new_problem = montepy.read_input(fh)
        new_fm = new_problem.tallies[4].multiplier
        assert new_fm is not None
        assert new_fm.bins[0].terms[0].material == 26


class TestScoresIntegration:
    def test_scores_reflects_multiplier_as_first_touch(self, tally_problem):
        # This must be the *first* @needs_full_ast touch on this object --
        # regression test for the _KEYS_TO_PRESERVE bug where the FM link
        # vanished the moment full_parse() ran.
        f4 = tally_problem.tallies[4]
        assert not f4.fully_parsed
        scores = f4.scores
        assert scores == [MultiplierScore(1.0, None, None, None, None)]

    def test_scores_falls_back_to_default_without_multiplier(self, tally_problem):
        assert tally_problem.tallies[2].scores == [Score.FLUX]

    def test_scores_for_multi_bin_multiplier(self, tally_problem):
        f64 = tally_problem.tallies[64]
        scores = f64.scores
        assert scores == [
            MultiplierScore(1.0, 26, Reaction(16), None, None),
            MultiplierScore(2.0, 27, Reaction(102), None, None),
        ]

    def test_scores_for_special_multiplier(self, tally_problem):
        f154 = tally_problem.tallies[154]
        assert f154.scores == [
            MultiplierScore(1.0, None, None, SpecialMultiplier.INVERSE_WEIGHT, None)
        ]

    def test_scores_carry_attenuator(self, tally_problem):
        f134 = tally_problem.tallies[134]
        attenuator = f134.multiplier.bins[0].attenuator
        assert f134.scores == [
            MultiplierScore(1.0, 26, Reaction(16), None, attenuator),
            MultiplierScore(2.0, 27, Reaction(102), None, attenuator),
        ]

    def test_clone_as_does_not_carry_multiplier(self, tally_problem):
        from montepy.data_inputs.tally import F6Tally

        f4 = tally_problem.tallies[4]
        assert f4.multiplier is not None
        new = f4.clone_as(F6Tally)
        assert new.multiplier is None
        assert new.scores == [Score.ENERGY_DEPOSITION]

    def test_clone_does_not_carry_multiplier(self, tally_problem):
        f4 = tally_problem.tallies[4]
        clone = f4.clone()
        assert clone.multiplier is None


class TestFlags:
    def test_include_total_and_cumulative_flags(self, tally_problem):
        assert tally_problem.tallies[184].multiplier.include_total is True
        assert tally_problem.tallies[184].multiplier.cumulative is False
        assert tally_problem.tallies[194].multiplier.include_total is False
        assert tally_problem.tallies[194].multiplier.cumulative is True

    def test_attenuator_only_bin_scores(self, tally_problem):
        fm = tally_problem.tallies[114].multiplier
        attenuator = fm.bins[0].attenuator
        assert tally_problem.tallies[114].scores == [
            MultiplierScore(1.0, None, None, None, attenuator)
        ]


class TestParseTermEdgeCases:
    def test_material_with_no_reaction_list(self):
        fm = TallyMultiplier(Input(["fm999 (1.0 26)"], BlockType.DATA), jit_parse=False)
        assert fm.bins[0].terms[0] == MultiplierSet(1.0, 26, [])

    def test_coerce_type_error(self):
        with pytest.raises(TypeError):
            Reaction(16) + "not a reaction"


class TestDuplicateFmCards:
    def test_duplicate_fm_cards_warn(self):
        problem = montepy.MCNP_Problem(None)
        tally = parse_data(Input(["f4:n 1 2 3"], BlockType.DATA))
        problem.tallies.append(tally)
        fm1 = TallyMultiplier(Input(["fm4 (1.0)"], BlockType.DATA), jit_parse=False)
        fm2 = TallyMultiplier(Input(["fm4 (2.0)"], BlockType.DATA), jit_parse=False)
        problem.tallies.append(fm1)
        with pytest.warns(montepy.exceptions.MalformedInputWarning):
            problem.tallies.append(fm2)

    def test_deleting_tally_cascades_to_multiplier(self):
        problem = montepy.MCNP_Problem(None)
        tally = parse_data(Input(["f4:n 1 2 3"], BlockType.DATA))
        problem.tallies.append(tally)
        fm = TallyMultiplier(
            Input(["fm4 (1.0 26 16)"], BlockType.DATA), jit_parse=False
        )
        problem.tallies.append(fm)
        with pytest.warns(montepy.exceptions.MalformedInputWarning):
            del problem.tallies[4]
        assert fm not in problem.data_inputs
        assert fm not in problem.tallies.multipliers
        assert fm.parent_tally is None

    def test_deleting_tally_without_multiplier_does_not_warn(self):
        problem = montepy.MCNP_Problem(None)
        tally = parse_data(Input(["f4:n 1 2 3"], BlockType.DATA))
        problem.tallies.append(tally)
        with warnings.catch_warnings():
            warnings.simplefilter("error")
            del problem.tallies[4]
        assert tally not in problem.data_inputs

    def test_renumbering_tally_syncs_multiplier_number(self):
        problem = montepy.MCNP_Problem(None)
        tally = parse_data(Input(["f4:n 1 2 3"], BlockType.DATA))
        problem.tallies.append(tally)
        fm = TallyMultiplier(
            Input(["fm4 (1.0 26 16)"], BlockType.DATA), jit_parse=False
        )
        problem.tallies.append(fm)
        tally.number = 14
        assert fm.number == 14


class TestBlankConstruction:
    def test_blank_tally_multiplier_construction(self):
        fm = TallyMultiplier()
        assert fm.bins == []
        assert str(fm)
        assert repr(fm)

    def test_str_and_repr_on_uninitialized_tally_multiplier(self):
        # __new__ bypasses __init__ entirely -- exactly the partially
        # constructed state __str__/__repr__'s except branches exist to
        # report gracefully.
        fm = TallyMultiplier.__new__(TallyMultiplier)
        assert str(fm) == "TallyMultiplier: (unparsed)"
        assert repr(fm) == "TALLY MULTIPLIER: (unparsed)"


class TestReprAndEquality:
    """Smoke tests for __repr__, __eq__-against-wrong-type, and otherwise
    unexercised property getters across the tally_multiplier.py value
    objects. Coverage only counts a line as hit if it executes, and pytest
    only reprs on assertion *failure*, so these branches need explicit
    exercising; likewise the existing tests only ever compare MultiplierScore
    via == (which reads the private attributes directly), never through its
    public properties."""

    def test_reaction_expression_eq_wrong_type_and_repr(self):
        expr = Reaction(16) * Reaction(103)
        assert expr != "not an expression"
        assert "ReactionExpression" in repr(expr)

    def test_reaction_number_and_eq_wrong_type_and_repr(self):
        r = Reaction(16)
        assert r.number == 16
        assert r != "not a reaction"
        assert repr(r) == "Reaction(16)"

    def test_attenuator_layer_material_and_eq_wrong_type_and_repr(self):
        layer = AttenuatorLayer(26, 0.5)
        assert layer.material == 26
        assert layer.is_atom_density is True
        assert layer != "not a layer"
        assert "AttenuatorLayer" in repr(layer)

    def test_attenuator_set_constant_and_eq_wrong_type_and_repr(self):
        att = AttenuatorSet(1.0, [AttenuatorLayer(26, 0.5)])
        assert att.constant == 1.0
        assert att != "not an attenuator set"
        assert "AttenuatorSet" in repr(att)

    def test_multiplier_set_eq_wrong_type_and_repr(self):
        ms = MultiplierSet(1.0, 26, [Reaction(16)])
        assert ms != "not a multiplier set"
        assert "MultiplierSet" in repr(ms)

    def test_special_multiplier_set_eq_wrong_type_and_repr(self):
        sms = SpecialMultiplierSet(1.0, SpecialMultiplier.INVERSE_WEIGHT)
        assert sms == SpecialMultiplierSet(1.0, SpecialMultiplier.INVERSE_WEIGHT)
        assert sms != "not a special multiplier set"
        assert "SpecialMultiplierSet" in repr(sms)

    def test_multiplier_score_properties_eq_wrong_type_and_repr(self):
        attenuator = AttenuatorSet(1.0, [AttenuatorLayer(26, 0.5)])
        score = MultiplierScore(
            1.0, 26, Reaction(16), SpecialMultiplier.INVERSE_WEIGHT, attenuator
        )
        assert score.constant == 1.0
        assert score.material == 26
        assert score.reaction == Reaction(16)
        assert score.kind == SpecialMultiplier.INVERSE_WEIGHT
        assert score.attenuator == attenuator
        assert score != "not a score"
        assert "MultiplierScore" in repr(score)

    def test_multiplier_bin_eq_wrong_type_and_repr(self):
        mb = MultiplierBin([MultiplierSet(1.0, 26, [Reaction(16)])])
        assert mb == MultiplierBin([MultiplierSet(1.0, 26, [Reaction(16)])])
        assert mb != "not a bin"
        assert "MultiplierBin" in repr(mb)

    def test_parent_collections(self):
        assert TallyMultiplier._parent_collections() == ()


class TestBinRoundTrip:
    """Mutating a TallyMultiplier's bins through the public API must be
    reflected in mcnp_str(), not just in the in-memory Python state."""

    @pytest.mark.parametrize("line", FM_FIXTURE_LINES)
    def test_unmodified_fm_round_trips_exactly(self, line):
        fm = TallyMultiplier(Input([line], BlockType.DATA), jit_parse=False)
        assert fm.mcnp_str() == line
        fm.full_parse()
        assert fm.mcnp_str() == line

    def test_add_bin_reflected_in_mcnp_str(self):
        fm = TallyMultiplier(
            Input(["fm4 (1.0 26 16)"], BlockType.DATA), jit_parse=False
        )
        fm.add_bin(MultiplierBin([MultiplierSet(2.0, 27, [Reaction(102)])]))
        text = fm.mcnp_str()
        assert "27" in text and "102" in text and "2.0" in text

    def test_blank_fm_add_bin_writes_valid_card(self):
        fm = TallyMultiplier()
        fm.number = 4
        fm.add_bin(MultiplierBin([MultiplierSet(1.0, 26, [Reaction(16)])]))
        text = fm.mcnp_str()
        assert "26" in text and "16" in text

    def test_remove_bin(self):
        fm = TallyMultiplier(
            Input(["fm4 (1.0 26 16)"], BlockType.DATA), jit_parse=False
        )
        bin_ = MultiplierBin([MultiplierSet(2.0, 27, [Reaction(102)])])
        fm.add_bin(bin_)
        fm.remove_bin(bin_)
        assert bin_ not in fm.bins
        text = fm.mcnp_str()
        assert "27" not in text

    def test_multiplier_set_material_object_resolves_live(self):
        mat = montepy.Material()
        mat.number = 26
        built = mat & Reaction.N_2N
        fm = TallyMultiplier()
        fm.number = 4
        fm.add_bin(MultiplierBin([built]))
        assert "26" in fm.mcnp_str()
        mat.number = 99
        text = fm.mcnp_str()
        assert "99" in text
        assert "26" not in text
        assert built.material == 99

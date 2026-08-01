# Copyright 2024-2025, Battelle Energy Alliance, LLC All Rights Reserved.
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
    ReactionNumber,
    SpecialMultiplierSet,
    TallyMultiplier,
)
from montepy.data_inputs.tally_multiplier_type import ReactionOperator, SpecialMultiplier
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
                Reaction(16) * Reaction(103) + Reaction(104) - Reaction(105) * Reaction(106),
            ),
            (264, Reaction(16) - Reaction(103) + Reaction(104) * Reaction(105)),
        ],
    )
    def test_precedence_matches_hand_built_expression(self, tally_problem, number, expected):
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
        built = 26 & ReactionNumber.CAPTURE
        assert built == MultiplierSet(1.0, 26, [ReactionNumber.CAPTURE])

    def test_rand_with_material_object(self):
        mat = montepy.Material()
        mat.number = 26
        built = mat & ReactionNumber.CAPTURE
        assert built == MultiplierSet(1.0, 26, [ReactionNumber.CAPTURE])

    def test_rmul_scales_constant(self):
        built = 1.5 * (26 & ReactionNumber.CAPTURE)
        assert built == MultiplierSet(1.5, 26, [ReactionNumber.CAPTURE])

    def test_reaction_number_dsl_composes(self):
        expr = ReactionNumber.TOTAL - ReactionNumber.CAPTURE - ReactionNumber.INELASTIC_SCATTER
        assert expr.left == ReactionNumber.TOTAL - ReactionNumber.CAPTURE
        assert expr.right == ReactionNumber.INELASTIC_SCATTER
        assert expr.operator == ReactionOperator.SUBTRACT


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
        assert tally_problem.tallies[4].multiplier.parent_tally is tally_problem.tallies[4]

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

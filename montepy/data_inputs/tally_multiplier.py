# Copyright 2024, Battelle Energy Alliance, LLC All Rights Reserved.
from __future__ import annotations
import copy
import warnings
from typing import Union

import montepy
from montepy.data_inputs.data_input import DataInputAbstract
from montepy.data_inputs.tally_multiplier_type import (
    ReactionOperator,
    SpecialMultiplier,
)
from montepy.exceptions import MalformedInputWarning
from montepy.input_parser.tally_parser import TallyParser
from montepy.input_parser import syntax_node
from montepy.numbered_mcnp_object import Numbered_MCNP_Object
import montepy.types as ty
from montepy.utilities import *
from montepy.mcnp_object import InitInput

_SPECIAL_KIND_MAP = {
    -1: SpecialMultiplier.INVERSE_WEIGHT,
    -2: SpecialMultiplier.INVERSE_VELOCITY,
    -3: SpecialMultiplier.FIRST_INTERACTION_XS,
}
_SPECIAL_KIND_MAP_INVERSE = {v: k for k, v in _SPECIAL_KIND_MAP.items()}


def _make_value_node(value_type, default, padding=" ", never_pad=False):
    padding_node = syntax_node.PaddingNode(padding) if padding else None
    if default is None:
        return syntax_node.ValueNode(default, value_type, padding_node, never_pad)
    return syntax_node.ValueNode(str(default), value_type, padding_node, never_pad)


def _coerce(value) -> ReactionExpression:
    """Wrap a bare ``int`` reaction number in a :class:`Reaction`, or pass through."""
    if isinstance(value, ReactionExpression):
        return value
    if isinstance(value, ty.Integral):
        return Reaction(int(value))
    raise TypeError(f"Cannot combine a reaction expression with {value!r}.")


class ReactionExpression:
    """A binary expression tree for one FM reaction list.

    Modeled on :class:`montepy.surfaces.half_space.HalfSpace`
    (``left``/``operator``/``right``, ``&``/``|``/``~`` there → ``*``/``+``/``-``
    here). Python's own operator precedence (``*`` binds tighter than
    ``+``/``-``) gives MCNP's "multiply first" reaction-list rule for free:
    ``Reaction(16) * Reaction(103) + Reaction(104)`` builds ``(16*103) + 104``
    with no custom precedence-climbing code.

    .. versionadded:: 1.6.0b2
    """

    def __init__(
        self,
        left: ReactionExpression,
        operator: ReactionOperator,
        right: ReactionExpression,
    ):
        self._left = left
        self._operator = operator
        self._right = right
        self._node = None

    @property
    def node(self) -> syntax_node.ListNode:
        """The syntax node for this reaction expression.

        .. versionadded:: 1.6.0b3
        """
        self._ensure_has_node()
        return self._node

    def _ensure_has_node(self):
        if self._node is not None:
            return
        node = syntax_node.ListNode("reaction expr")
        for n in self.left.node.nodes:
            node.append(n)
        if self._operator != ReactionOperator.MULTIPLY:
            symbol = ":" if self._operator == ReactionOperator.ADD else "#"
            node.append(_make_value_node(str, symbol, padding=" "))
        for n in self.right.node.nodes:
            node.append(n)
        self._node = node

    @make_prop_pointer("_left")
    def left(self):
        """The left side of this expression."""
        pass

    @make_prop_pointer("_operator")
    def operator(self):
        """The :class:`~montepy.data_inputs.tally_multiplier_type.ReactionOperator` joining the two sides."""
        pass

    @make_prop_pointer("_right")
    def right(self):
        """The right side of this expression."""
        pass

    def __mul__(self, other) -> ReactionExpression:
        return ReactionExpression(self, ReactionOperator.MULTIPLY, _coerce(other))

    def __add__(self, other) -> ReactionExpression:
        return ReactionExpression(self, ReactionOperator.ADD, _coerce(other))

    def __sub__(self, other) -> ReactionExpression:
        return ReactionExpression(self, ReactionOperator.SUBTRACT, _coerce(other))

    def __rmul__(self, other) -> ReactionExpression:
        # Not a plain alias to __mul__: that would put ``self`` on the left,
        # reversing the operand order implied by e.g. ``16 * Reaction(103)``.
        return ReactionExpression(_coerce(other), ReactionOperator.MULTIPLY, self)

    def __radd__(self, other) -> ReactionExpression:
        return ReactionExpression(_coerce(other), ReactionOperator.ADD, self)

    def __rsub__(self, other) -> ReactionExpression:
        return ReactionExpression(_coerce(other), ReactionOperator.SUBTRACT, self)

    def __rand__(
        self, material: Union[ty.Integral, "montepy.Material"]
    ) -> MultiplierSet:
        """``material_or_number & reaction_expr`` -> a one-term :class:`MultiplierSet`.

        Defined here so both leaves and composite trees support it via
        inheritance: ``mat1 & Reaction.CAPTURE`` and
        ``26 & (Reaction.CAPTURE - Reaction.INELASTIC_SCATTER)`` both work,
        building a single-reaction :class:`MultiplierSet` with
        ``constant=1.0``. Scale it with ``*`` afterwards (see
        ``MultiplierSet.__rmul__``) or drop it straight into a
        :class:`~montepy.data_inputs.tally_multiplier.MultiplierBin`'s
        ``terms`` list.
        """
        return MultiplierSet(1.0, material, [self])

    def __eq__(self, other):
        if not isinstance(other, ReactionExpression):
            return NotImplemented
        return (
            self._left == other._left
            and self._operator == other._operator
            and self._right == other._right
        )

    def __repr__(self):
        return f"ReactionExpression({self._left!r}, {self._operator}, {self._right!r})"


class Reaction(ReactionExpression):
    """A leaf reaction number: a single ENDF (MT) or special (R) reaction.

    Does **not** call ``ReactionExpression.__init__`` — mirrors
    ``UnitHalfSpace``, which holds independent leaf state rather than being a
    degenerate composite node pointing at itself. Inherits
    ``__mul__``/``__add__``/``__sub__``/``__rand__`` from
    :class:`~montepy.data_inputs.tally_multiplier.ReactionExpression` unchanged;
    only ``__eq__``/``__repr__`` need leaf-specific overrides.

    Common reaction numbers are available as ready-to-use class attributes,
    e.g. ``Reaction.CAPTURE``, so you don't need to remember that capture is
    MT 102. These are not exhaustive or closed — any other MT/reaction
    number still works via ``Reaction(n)`` directly; the class attributes
    are just a convenience for the common ones. ``Reaction.CAPTURE`` is MT
    102, (n,gamma) radiative capture. ``Reaction.RADIATION_DAMAGE`` and its
    ``RADIATION_DAMAGE_*`` siblings are NJOY HEATR-computed
    displacement-damage energies, not standard ENDF physics MTs, split the
    same way ENDF splits total/elastic/inelastic/capture. A handful of other
    constants (``AVERAGE_LETHARGY``, ``INVERSE_VELOCITY``, ``WEIGHTING_FLUX``,
    ``PHOTON_HEATING``, ``KINEMATIC_KERMA``, ``FISSION_STEADY_STATE_SPECTRUM``,
    ``FISSION_DELAYED_SPECTRUM``) are likewise NJOY-module-specific "MT"
    identifiers (from GROUPR, HEATR, and DTFR) rather than official ENDF-6
    reaction numbers. The negative aliases (``TOTAL_MCNP``, ``ABSORPTION``,
    etc.) are MCNP's own special reaction-number aliases, computed directly
    from transport data rather than corresponding to a single ENDF MT
    channel.

    .. versionadded:: 1.6.0b2
    """

    def __init__(self, number: int):
        self._number = number
        self._left = None
        self._operator = None
        self._right = None
        self._node = None

    @property
    def number(self) -> int:
        """The raw ENDF (MT) or special (R) reaction number."""
        return self._number

    def _ensure_has_node(self):
        if self._node is None:
            node = syntax_node.ListNode("reaction expr")
            node.append(_make_value_node(int, self._number, padding=" "))
            self._node = node

    def __eq__(self, other):
        if not isinstance(other, Reaction):
            return NotImplemented
        return self._number == other._number

    def __repr__(self):
        return f"Reaction({self._number})"


# Common reaction numbers as ready-to-use Reaction instances, attached here
# rather than in the class body above, since `Reaction` isn't bound as a
# name until the class statement finishes executing.

# ENDF MT numbers (positive; direct ENDF cross-section channel)
Reaction.TOTAL = Reaction(1)
Reaction.ELASTIC = Reaction(2)
Reaction.INELASTIC_SCATTER = Reaction(4)
Reaction.N_2N = Reaction(16)
Reaction.N_3N = Reaction(17)
Reaction.FISSION = Reaction(18)
Reaction.CAPTURE = Reaction(102)
Reaction.N_P = Reaction(103)
Reaction.N_D = Reaction(104)
Reaction.N_T = Reaction(105)
Reaction.N_HE3 = Reaction(106)
Reaction.N_ALPHA = Reaction(107)

# NJOY HEATR radiation-damage-energy family.
Reaction.RADIATION_DAMAGE = Reaction(444)
Reaction.RADIATION_DAMAGE_ELASTIC = Reaction(445)
Reaction.RADIATION_DAMAGE_INELASTIC = Reaction(446)
Reaction.RADIATION_DAMAGE_DISAPPEARANCE = Reaction(447)

# Other NJOY-module-specific "MT" identifiers that aren't official ENDF-6
# reaction numbers (transcribed from the NJOY2016 manual, LA-UR-17-20093):
# GROUPR's special mtd values for slowing-down-moment group constants,
# HEATR's mtk values for heating diagnostics, and DTFR's special edit MTs
# for its DTF-format multigroup edits.
Reaction.AVERAGE_LETHARGY = Reaction(258)
Reaction.INVERSE_VELOCITY = Reaction(259)
Reaction.WEIGHTING_FLUX = Reaction(300)
Reaction.PHOTON_HEATING = Reaction(442)
Reaction.KINEMATIC_KERMA = Reaction(443)
Reaction.FISSION_STEADY_STATE_SPECTRUM = Reaction(470)
Reaction.FISSION_DELAYED_SPECTRUM = Reaction(471)

# MCNP's own special reaction-number aliases (negative; computed directly
# from transport data, not a single ENDF MT channel).
Reaction.TOTAL_MCNP = Reaction(-1)
Reaction.ABSORPTION = Reaction(-2)
Reaction.ELASTIC_MCNP = Reaction(-3)
Reaction.HEATING = Reaction(-4)
Reaction.PHOTON_PRODUCTION = Reaction(-5)
Reaction.FISSION_MCNP = Reaction(-6)

# The remaining constants below cover every other officially-assigned
# ENDF-6 MT number from Appendix B of the ENDF-6 Formats Manual, transcribed
# directly from that appendix. Skipped: MT numbers Appendix B marks
# "(Unassigned)" or "Not allowed in Version 6"; MT 6-9, 26, 31, 39, 40, 46-49,
# 120, 465-466 (old Version-5-only assignments); MT 301-450 (a formulaic
# "MT=300+reaction" energy-release/KERMA transform over the other reaction
# MTs, not itself a set of individually-assigned reactions); MT 451 (File 1
# heading/title metadata, not a cross section); and MT 851-870 ("Lumped
# reaction covariances", a covariance grouping rather than a reaction).

# Redundant summary / total-type cross sections.
Reaction.NONELASTIC = Reaction(3)
Reaction.ANYTHING = Reaction(5)
Reaction.TOTAL_CONTINUUM = Reaction(10)
Reaction.TOTAL_ABSORPTION = Reaction(27)

# Partial (chance) fission cross sections; sum to Reaction.FISSION.
Reaction.FISSION_FIRST_CHANCE = Reaction(19)
Reaction.FISSION_SECOND_CHANCE = Reaction(20)
Reaction.FISSION_THIRD_CHANCE = Reaction(21)
Reaction.FISSION_FOURTH_CHANCE = Reaction(38)

# Exclusive multi-particle-emission channels (single/few discrete exit
# channels, as opposed to the summed families like N_P above).
Reaction.N_2N_D = Reaction(11)
Reaction.N_N_ALPHA = Reaction(22)
Reaction.N_N_3ALPHA = Reaction(23)
Reaction.N_2N_ALPHA = Reaction(24)
Reaction.N_3N_ALPHA = Reaction(25)
Reaction.N_N_P = Reaction(28)
Reaction.N_N_2ALPHA = Reaction(29)
Reaction.N_2N_2ALPHA = Reaction(30)
Reaction.N_N_D = Reaction(32)
Reaction.N_N_T = Reaction(33)
Reaction.N_N_HE3 = Reaction(34)
Reaction.N_N_D_2ALPHA = Reaction(35)
Reaction.N_N_T_2ALPHA = Reaction(36)
Reaction.N_4N = Reaction(37)
Reaction.N_2N_P = Reaction(41)
Reaction.N_3N_P = Reaction(42)
Reaction.N_N_2P = Reaction(44)
Reaction.N_N_P_ALPHA = Reaction(45)
Reaction.N_2ALPHA = Reaction(108)
Reaction.N_3ALPHA = Reaction(109)
Reaction.N_2P = Reaction(111)
Reaction.N_P_ALPHA = Reaction(112)
Reaction.N_T_2ALPHA = Reaction(113)
Reaction.N_D_2ALPHA = Reaction(114)
Reaction.N_P_D = Reaction(115)
Reaction.N_P_T = Reaction(116)
Reaction.N_D_ALPHA = Reaction(117)

# Neutron disappearance (capture-like absorption, excludes fission).
Reaction.NEUTRON_DISAPPEARANCE = Reaction(101)

# Resonance-parameter data (File 2); incident neutrons only.
Reaction.RESONANCE_PARAMETERS = Reaction(151)

# High-energy multi-particle-emission open channels, allocated to cover
# all reaction channels (within +/-10 mb) up to 60 MeV incident energy.
Reaction.N_5N = Reaction(152)
Reaction.N_6N = Reaction(153)
Reaction.N_2N_T = Reaction(154)
Reaction.N_T_ALPHA = Reaction(155)
Reaction.N_4N_P = Reaction(156)
Reaction.N_3N_D = Reaction(157)
Reaction.N_N_D_ALPHA = Reaction(158)
Reaction.N_2N_P_ALPHA = Reaction(159)
Reaction.N_7N = Reaction(160)
Reaction.N_8N = Reaction(161)
Reaction.N_5N_P = Reaction(162)
Reaction.N_6N_P = Reaction(163)
Reaction.N_7N_P = Reaction(164)
Reaction.N_4N_ALPHA = Reaction(165)
Reaction.N_5N_ALPHA = Reaction(166)
Reaction.N_6N_ALPHA = Reaction(167)
Reaction.N_7N_ALPHA = Reaction(168)
Reaction.N_4N_D = Reaction(169)
Reaction.N_5N_D = Reaction(170)
Reaction.N_6N_D = Reaction(171)
Reaction.N_3N_T = Reaction(172)
Reaction.N_4N_T = Reaction(173)
Reaction.N_5N_T = Reaction(174)
Reaction.N_6N_T = Reaction(175)
Reaction.N_2N_HE3 = Reaction(176)
Reaction.N_3N_HE3 = Reaction(177)
Reaction.N_4N_HE3 = Reaction(178)
Reaction.N_3N_2P = Reaction(179)
Reaction.N_3N_2ALPHA = Reaction(180)
Reaction.N_3N_P_ALPHA = Reaction(181)
Reaction.N_D_T = Reaction(182)
Reaction.N_N_P_D = Reaction(183)
Reaction.N_N_P_T = Reaction(184)
Reaction.N_N_D_T = Reaction(185)
Reaction.N_N_P_HE3 = Reaction(186)
Reaction.N_N_D_HE3 = Reaction(187)
Reaction.N_N_T_HE3 = Reaction(188)
Reaction.N_N_T_ALPHA = Reaction(189)
Reaction.N_2N_2P = Reaction(190)
Reaction.N_P_HE3 = Reaction(191)
Reaction.N_D_HE3 = Reaction(192)
Reaction.N_HE3_ALPHA = Reaction(193)
Reaction.N_4N_2P = Reaction(194)
Reaction.N_4N_2ALPHA = Reaction(195)
Reaction.N_4N_P_ALPHA = Reaction(196)
Reaction.N_3P = Reaction(197)
Reaction.N_N_3P = Reaction(198)
Reaction.N_3N_2P_ALPHA = Reaction(199)
Reaction.N_5N_2P = Reaction(200)

# Redundant total-particle-production cross sections (derived files).
Reaction.TOTAL_NEUTRON_PRODUCTION = Reaction(201)
Reaction.TOTAL_GAMMA_PRODUCTION = Reaction(202)
Reaction.TOTAL_PROTON_PRODUCTION = Reaction(203)
Reaction.TOTAL_DEUTERON_PRODUCTION = Reaction(204)
Reaction.TOTAL_TRITON_PRODUCTION = Reaction(205)
Reaction.TOTAL_HE3_PRODUCTION = Reaction(206)
Reaction.TOTAL_ALPHA_PRODUCTION = Reaction(207)
Reaction.TOTAL_PI_PLUS_PRODUCTION = Reaction(208)
Reaction.TOTAL_PI_ZERO_PRODUCTION = Reaction(209)
Reaction.TOTAL_PI_MINUS_PRODUCTION = Reaction(210)
Reaction.TOTAL_MU_PLUS_PRODUCTION = Reaction(211)
Reaction.TOTAL_MU_MINUS_PRODUCTION = Reaction(212)
Reaction.TOTAL_KAON_PLUS_PRODUCTION = Reaction(213)
Reaction.TOTAL_KAON_ZERO_LONG_PRODUCTION = Reaction(214)
Reaction.TOTAL_KAON_ZERO_SHORT_PRODUCTION = Reaction(215)
Reaction.TOTAL_KAON_MINUS_PRODUCTION = Reaction(216)
Reaction.TOTAL_ANTIPROTON_PRODUCTION = Reaction(217)
Reaction.TOTAL_ANTINEUTRON_PRODUCTION = Reaction(218)

# Elastic-scattering slowing-down moments (derived files only).
Reaction.AVERAGE_COSINE_ELASTIC = Reaction(251)
Reaction.AVERAGE_LOG_ENERGY_DECREMENT_ELASTIC = Reaction(252)
Reaction.AVERAGE_ENERGY_DECREMENT_RATIO_ELASTIC = Reaction(253)

# Fission nu-bar, yield, and decay data.
Reaction.NU_TOTAL = Reaction(452)
Reaction.FISSION_YIELD_INDEPENDENT = Reaction(454)
Reaction.NU_DELAYED = Reaction(455)
Reaction.NU_PROMPT = Reaction(456)
Reaction.RADIOACTIVE_DECAY_DATA = Reaction(457)
Reaction.FISSION_ENERGY_RELEASE = Reaction(458)
Reaction.FISSION_YIELD_CUMULATIVE = Reaction(459)
Reaction.DELAYED_FISSION_PHOTONS = Reaction(460)

# Photo-/electro-atomic interaction data (incident photons/electrons
# only, never incident neutrons; kept plainly-named for that reason).
Reaction.TOTAL_CHARGED_PARTICLE_STOPPING_POWER = Reaction(500)
Reaction.TOTAL_ATOMIC_INTERACTION = Reaction(501)
Reaction.PHOTON_COHERENT_SCATTERING = Reaction(502)
Reaction.PHOTON_INCOHERENT_SCATTERING = Reaction(504)
Reaction.IMAGINARY_SCATTERING_FACTOR = Reaction(505)
Reaction.REAL_SCATTERING_FACTOR = Reaction(506)
Reaction.PAIR_PRODUCTION_ELECTRON_FIELD = Reaction(515)
Reaction.PAIR_PRODUCTION_TOTAL = Reaction(516)
Reaction.PAIR_PRODUCTION_NUCLEAR_FIELD = Reaction(517)
Reaction.IONIZATION_TOTAL = Reaction(522)
Reaction.PHOTOEXCITATION = Reaction(523)
Reaction.LARGE_ANGLE_SCATTERING = Reaction(525)
Reaction.TOTAL_ELECTRO_ATOMIC_SCATTERING = Reaction(526)
Reaction.ELECTRO_ATOMIC_BREMSSTRAHLUNG = Reaction(527)
Reaction.ELECTRO_ATOMIC_EXCITATION = Reaction(528)
Reaction.ATOMIC_RELAXATION_DATA = Reaction(533)

# Atomic-subshell photoelectric/electro-atomic cross sections.
Reaction.SUBSHELL_K = Reaction(534)
Reaction.SUBSHELL_L1 = Reaction(535)
Reaction.SUBSHELL_L2 = Reaction(536)
Reaction.SUBSHELL_L3 = Reaction(537)
Reaction.SUBSHELL_M1 = Reaction(538)
Reaction.SUBSHELL_M2 = Reaction(539)
Reaction.SUBSHELL_M3 = Reaction(540)
Reaction.SUBSHELL_M4 = Reaction(541)
Reaction.SUBSHELL_M5 = Reaction(542)
Reaction.SUBSHELL_N1 = Reaction(543)
Reaction.SUBSHELL_N2 = Reaction(544)
Reaction.SUBSHELL_N3 = Reaction(545)
Reaction.SUBSHELL_N4 = Reaction(546)
Reaction.SUBSHELL_N5 = Reaction(547)
Reaction.SUBSHELL_N6 = Reaction(548)
Reaction.SUBSHELL_N7 = Reaction(549)
Reaction.SUBSHELL_O1 = Reaction(550)
Reaction.SUBSHELL_O2 = Reaction(551)
Reaction.SUBSHELL_O3 = Reaction(552)
Reaction.SUBSHELL_O4 = Reaction(553)
Reaction.SUBSHELL_O5 = Reaction(554)
Reaction.SUBSHELL_O6 = Reaction(555)
Reaction.SUBSHELL_O7 = Reaction(556)
Reaction.SUBSHELL_O8 = Reaction(557)
Reaction.SUBSHELL_O9 = Reaction(558)
Reaction.SUBSHELL_P1 = Reaction(559)
Reaction.SUBSHELL_P2 = Reaction(560)
Reaction.SUBSHELL_P3 = Reaction(561)
Reaction.SUBSHELL_P4 = Reaction(562)
Reaction.SUBSHELL_P5 = Reaction(563)
Reaction.SUBSHELL_P6 = Reaction(564)
Reaction.SUBSHELL_P7 = Reaction(565)
Reaction.SUBSHELL_P8 = Reaction(566)
Reaction.SUBSHELL_P9 = Reaction(567)
Reaction.SUBSHELL_P10 = Reaction(568)
Reaction.SUBSHELL_P11 = Reaction(569)
Reaction.SUBSHELL_Q1 = Reaction(570)
Reaction.SUBSHELL_Q2 = Reaction(571)
Reaction.SUBSHELL_Q3 = Reaction(572)

# (n,n') to individual discrete excited levels of the residual nucleus,
# and the continuum remainder; sum to Reaction.INELASTIC_SCATTER (MT 4).
# No L00/MT 50 (ground state) for incident neutrons -- that's elastic
# scattering, Reaction.ELASTIC.
Reaction.INELASTIC_SCATTER_L01 = Reaction(51)
Reaction.INELASTIC_SCATTER_L02 = Reaction(52)
Reaction.INELASTIC_SCATTER_L03 = Reaction(53)
Reaction.INELASTIC_SCATTER_L04 = Reaction(54)
Reaction.INELASTIC_SCATTER_L05 = Reaction(55)
Reaction.INELASTIC_SCATTER_L06 = Reaction(56)
Reaction.INELASTIC_SCATTER_L07 = Reaction(57)
Reaction.INELASTIC_SCATTER_L08 = Reaction(58)
Reaction.INELASTIC_SCATTER_L09 = Reaction(59)
Reaction.INELASTIC_SCATTER_L10 = Reaction(60)
Reaction.INELASTIC_SCATTER_L11 = Reaction(61)
Reaction.INELASTIC_SCATTER_L12 = Reaction(62)
Reaction.INELASTIC_SCATTER_L13 = Reaction(63)
Reaction.INELASTIC_SCATTER_L14 = Reaction(64)
Reaction.INELASTIC_SCATTER_L15 = Reaction(65)
Reaction.INELASTIC_SCATTER_L16 = Reaction(66)
Reaction.INELASTIC_SCATTER_L17 = Reaction(67)
Reaction.INELASTIC_SCATTER_L18 = Reaction(68)
Reaction.INELASTIC_SCATTER_L19 = Reaction(69)
Reaction.INELASTIC_SCATTER_L20 = Reaction(70)
Reaction.INELASTIC_SCATTER_L21 = Reaction(71)
Reaction.INELASTIC_SCATTER_L22 = Reaction(72)
Reaction.INELASTIC_SCATTER_L23 = Reaction(73)
Reaction.INELASTIC_SCATTER_L24 = Reaction(74)
Reaction.INELASTIC_SCATTER_L25 = Reaction(75)
Reaction.INELASTIC_SCATTER_L26 = Reaction(76)
Reaction.INELASTIC_SCATTER_L27 = Reaction(77)
Reaction.INELASTIC_SCATTER_L28 = Reaction(78)
Reaction.INELASTIC_SCATTER_L29 = Reaction(79)
Reaction.INELASTIC_SCATTER_L30 = Reaction(80)
Reaction.INELASTIC_SCATTER_L31 = Reaction(81)
Reaction.INELASTIC_SCATTER_L32 = Reaction(82)
Reaction.INELASTIC_SCATTER_L33 = Reaction(83)
Reaction.INELASTIC_SCATTER_L34 = Reaction(84)
Reaction.INELASTIC_SCATTER_L35 = Reaction(85)
Reaction.INELASTIC_SCATTER_L36 = Reaction(86)
Reaction.INELASTIC_SCATTER_L37 = Reaction(87)
Reaction.INELASTIC_SCATTER_L38 = Reaction(88)
Reaction.INELASTIC_SCATTER_L39 = Reaction(89)
Reaction.INELASTIC_SCATTER_L40 = Reaction(90)
Reaction.INELASTIC_SCATTER_CONTINUUM = Reaction(91)

# (n,p) to individual discrete levels (L00 = ground state) and the
# continuum remainder; sum to Reaction.N_P (MT 103).
Reaction.N_P_L00 = Reaction(600)
Reaction.N_P_L01 = Reaction(601)
Reaction.N_P_L02 = Reaction(602)
Reaction.N_P_L03 = Reaction(603)
Reaction.N_P_L04 = Reaction(604)
Reaction.N_P_L05 = Reaction(605)
Reaction.N_P_L06 = Reaction(606)
Reaction.N_P_L07 = Reaction(607)
Reaction.N_P_L08 = Reaction(608)
Reaction.N_P_L09 = Reaction(609)
Reaction.N_P_L10 = Reaction(610)
Reaction.N_P_L11 = Reaction(611)
Reaction.N_P_L12 = Reaction(612)
Reaction.N_P_L13 = Reaction(613)
Reaction.N_P_L14 = Reaction(614)
Reaction.N_P_L15 = Reaction(615)
Reaction.N_P_L16 = Reaction(616)
Reaction.N_P_L17 = Reaction(617)
Reaction.N_P_L18 = Reaction(618)
Reaction.N_P_L19 = Reaction(619)
Reaction.N_P_L20 = Reaction(620)
Reaction.N_P_L21 = Reaction(621)
Reaction.N_P_L22 = Reaction(622)
Reaction.N_P_L23 = Reaction(623)
Reaction.N_P_L24 = Reaction(624)
Reaction.N_P_L25 = Reaction(625)
Reaction.N_P_L26 = Reaction(626)
Reaction.N_P_L27 = Reaction(627)
Reaction.N_P_L28 = Reaction(628)
Reaction.N_P_L29 = Reaction(629)
Reaction.N_P_L30 = Reaction(630)
Reaction.N_P_L31 = Reaction(631)
Reaction.N_P_L32 = Reaction(632)
Reaction.N_P_L33 = Reaction(633)
Reaction.N_P_L34 = Reaction(634)
Reaction.N_P_L35 = Reaction(635)
Reaction.N_P_L36 = Reaction(636)
Reaction.N_P_L37 = Reaction(637)
Reaction.N_P_L38 = Reaction(638)
Reaction.N_P_L39 = Reaction(639)
Reaction.N_P_L40 = Reaction(640)
Reaction.N_P_L41 = Reaction(641)
Reaction.N_P_L42 = Reaction(642)
Reaction.N_P_L43 = Reaction(643)
Reaction.N_P_L44 = Reaction(644)
Reaction.N_P_L45 = Reaction(645)
Reaction.N_P_L46 = Reaction(646)
Reaction.N_P_L47 = Reaction(647)
Reaction.N_P_L48 = Reaction(648)
Reaction.N_P_CONTINUUM = Reaction(649)

# (n,d) to individual discrete levels (L00 = ground state) and the
# continuum remainder; sum to Reaction.N_D (MT 104).
Reaction.N_D_L00 = Reaction(650)
Reaction.N_D_L01 = Reaction(651)
Reaction.N_D_L02 = Reaction(652)
Reaction.N_D_L03 = Reaction(653)
Reaction.N_D_L04 = Reaction(654)
Reaction.N_D_L05 = Reaction(655)
Reaction.N_D_L06 = Reaction(656)
Reaction.N_D_L07 = Reaction(657)
Reaction.N_D_L08 = Reaction(658)
Reaction.N_D_L09 = Reaction(659)
Reaction.N_D_L10 = Reaction(660)
Reaction.N_D_L11 = Reaction(661)
Reaction.N_D_L12 = Reaction(662)
Reaction.N_D_L13 = Reaction(663)
Reaction.N_D_L14 = Reaction(664)
Reaction.N_D_L15 = Reaction(665)
Reaction.N_D_L16 = Reaction(666)
Reaction.N_D_L17 = Reaction(667)
Reaction.N_D_L18 = Reaction(668)
Reaction.N_D_L19 = Reaction(669)
Reaction.N_D_L20 = Reaction(670)
Reaction.N_D_L21 = Reaction(671)
Reaction.N_D_L22 = Reaction(672)
Reaction.N_D_L23 = Reaction(673)
Reaction.N_D_L24 = Reaction(674)
Reaction.N_D_L25 = Reaction(675)
Reaction.N_D_L26 = Reaction(676)
Reaction.N_D_L27 = Reaction(677)
Reaction.N_D_L28 = Reaction(678)
Reaction.N_D_L29 = Reaction(679)
Reaction.N_D_L30 = Reaction(680)
Reaction.N_D_L31 = Reaction(681)
Reaction.N_D_L32 = Reaction(682)
Reaction.N_D_L33 = Reaction(683)
Reaction.N_D_L34 = Reaction(684)
Reaction.N_D_L35 = Reaction(685)
Reaction.N_D_L36 = Reaction(686)
Reaction.N_D_L37 = Reaction(687)
Reaction.N_D_L38 = Reaction(688)
Reaction.N_D_L39 = Reaction(689)
Reaction.N_D_L40 = Reaction(690)
Reaction.N_D_L41 = Reaction(691)
Reaction.N_D_L42 = Reaction(692)
Reaction.N_D_L43 = Reaction(693)
Reaction.N_D_L44 = Reaction(694)
Reaction.N_D_L45 = Reaction(695)
Reaction.N_D_L46 = Reaction(696)
Reaction.N_D_L47 = Reaction(697)
Reaction.N_D_L48 = Reaction(698)
Reaction.N_D_CONTINUUM = Reaction(699)

# (n,t) to individual discrete levels (L00 = ground state) and the
# continuum remainder; sum to Reaction.N_T (MT 105).
Reaction.N_T_L00 = Reaction(700)
Reaction.N_T_L01 = Reaction(701)
Reaction.N_T_L02 = Reaction(702)
Reaction.N_T_L03 = Reaction(703)
Reaction.N_T_L04 = Reaction(704)
Reaction.N_T_L05 = Reaction(705)
Reaction.N_T_L06 = Reaction(706)
Reaction.N_T_L07 = Reaction(707)
Reaction.N_T_L08 = Reaction(708)
Reaction.N_T_L09 = Reaction(709)
Reaction.N_T_L10 = Reaction(710)
Reaction.N_T_L11 = Reaction(711)
Reaction.N_T_L12 = Reaction(712)
Reaction.N_T_L13 = Reaction(713)
Reaction.N_T_L14 = Reaction(714)
Reaction.N_T_L15 = Reaction(715)
Reaction.N_T_L16 = Reaction(716)
Reaction.N_T_L17 = Reaction(717)
Reaction.N_T_L18 = Reaction(718)
Reaction.N_T_L19 = Reaction(719)
Reaction.N_T_L20 = Reaction(720)
Reaction.N_T_L21 = Reaction(721)
Reaction.N_T_L22 = Reaction(722)
Reaction.N_T_L23 = Reaction(723)
Reaction.N_T_L24 = Reaction(724)
Reaction.N_T_L25 = Reaction(725)
Reaction.N_T_L26 = Reaction(726)
Reaction.N_T_L27 = Reaction(727)
Reaction.N_T_L28 = Reaction(728)
Reaction.N_T_L29 = Reaction(729)
Reaction.N_T_L30 = Reaction(730)
Reaction.N_T_L31 = Reaction(731)
Reaction.N_T_L32 = Reaction(732)
Reaction.N_T_L33 = Reaction(733)
Reaction.N_T_L34 = Reaction(734)
Reaction.N_T_L35 = Reaction(735)
Reaction.N_T_L36 = Reaction(736)
Reaction.N_T_L37 = Reaction(737)
Reaction.N_T_L38 = Reaction(738)
Reaction.N_T_L39 = Reaction(739)
Reaction.N_T_L40 = Reaction(740)
Reaction.N_T_L41 = Reaction(741)
Reaction.N_T_L42 = Reaction(742)
Reaction.N_T_L43 = Reaction(743)
Reaction.N_T_L44 = Reaction(744)
Reaction.N_T_L45 = Reaction(745)
Reaction.N_T_L46 = Reaction(746)
Reaction.N_T_L47 = Reaction(747)
Reaction.N_T_L48 = Reaction(748)
Reaction.N_T_CONTINUUM = Reaction(749)

# (n,He3) to individual discrete levels (L00 = ground state) and the
# continuum remainder; sum to Reaction.N_HE3 (MT 106).
Reaction.N_HE3_L00 = Reaction(750)
Reaction.N_HE3_L01 = Reaction(751)
Reaction.N_HE3_L02 = Reaction(752)
Reaction.N_HE3_L03 = Reaction(753)
Reaction.N_HE3_L04 = Reaction(754)
Reaction.N_HE3_L05 = Reaction(755)
Reaction.N_HE3_L06 = Reaction(756)
Reaction.N_HE3_L07 = Reaction(757)
Reaction.N_HE3_L08 = Reaction(758)
Reaction.N_HE3_L09 = Reaction(759)
Reaction.N_HE3_L10 = Reaction(760)
Reaction.N_HE3_L11 = Reaction(761)
Reaction.N_HE3_L12 = Reaction(762)
Reaction.N_HE3_L13 = Reaction(763)
Reaction.N_HE3_L14 = Reaction(764)
Reaction.N_HE3_L15 = Reaction(765)
Reaction.N_HE3_L16 = Reaction(766)
Reaction.N_HE3_L17 = Reaction(767)
Reaction.N_HE3_L18 = Reaction(768)
Reaction.N_HE3_L19 = Reaction(769)
Reaction.N_HE3_L20 = Reaction(770)
Reaction.N_HE3_L21 = Reaction(771)
Reaction.N_HE3_L22 = Reaction(772)
Reaction.N_HE3_L23 = Reaction(773)
Reaction.N_HE3_L24 = Reaction(774)
Reaction.N_HE3_L25 = Reaction(775)
Reaction.N_HE3_L26 = Reaction(776)
Reaction.N_HE3_L27 = Reaction(777)
Reaction.N_HE3_L28 = Reaction(778)
Reaction.N_HE3_L29 = Reaction(779)
Reaction.N_HE3_L30 = Reaction(780)
Reaction.N_HE3_L31 = Reaction(781)
Reaction.N_HE3_L32 = Reaction(782)
Reaction.N_HE3_L33 = Reaction(783)
Reaction.N_HE3_L34 = Reaction(784)
Reaction.N_HE3_L35 = Reaction(785)
Reaction.N_HE3_L36 = Reaction(786)
Reaction.N_HE3_L37 = Reaction(787)
Reaction.N_HE3_L38 = Reaction(788)
Reaction.N_HE3_L39 = Reaction(789)
Reaction.N_HE3_L40 = Reaction(790)
Reaction.N_HE3_L41 = Reaction(791)
Reaction.N_HE3_L42 = Reaction(792)
Reaction.N_HE3_L43 = Reaction(793)
Reaction.N_HE3_L44 = Reaction(794)
Reaction.N_HE3_L45 = Reaction(795)
Reaction.N_HE3_L46 = Reaction(796)
Reaction.N_HE3_L47 = Reaction(797)
Reaction.N_HE3_L48 = Reaction(798)
Reaction.N_HE3_CONTINUUM = Reaction(799)

# (n,alpha) to individual discrete levels (L00 = ground state) and the
# continuum remainder; sum to Reaction.N_ALPHA (MT 107).
Reaction.N_ALPHA_L00 = Reaction(800)
Reaction.N_ALPHA_L01 = Reaction(801)
Reaction.N_ALPHA_L02 = Reaction(802)
Reaction.N_ALPHA_L03 = Reaction(803)
Reaction.N_ALPHA_L04 = Reaction(804)
Reaction.N_ALPHA_L05 = Reaction(805)
Reaction.N_ALPHA_L06 = Reaction(806)
Reaction.N_ALPHA_L07 = Reaction(807)
Reaction.N_ALPHA_L08 = Reaction(808)
Reaction.N_ALPHA_L09 = Reaction(809)
Reaction.N_ALPHA_L10 = Reaction(810)
Reaction.N_ALPHA_L11 = Reaction(811)
Reaction.N_ALPHA_L12 = Reaction(812)
Reaction.N_ALPHA_L13 = Reaction(813)
Reaction.N_ALPHA_L14 = Reaction(814)
Reaction.N_ALPHA_L15 = Reaction(815)
Reaction.N_ALPHA_L16 = Reaction(816)
Reaction.N_ALPHA_L17 = Reaction(817)
Reaction.N_ALPHA_L18 = Reaction(818)
Reaction.N_ALPHA_L19 = Reaction(819)
Reaction.N_ALPHA_L20 = Reaction(820)
Reaction.N_ALPHA_L21 = Reaction(821)
Reaction.N_ALPHA_L22 = Reaction(822)
Reaction.N_ALPHA_L23 = Reaction(823)
Reaction.N_ALPHA_L24 = Reaction(824)
Reaction.N_ALPHA_L25 = Reaction(825)
Reaction.N_ALPHA_L26 = Reaction(826)
Reaction.N_ALPHA_L27 = Reaction(827)
Reaction.N_ALPHA_L28 = Reaction(828)
Reaction.N_ALPHA_L29 = Reaction(829)
Reaction.N_ALPHA_L30 = Reaction(830)
Reaction.N_ALPHA_L31 = Reaction(831)
Reaction.N_ALPHA_L32 = Reaction(832)
Reaction.N_ALPHA_L33 = Reaction(833)
Reaction.N_ALPHA_L34 = Reaction(834)
Reaction.N_ALPHA_L35 = Reaction(835)
Reaction.N_ALPHA_L36 = Reaction(836)
Reaction.N_ALPHA_L37 = Reaction(837)
Reaction.N_ALPHA_L38 = Reaction(838)
Reaction.N_ALPHA_L39 = Reaction(839)
Reaction.N_ALPHA_L40 = Reaction(840)
Reaction.N_ALPHA_L41 = Reaction(841)
Reaction.N_ALPHA_L42 = Reaction(842)
Reaction.N_ALPHA_L43 = Reaction(843)
Reaction.N_ALPHA_L44 = Reaction(844)
Reaction.N_ALPHA_L45 = Reaction(845)
Reaction.N_ALPHA_L46 = Reaction(846)
Reaction.N_ALPHA_L47 = Reaction(847)
Reaction.N_ALPHA_L48 = Reaction(848)
Reaction.N_ALPHA_CONTINUUM = Reaction(849)

# (n,2n) to individual discrete levels (L00 = ground state) and the
# continuum remainder; sum to Reaction.N_2N (MT 16).
Reaction.N_2N_L00 = Reaction(875)
Reaction.N_2N_L01 = Reaction(876)
Reaction.N_2N_L02 = Reaction(877)
Reaction.N_2N_L03 = Reaction(878)
Reaction.N_2N_L04 = Reaction(879)
Reaction.N_2N_L05 = Reaction(880)
Reaction.N_2N_L06 = Reaction(881)
Reaction.N_2N_L07 = Reaction(882)
Reaction.N_2N_L08 = Reaction(883)
Reaction.N_2N_L09 = Reaction(884)
Reaction.N_2N_L10 = Reaction(885)
Reaction.N_2N_L11 = Reaction(886)
Reaction.N_2N_L12 = Reaction(887)
Reaction.N_2N_L13 = Reaction(888)
Reaction.N_2N_L14 = Reaction(889)
Reaction.N_2N_L15 = Reaction(890)
Reaction.N_2N_CONTINUUM = Reaction(891)


class AttenuatorLayer:
    """One layer of an FM attenuator set: ``m px``.

    .. versionadded:: 1.6.0b2

    Parameters
    ----------
    material : int
        Material number identified on an ``Mm`` card.
    areal_density : float
        Density times thickness of the attenuating layer. Always stored
        positive (like :attr:`montepy.Material.is_atom_fraction`'s
        convention) — the atom-vs-mass distinction is carried separately in
        ``is_atom_density``, not via sign.
    is_atom_density : bool
        ``True`` if ``areal_density`` is an atom density (atoms/barn-cm),
        ``False`` if it's a mass density (g/cm3). Corresponds to the sign
        of the raw MCNP ``px`` value (positive = atom, negative = mass).
    """

    __slots__ = ("_material", "_areal_density", "_is_atom_density")

    @args_checked
    def __init__(
        self,
        material: ty.Integral,
        areal_density: ty.Real,
        is_atom_density: bool = True,
    ):
        self._material = material
        self._areal_density = abs(areal_density)
        self._is_atom_density = is_atom_density

    @property
    def material(self) -> int:
        """The material number for this layer, from an ``Mm`` card."""
        return self._material

    @property
    def areal_density(self) -> float:
        """Density times thickness of this layer (always positive)."""
        return self._areal_density

    @property
    def is_atom_density(self) -> bool:
        """``True`` if :attr:`areal_density` is an atom density, ``False`` if mass density."""
        return self._is_atom_density

    def __eq__(self, other):
        if not isinstance(other, AttenuatorLayer):
            return NotImplemented
        return (
            self._material == other._material
            and self._areal_density == other._areal_density
            and self._is_atom_density == other._is_atom_density
        )

    def __repr__(self):
        return f"AttenuatorLayer({self._material}, {self._areal_density}, is_atom_density={self._is_atom_density})"


class AttenuatorSet:
    """An FM attenuator set: ``c -1 m1 px1 m2 px2 ...``.

    Models the thin-shield line-of-sight attenuation factor
    ``exp(-sum(sigma_i * px_i))``. Layers chain via ``&`` (mirrors
    :class:`~montepy.HalfSpace`'s own ``&``; layers stack multiplicatively
    in the exponent, like an intersection of independent attenuating
    conditions):

    .. code-block:: python

        attenuator = AttenuatorSet(1.0, [AttenuatorLayer(3, 0.05)])
        attenuator = attenuator & AttenuatorLayer(4, 0.1, is_atom_density=False)

    .. versionadded:: 1.6.0b2
    """

    __slots__ = ("_constant", "_layers", "_node")

    @args_checked
    def __init__(self, constant: ty.Real, layers: list[AttenuatorLayer]):
        self._constant = constant
        self._layers = list(layers)
        self._node = None

    @property
    def constant(self) -> float:
        """The scalar constant ``c`` for this attenuator set."""
        return self._constant

    @property
    def layers(self) -> list[AttenuatorLayer]:
        """The attenuating layers, in order."""
        return list(self._layers)

    @property
    def node(self) -> syntax_node.ListNode:
        """The syntax node for this attenuator set.

        .. versionadded:: 1.6.0b3
        """
        self._ensure_has_node()
        return self._node

    def _ensure_has_node(self):
        if self._node is not None:
            return
        node = syntax_node.ListNode("attenuator set")
        node.append(_make_value_node(float, self._constant))
        node.append(_make_value_node(int, -1))
        for layer in self._layers:
            node.append(_make_value_node(int, layer.material))
            density = (
                layer.areal_density if layer.is_atom_density else -layer.areal_density
            )
            node.append(_make_value_node(float, density))
        self._node = node

    @args_checked
    def __and__(self, other: Union[AttenuatorLayer, "AttenuatorSet"]) -> AttenuatorSet:
        """Return a new :class:`AttenuatorSet` with ``other``'s layer(s) appended."""
        if isinstance(other, AttenuatorLayer):
            new_layers = [other]
        else:
            new_layers = other.layers
        return AttenuatorSet(self._constant, self._layers + new_layers)

    def __eq__(self, other):
        if not isinstance(other, AttenuatorSet):
            return NotImplemented
        return self._constant == other._constant and self._layers == other._layers

    def __repr__(self):
        return f"AttenuatorSet({self._constant}, {self._layers!r})"


class MultiplierSet:
    """An FM multiplier set: ``c m (reaction list 1) (reaction list 2) ...``.

    .. versionadded:: 1.6.0b2

    Parameters
    ----------
    constant : float
        The scalar constant ``c``. If negative (type-4 tallies only), MCNP
        replaces ``|c|`` with ``|c|`` times the tallying cell's atom density.
    material : int, optional
        Material number from an ``Mm`` card. ``None``/``0`` means "the
        material of the current cell."
    reactions : list[montepy.data_inputs.tally_multiplier.ReactionExpression]
        One entry per output bin this set creates (MCNP creates one bin per
        reaction list, per FM spec footnote 4).
    """

    __slots__ = ("_constant", "_material", "_reactions", "_node", "_material_node")

    @args_checked
    def __init__(
        self,
        constant: ty.Real,
        material: Union[ty.Integral, "montepy.Material", None],
        reactions: list[ReactionExpression],
    ):
        self._constant = constant
        self._material = material
        self._reactions = list(reactions)
        self._node = None
        self._material_node = None

    @property
    def constant(self) -> float:
        """The scalar constant ``c`` for this multiplier set."""
        return self._constant

    @property
    def material(self) -> int | None:
        """The material number, or ``None`` for "current cell's material".

        Resolved live from the linked :class:`~montepy.Material` if this set
        was built from one (e.g. ``mat & Reaction.CAPTURE``), so a later
        renumber of that material is reflected here too.
        """
        if isinstance(self._material, montepy.Material):
            return self._material.number
        return self._material

    @property
    def reactions(self) -> list[ReactionExpression]:
        """One :class:`~montepy.data_inputs.tally_multiplier.ReactionExpression` per output bin this set creates."""
        return list(self._reactions)

    @property
    def node(self) -> syntax_node.ListNode:
        """The syntax node for this multiplier set.

        .. versionadded:: 1.6.0b3
        """
        self._ensure_has_node()
        if (
            self._material_node is not None
            and self._material_node.value != self.material
        ):
            self._material_node.value = self.material
        return self._node

    def _ensure_has_node(self):
        if self._node is not None:
            return
        node = syntax_node.ListNode("multiplier set")
        node.append(_make_value_node(float, self._constant))
        if self.material is not None:
            self._material_node = _make_value_node(int, self.material)
            node.append(self._material_node)
        if len(self._reactions) == 1:
            node.append(self._reactions[0].node)
        else:
            for reaction in self._reactions:
                group = syntax_node.ListNode("tally group")
                group.append(syntax_node.PaddingNode("("))
                for n in reaction.node.nodes:
                    group.append(n)
                group.append(syntax_node.PaddingNode(")"))
                node.append(group)
        self._node = node

    def __rmul__(self, constant: ty.Real) -> MultiplierSet:
        """``1.5 * (mat1 & Reaction.CAPTURE)`` sets the constant.

        Completes the DSL alongside ``ReactionExpression.__rand__``:
        ``material & reaction`` builds a :class:`MultiplierSet` with
        ``constant=1.0``, and this lets you scale it afterwards, mirroring
        ``ReactionExpression.__rmul__``'s int-first convenience
        (``16 * Reaction(103)``).
        """
        return MultiplierSet(constant, self._material, self._reactions)

    def __eq__(self, other):
        if not isinstance(other, MultiplierSet):
            return NotImplemented
        return (
            self._constant == other._constant
            and self.material == other.material
            and self._reactions == other._reactions
        )

    def __repr__(self):
        return f"MultiplierSet({self._constant}, {self.material}, {self._reactions!r})"


class SpecialMultiplierSet:
    """An FM special multiplier set: ``c k``.

    .. versionadded:: 1.6.0b2

    Parameters
    ----------
    constant : float
        The scalar constant ``c``.
    kind : SpecialMultiplier
        Which special multiplier option (``k``) this is.
    """

    __slots__ = ("_constant", "_kind", "_node")

    @args_checked
    def __init__(self, constant: ty.Real, kind: SpecialMultiplier):
        self._constant = constant
        self._kind = kind
        self._node = None

    @property
    def constant(self) -> float:
        """The scalar constant ``c`` for this special multiplier set."""
        return self._constant

    @property
    def kind(self) -> SpecialMultiplier:
        """Which special multiplier option this is."""
        return self._kind

    @property
    def node(self) -> syntax_node.ListNode:
        """The syntax node for this special multiplier set.

        .. versionadded:: 1.6.0b3
        """
        self._ensure_has_node()
        return self._node

    def _ensure_has_node(self):
        if self._node is not None:
            return
        node = syntax_node.ListNode("special multiplier set")
        node.append(_make_value_node(float, self._constant))
        node.append(_make_value_node(int, _SPECIAL_KIND_MAP_INVERSE[self._kind]))
        self._node = node

    def __eq__(self, other):
        if not isinstance(other, SpecialMultiplierSet):
            return NotImplemented
        return self._constant == other._constant and self._kind == other._kind

    def __repr__(self):
        return f"SpecialMultiplierSet({self._constant}, {self._kind})"


class MultiplierScore:
    """One physical output bin's full recipe: exactly one FM-derived tally score.

    Exactly one of ``reaction``/``kind`` is non-``None``: ``reaction`` for a
    bin coming from a :class:`MultiplierSet`, ``kind`` for one coming from a
    :class:`SpecialMultiplierSet`.

    .. versionadded:: 1.6.0b2
    """

    __slots__ = ("_constant", "_material", "_reaction", "_kind", "_attenuator")

    def __init__(
        self,
        constant: ty.Real,
        material: ty.Integral | None,
        reaction: ReactionExpression | None,
        kind: SpecialMultiplier | None,
        attenuator: AttenuatorSet | None,
    ):
        self._constant = constant
        self._material = material
        self._reaction = reaction
        self._kind = kind
        self._attenuator = attenuator

    @property
    def constant(self) -> float:
        """The scalar constant ``c`` for this score."""
        return self._constant

    @property
    def material(self) -> int | None:
        """The material number, or ``None``."""
        return self._material

    @property
    def reaction(self) -> ReactionExpression | None:
        """The reaction expression for this score, if from a :class:`MultiplierSet`."""
        return self._reaction

    @property
    def kind(self) -> SpecialMultiplier | None:
        """The special multiplier kind for this score, if from a :class:`SpecialMultiplierSet`."""
        return self._kind

    @property
    def attenuator(self) -> AttenuatorSet | None:
        """The attenuator applied to this score, if any, inherited from the parent :class:`MultiplierBin`."""
        return self._attenuator

    def __eq__(self, other):
        if not isinstance(other, MultiplierScore):
            return NotImplemented
        return (
            self._constant == other._constant
            and self._material == other._material
            and self._reaction == other._reaction
            and self._kind == other._kind
            and self._attenuator == other._attenuator
        )

    def __repr__(self):
        return (
            f"MultiplierScore(constant={self._constant}, material={self._material}, "
            f"reaction={self._reaction!r}, kind={self._kind}, attenuator={self._attenuator!r})"
        )


class MultiplierBin:
    """One top-level ``(bin set k)`` group of an FM card.

    .. versionadded:: 1.6.0b2

    Parameters
    ----------
    terms : list[MultiplierSet | SpecialMultiplierSet]
        The multiplier/special-multiplier sets in this bin set.
    attenuator : AttenuatorSet, optional
        The attenuator set for this bin set, if any -- applies to every bin
        the ``terms`` produce.
    """

    __slots__ = ("_terms", "_attenuator", "_node")

    def __init__(
        self,
        terms: list[MultiplierSet | SpecialMultiplierSet],
        attenuator: AttenuatorSet | None = None,
    ):
        self._terms = list(terms)
        self._attenuator = attenuator
        self._node = None

    @property
    def terms(self) -> list[MultiplierSet | SpecialMultiplierSet]:
        """The multiplier/special-multiplier sets in this bin set."""
        return list(self._terms)

    @property
    def attenuator(self) -> AttenuatorSet | None:
        """The attenuator set for this bin set, if any."""
        return self._attenuator

    @property
    def node(self) -> syntax_node.ListNode:
        """The syntax node for this bin's own content (not including the
        outer parens a sibling bin or multi-term structure may require --
        that's decided by :class:`TallyMultiplier`, which knows about
        sibling bins).

        .. versionadded:: 1.6.0b3
        """
        self._ensure_has_node()
        items = list(self._terms)
        if self._attenuator is not None:
            items.append(self._attenuator)
        for item in items:
            if item._node is not None:
                item.node
        return self._node

    def _own_item_count(self):
        return len(self._terms) + (1 if self._attenuator is not None else 0)

    def _ensure_has_node(self):
        if self._node is not None:
            return
        items = list(self._terms)
        if self._attenuator is not None:
            items.append(self._attenuator)
        node = syntax_node.ListNode("bin body")
        wrap_each = len(items) > 1
        for item in items:
            item_node = item.node
            if wrap_each:
                group = syntax_node.ListNode("tally group")
                group.append(syntax_node.PaddingNode("("))
                for n in item_node.nodes:
                    group.append(n)
                group.append(syntax_node.PaddingNode(")"))
                node.append(group)
            else:
                for n in item_node.nodes:
                    node.append(n)
        self._node = node

    @property
    def scores(self) -> list[MultiplierScore]:
        """Flatten this bin set's terms into one :class:`MultiplierScore` per actual output bin."""
        if not self._terms and self._attenuator is not None:
            return [
                MultiplierScore(
                    self._attenuator.constant, None, None, None, self._attenuator
                )
            ]
        result = []
        for term in self._terms:
            if isinstance(term, MultiplierSet):
                if not term.reactions:
                    result.append(
                        MultiplierScore(
                            term.constant, term.material, None, None, self._attenuator
                        )
                    )
                for reaction in term.reactions:
                    result.append(
                        MultiplierScore(
                            term.constant,
                            term.material,
                            reaction,
                            None,
                            self._attenuator,
                        )
                    )
            elif isinstance(term, SpecialMultiplierSet):
                result.append(
                    MultiplierScore(
                        term.constant, None, None, term.kind, self._attenuator
                    )
                )
        return result

    @classmethod
    def from_items(cls, items: list) -> MultiplierBin:
        """Parse a bin set's flat CST items into a :class:`MultiplierBin`."""
        original = list(items)
        items = _non_padding(items)
        nested_groups = [n for n in items if _is_group(n)]
        if nested_groups and len(nested_groups) == len(items):
            # Multiple sibling multiplier/attenuator sets, each individually
            # parenthesized (FM parenthesization rule 2).
            raw_terms = [_parse_term(_group_body(g)) for g in nested_groups]
        else:
            # A single term, inline (rule 1) -- items are that term's content.
            raw_terms = [_parse_term(items)]
        terms = []
        attenuator = None
        for term in raw_terms:
            if isinstance(term, AttenuatorSet):
                attenuator = term
            else:
                terms.append(term)
        result = cls(terms, attenuator)
        node = syntax_node.ListNode("bin body")
        for n in original:
            node.append(n)
        result._node = node
        return result

    def __eq__(self, other):
        if not isinstance(other, MultiplierBin):
            return NotImplemented
        return self._terms == other._terms and self._attenuator == other._attenuator

    def __repr__(self):
        return f"MultiplierBin(terms={self._terms!r}, attenuator={self._attenuator!r})"


def _is_group(node) -> bool:
    return isinstance(node, syntax_node.ListNode) and node.name == "tally group"


def _non_padding(nodes):
    return [n for n in nodes if not isinstance(n, syntax_node.PaddingNode)]


def _group_body(group_node):
    """Strip the leading/trailing paren ``ValueNode``s off a "tally group" ``ListNode``."""
    nodes = list(group_node.nodes)
    return _non_padding(nodes[1:-1]) if len(nodes) >= 2 else _non_padding(nodes)


def _numeric_value(node):
    return node.value


def _parse_term(items: list) -> MultiplierSet | SpecialMultiplierSet | AttenuatorSet:
    """Parse one multiplier/special-multiplier/attenuator set's flat content."""
    items = _non_padding(items)
    constant = _numeric_value(items[0])
    rest = items[1:]
    if not rest:
        return MultiplierSet(constant, None, [])

    first = rest[0]
    first_val = (
        _numeric_value(first) if isinstance(first, syntax_node.ValueNode) else None
    )

    if first_val in _SPECIAL_KIND_MAP and len(rest) == 1:
        return SpecialMultiplierSet(constant, _SPECIAL_KIND_MAP[first_val])

    if first_val == -1 and len(rest) > 1:
        layer_tokens = rest[1:]
        layers = []
        for i in range(0, len(layer_tokens), 2):
            mat = int(_numeric_value(layer_tokens[i]))
            px = _numeric_value(layer_tokens[i + 1])
            layers.append(AttenuatorLayer(mat, abs(px), px >= 0))
        return AttenuatorSet(constant, layers)

    # A multiplier set: material, then reaction list(s).
    material = int(first_val)
    reaction_items = rest[1:]
    nested = [n for n in reaction_items if _is_group(n)]
    if nested:
        reactions = [_parse_reaction_expr(_group_body(g)) for g in nested]
    elif reaction_items:
        reactions = [_parse_reaction_expr(reaction_items)]
    else:
        reactions = []
    return MultiplierSet(constant, material, reactions)


def _parse_reaction_expr(items: list) -> ReactionExpression:
    """Resolve a flat reaction-list token stream into a :class:`ReactionExpression`.

    Applies "multiply first" precedence in Python (fold space-separated
    numbers with ``*``, then fold ``:``/``#``-separated groups with
    ``+``/``-``) rather than encoding it in the grammar -- mirrors how
    ``tally.py``'s own ``_parse_tally_group_node`` does its real
    interpretation as a second pass over a loosely structured CST.
    """
    original = list(items)
    items = _non_padding(items)
    groups: list[tuple[ReactionOperator | None, list[Reaction]]] = []
    current_op = None
    current_nums = []
    for item in items:
        val = item.value
        if isinstance(val, str) and val.strip() in (":", "#"):
            groups.append((current_op, current_nums))
            current_op = (
                ReactionOperator.ADD
                if val.strip() == ":"
                else ReactionOperator.SUBTRACT
            )
            current_nums = []
        else:
            current_nums.append(Reaction(int(val)))
    groups.append((current_op, current_nums))

    def fold_multiply(nums):
        expr = nums[0]
        for n in nums[1:]:
            expr = expr * n
        return expr

    expr = fold_multiply(groups[0][1])
    for op, nums in groups[1:]:
        term = fold_multiply(nums)
        expr = expr + term if op == ReactionOperator.ADD else expr - term
    node = syntax_node.ListNode("reaction expr")
    for n in original:
        node.append(n)
    expr._node = node
    return expr


def _mark_never_pad(nodes):
    for i, n in enumerate(nodes):
        if (
            isinstance(n, syntax_node.ValueNode)
            and n.padding is None
            and i + 1 < len(nodes)
            and not isinstance(nodes[i + 1], syntax_node.PaddingNode)
        ):
            n.never_pad = True
        if isinstance(n, syntax_node.ListNode):
            _mark_never_pad(n.nodes)


def _parse_multiplier_bins(tally_numbers_node) -> list[MultiplierBin]:
    """Parse a full FM card's ``tally numbers`` CST node into its bin sets."""
    raw = list(tally_numbers_node)
    _mark_never_pad(raw)
    items = _non_padding(raw)
    top_groups = [n for n in items if _is_group(n)]
    if not top_groups:
        # FM parenthesization rule 3: the whole card is one bin set with one
        # term, and no parens are used anywhere.
        return [MultiplierBin.from_items(items)]
    return [MultiplierBin.from_items(_group_body(g)) for g in top_groups]


class TallyMultiplier(DataInputAbstract, Numbered_MCNP_Object):
    """An ``FMn`` tally multiplier card.

    Multiplies tally ``n``'s flux/current by a cross-section-derived
    response function. Must be paired with a
    :class:`~montepy.data_inputs.tally.Tally` of the same number -- see
    :attr:`parent_tally`.

    .. versionadded:: 1.6.0b2
    """

    _KEYS_TO_PRESERVE = {"_parent_tally"}

    @staticmethod
    def _parser():
        return TallyParser()

    def _init_blank(self):
        super()._init_blank()
        self._old_number = self._generate_default_node(int, -1)
        self._bins = []
        self._parsed_bins = []
        self._include_total = False
        self._cumulative = False
        self._parent_tally = None

    def _jit_light_init(self, input):
        super()._jit_light_init(input)
        self._old_number = self._input_number

    def _parse_tree(self):
        super()._parse_tree()
        num = self._input_number
        self._old_number = copy.deepcopy(num)
        self._number = num
        self._parse_multiplier_body()

    def _generate_default_tree(self, **kwargs):
        ret = {}
        ret["start_pad"] = syntax_node.PaddingNode()
        ret["classifier"] = syntax_node.ClassifierNode()
        ret["classifier"].prefix = syntax_node.ValueNode(
            self._class_prefix().upper(), str, padding=None, never_pad=True
        )
        # A non-negative placeholder: ValueNode._reverse_engineer_formatting
        # reserves a leading sign column for any token starting with "-",
        # which would otherwise permanently corrupt this node's formatting
        # once a real (positive) tally number is assigned to it.
        ret["classifier"].number = self._generate_default_node(int, 1)
        ret["keyword"] = syntax_node.ValueNode(None, str, padding=None)
        tally_numbers = syntax_node.ListNode("tally numbers")
        end_node = syntax_node.ValueNode(None, str)
        ret["data"] = syntax_node.SyntaxNode(
            "tally list", {"tally": tally_numbers, "end": end_node}
        )
        ret["parameters"] = syntax_node.ParametersNode()
        self._tree = syntax_node.SyntaxNode("blank data tree", ret)

    @args_checked
    def __init__(
        self,
        input: InitInput = None,
        number: ty.PositiveInt = None,
        *,
        jit_parse: bool = True,
    ):
        Numbered_MCNP_Object.__init__(self, input, number, jit_parse=jit_parse)

    @staticmethod
    def _class_prefix() -> str:
        return "fm"

    @staticmethod
    def _has_number() -> bool:
        return True

    @staticmethod
    def _has_classifier() -> int:
        return 1

    @staticmethod
    def _parent_collections():
        return ()

    def _parse_multiplier_body(self):
        if self._input is None:
            return
        tally_list = self._tree["data"]
        end_node = tally_list["end"]
        end_val = str(end_node.value).upper() if end_node.value is not None else None
        self._include_total = end_val == "T"
        self._cumulative = end_val == "C"
        self._bins = _parse_multiplier_bins(tally_list["tally"])
        self._parsed_bins = list(self._bins)

    @make_prop_val_node("_old_number")
    def old_number(self):
        """The FM number as read from the input file."""
        pass

    @property
    @needs_full_ast
    def bins(self) -> list[MultiplierBin]:
        """The bin sets (top-level parenthesized groups) of this FM card."""
        return list(self._bins)

    @args_checked
    @needs_full_cst
    def add_bin(self, bin_: MultiplierBin) -> None:
        """Add a bin set to this FM card.

        Parameters
        ----------
        bin_ : MultiplierBin
            The bin set to add.
        """
        self._bins.append(bin_)

    @args_checked
    @needs_full_cst
    def remove_bin(self, bin_: MultiplierBin) -> None:
        """Remove a bin set from this FM card.

        Parameters
        ----------
        bin_ : MultiplierBin
            The bin set to remove.
        """
        self._bins.remove(bin_)

    @property
    @needs_full_ast
    def include_total(self) -> bool:
        """``True`` if a total bin (``T``) is appended."""
        return self._include_total

    @include_total.setter
    @args_checked
    @needs_full_cst
    def include_total(self, value: bool):
        self._include_total = value
        if value:
            self._cumulative = False

    @property
    @needs_full_ast
    def cumulative(self) -> bool:
        """``True`` if the bins are cumulative (``C``), with the last being the total."""
        return self._cumulative

    @cumulative.setter
    @args_checked
    @needs_full_cst
    def cumulative(self, value: bool):
        self._cumulative = value
        if value:
            self._include_total = False

    @property
    def parent_tally(self):
        """The :class:`~montepy.data_inputs.tally.Tally` this multiplier is linked to."""
        return self._parent_tally

    def _link_to_parent(self, tally: "montepy.data_inputs.tally.Tally"):
        if tally.multiplier is not None:
            warnings.warn(
                f"Multiple FM inputs were specified for tally: {self.old_number}.",
                MalformedInputWarning,
            )
        self._parent_tally = tally

    def link_to_problem(self, problem, *, deepcopy=False):
        super().link_to_problem(problem)

    @args_checked
    @needs_full_cst
    def clone(
        self, tally: "montepy.data_inputs.tally.Tally" = None
    ) -> "TallyMultiplier":
        """Create an independent copy of this ``FM`` card.

        Unlike the generic :meth:`~montepy.numbered_mcnp_object.Numbered_MCNP_Object.clone`,
        a ``TallyMultiplier`` has no independent number or collection of its
        own -- its number always matches its parent tally's -- so this is a
        bespoke override.

        Parameters
        ----------
        tally : Tally
            The tally to link the clone to. Its number is copied onto the
            clone, and the clone is registered as that tally's
            :attr:`~montepy.data_inputs.tally.Tally.multiplier`. If omitted,
            a detached, unregistered clone is returned instead.

        Returns
        -------
        TallyMultiplier
            The cloned ``FM`` card.
        """
        ret = copy.deepcopy(self)
        ret._parent_tally = None
        if tally is not None:
            ret.number = tally.number
            ret._old_number.value = tally.number
            tally.multiplier = ret
        return ret

    def _update_values(self):
        if self._bins != self._parsed_bins:
            tally_numbers_node = self._tree["data"]["tally"]
            tally_numbers_node.nodes.clear()
            wrap_each = len(self._bins) > 1
            for bin_ in self._bins:
                bin_node = bin_.node
                if wrap_each or bin_._own_item_count() > 1:
                    group = syntax_node.ListNode("tally group")
                    group.append(syntax_node.PaddingNode("("))
                    for n in bin_node.nodes:
                        group.append(n)
                    group.append(syntax_node.PaddingNode(")"))
                    tally_numbers_node.nodes.append(group)
                else:
                    for n in bin_node.nodes:
                        tally_numbers_node.nodes.append(n)
            self._parsed_bins = list(self._bins)
        else:
            for bin_ in self._bins:
                if bin_._node is not None:
                    bin_.node
        end_node = self._tree["data"]["end"]
        if self._include_total:
            end_node.value = "T"
        elif self._cumulative:
            end_node.value = "C"
        else:
            end_node.value = None

    def __str__(self):
        try:
            return f"{type(self).__name__}: {self.number}"
        except Exception:
            return f"{type(self).__name__}: (unparsed)"

    def __repr__(self):
        try:
            nbins = len(getattr(self, "_bins", []))
            return f"TALLY MULTIPLIER: {self.number}, bins: {nbins}"
        except Exception:
            return "TALLY MULTIPLIER: (unparsed)"

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
        if isinstance(material, montepy.Material):
            material = material.number
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
    same way ENDF splits total/elastic/inelastic/capture. The negative
    aliases (``TOTAL_MCNP``, ``ABSORPTION``, etc.) are MCNP's own special
    reaction-number aliases, computed directly from transport data rather
    than corresponding to a single ENDF MT channel.

    .. versionadded:: 1.6.0b2
    """

    def __init__(self, number: int):
        self._number = number
        self._left = None
        self._operator = None
        self._right = None

    @property
    def number(self) -> int:
        """The raw ENDF (MT) or special (R) reaction number."""
        return self._number

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

# MCNP's own special reaction-number aliases (negative; computed directly
# from transport data, not a single ENDF MT channel).
Reaction.TOTAL_MCNP = Reaction(-1)
Reaction.ABSORPTION = Reaction(-2)
Reaction.ELASTIC_MCNP = Reaction(-3)
Reaction.HEATING = Reaction(-4)
Reaction.PHOTON_PRODUCTION = Reaction(-5)
Reaction.FISSION_MCNP = Reaction(-6)


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

    __slots__ = ("_constant", "_layers")

    @args_checked
    def __init__(self, constant: ty.Real, layers: list[AttenuatorLayer]):
        self._constant = constant
        self._layers = list(layers)

    @property
    def constant(self) -> float:
        """The scalar constant ``c`` for this attenuator set."""
        return self._constant

    @property
    def layers(self) -> list[AttenuatorLayer]:
        """The attenuating layers, in order."""
        return list(self._layers)

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

    __slots__ = ("_constant", "_material", "_reactions")

    @args_checked
    def __init__(
        self,
        constant: ty.Real,
        material: ty.Integral | None,
        reactions: list[ReactionExpression],
    ):
        self._constant = constant
        self._material = material
        self._reactions = list(reactions)

    @property
    def constant(self) -> float:
        """The scalar constant ``c`` for this multiplier set."""
        return self._constant

    @property
    def material(self) -> int | None:
        """The material number, or ``None`` for "current cell's material"."""
        return self._material

    @property
    def reactions(self) -> list[ReactionExpression]:
        """One :class:`~montepy.data_inputs.tally_multiplier.ReactionExpression` per output bin this set creates."""
        return list(self._reactions)

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
            and self._material == other._material
            and self._reactions == other._reactions
        )

    def __repr__(self):
        return f"MultiplierSet({self._constant}, {self._material}, {self._reactions!r})"


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

    __slots__ = ("_constant", "_kind")

    @args_checked
    def __init__(self, constant: ty.Real, kind: SpecialMultiplier):
        self._constant = constant
        self._kind = kind

    @property
    def constant(self) -> float:
        """The scalar constant ``c`` for this special multiplier set."""
        return self._constant

    @property
    def kind(self) -> SpecialMultiplier:
        """Which special multiplier option this is."""
        return self._kind

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

    __slots__ = ("_terms", "_attenuator")

    def __init__(
        self,
        terms: list[MultiplierSet | SpecialMultiplierSet],
        attenuator: AttenuatorSet | None = None,
    ):
        self._terms = list(terms)
        self._attenuator = attenuator

    @property
    def terms(self) -> list[MultiplierSet | SpecialMultiplierSet]:
        """The multiplier/special-multiplier sets in this bin set."""
        return list(self._terms)

    @property
    def attenuator(self) -> AttenuatorSet | None:
        """The attenuator set for this bin set, if any."""
        return self._attenuator

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
        return cls(terms, attenuator)

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
    return expr


def _parse_multiplier_bins(tally_numbers_node) -> list[MultiplierBin]:
    """Parse a full FM card's ``tally numbers`` CST node into its bin sets."""
    items = _non_padding(list(tally_numbers_node))
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
        ret["classifier"].number = self._generate_default_node(int, -1)
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

    @make_prop_val_node("_old_number")
    def old_number(self):
        """The FM number as read from the input file."""
        pass

    @property
    @needs_full_ast
    def bins(self) -> list[MultiplierBin]:
        """The bin sets (top-level parenthesized groups) of this FM card."""
        return list(self._bins)

    @property
    @needs_full_ast
    def include_total(self) -> bool:
        """``True`` if a total bin (``T``) is appended."""
        return self._include_total

    @property
    @needs_full_ast
    def cumulative(self) -> bool:
        """``True`` if the bins are cumulative (``C``), with the last being the total."""
        return self._cumulative

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

    def _update_values(self):
        pass

    def __str__(self):
        try:
            return f"TALLY MULTIPLIER: {self.number}"
        except Exception:
            return "TALLY MULTIPLIER: (unparsed)"

    def __repr__(self):
        try:
            nbins = len(getattr(self, "_bins", []))
            return f"TALLY MULTIPLIER: {self.number}, bins: {nbins}"
        except Exception:
            return "TALLY MULTIPLIER: (unparsed)"

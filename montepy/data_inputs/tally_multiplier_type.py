# Copyright 2024, Battelle Energy Alliance, LLC All Rights Reserved.

from enum import unique, Enum


@unique
class ReactionOperator(Enum):
    """The combinator between reaction numbers in an FM reaction list.

    See MCNP manual section 5.9.7, footnote 4: a space means multiply, a
    colon means add, and a pound sign means subtract, with multiply binding
    tighter than add/subtract.

    .. versionadded:: 1.6.0b2
    """

    MULTIPLY = " "
    ADD = ":"
    SUBTRACT = "#"


@unique
class SpecialMultiplier(Enum):
    """The ``c k`` special-multiplier flags (FM spec footnote 2).

    A closed, fixed 3-value set with no arithmetic use case, unlike
    reaction numbers, so unlike :class:`~montepy.data_inputs.tally_multiplier.Reaction`
    this is a real :class:`~enum.Enum`.

    .. versionadded:: 1.6.0b2
    """

    INVERSE_WEIGHT = -1
    """The tally is multiplied by 1/weight; the tally is the number of tracks (or collisions for F5)."""
    INVERSE_VELOCITY = -2
    """The tally is multiplied by 1/velocity; the tally is the neutron population or removal lifetime."""
    FIRST_INTERACTION_XS = -3
    """The tally is multiplied by the microscopic cross section of the first interaction."""

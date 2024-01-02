# Copyright 2024, Battelle Energy Alliance, LLC All Rights Reserved.
from enum import Enum


class Operator(Enum):
    """
    Enumeration of the allowed geometry set logic.
    """

    INTERSECTION = "*"
    """
    Represents the intersection of sets.
    """
    UNION = ":"
    """
    Represents the union of sets.
    """
    COMPLEMENT = "#"
    """
    Represents the complement of a set.
    """
    _SHIFT = ">"
    """
    Internal operator essentially equivalent to No-op.

    This is used to properly handle parentheses while parsing.
    """

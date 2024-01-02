# Copyright 2024, Battelle Energy Alliance, LLC All Rights Reserved.
from enum import Enum


class Shortcuts(Enum):
    """
    Enumeration of the possible MCNP shortcuts.

    .. versionadded:: 0.2.0
        This was added with the major parser rework.
    """

    REPEAT = "r"
    """
    A repeated entry shortcut.
    """
    JUMP = "j"
    """
    A jump entry, which counts as a default entry.
    """
    INTERPOLATE = "i"
    """
    A linear interpolation.
    """
    LOG_INTERPOLATE = "ilog"
    """
    A logarithmic interpolation.
    """
    MULTIPLY = "m"
    """
    a multiplication of the previous entry.
    """

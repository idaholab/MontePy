# Copyright 2024, Battelle Energy Alliance, LLC All Rights Reserved.
from montepy.errors import UnsupportedFeature

"""
Constants related to how MCNP inputs are formatted, and MontePy behavior.
"""

rel_tol = 1e-9
"""
Relative tolerance passed to math.isclose.

:rtype: float
"""

abs_tol = 0.0
"""
Absolute tolerance passed to math.isclose.

:rtype: float
"""


BLANK_SPACE_CONTINUE = 5
"""
Number of spaces in a new line before it's considered a continuation.
"""

LINE_LENGTH = {(5, 1, 60): 80, (6, 1, 0): 80, (6, 2, 0): 128}
"""
The number of characters allowed in a line for each MCNP version.
"""

DEFAULT_VERSION = (6, 2, 0)
"""
The default version of MCNP to use.
"""

TABSIZE = 8
"""
How many spaces a tab is expand to.
"""

ASCII_CEILING = 127
"""
The maximum allowed code point allowed by ASCII.

Source: `Wikipedia <https://en.wikipedia.org/wiki/ASCII>`_
"""


def get_max_line_length(mcnp_version=DEFAULT_VERSION):
    """
    Gets the maximum allowed length for an input line for a specific MCNP version.

    The version must be a three component tuple e.g., (6, 2, 0) and (5, 1, 60).
    Line lengths inferred from:

    | C. J. Werner et al., “MCNP Version 6.2 Release Notes,” LA-UR--18-20808, 1419730, Feb. 2018. doi: 10.2172/1419730. section 2.6.2

    Prior MCNP release version numbers were taken from `RSICC <https://rsicc.ornl.gov/codes/ccc/ccc8/ccc-810.html>`_.

    :param mcnp_version: The version of MCNP that the input is intended for.
    :type mcnp_version: tuple
    :returns: The number of characters allowed in a line.
    :rtype: int
    """
    if mcnp_version >= DEFAULT_VERSION:
        return LINE_LENGTH[DEFAULT_VERSION]
    try:
        return LINE_LENGTH[mcnp_version]
    except KeyError:
        raise UnsupportedFeature(f"MCNP Version {mcnp_version} is not supported.")

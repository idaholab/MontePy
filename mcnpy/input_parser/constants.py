BLANK_SPACE_CONTINUE = 5

"""
Line lengths inferred from:
    C. J. Werner et al., “MCNP Version 6.2 Release Notes,” LA-UR--18-20808, 1419730, Feb. 2018. doi: 10.2172/1419730.
    section 2.6.2

Prior MCNP release version numbers were taken from RSICC:
    https://rsicc.ornl.gov/codes/ccc/ccc8/ccc-810.html
"""

LINE_LENGTH = {
    (5, 1, 60): 80,
    (6, 1, 0): 80,
    (6, 2, 0): 128
}

DEFAULT_VERSION = (6,2,0)

def get_max_line_length(mcnp_version= DEFAULT_VERSION):
    """
    Gets the maximum allowed length for an input line for a specific MCNP version.

    The version must be a three component tuple e.g., (6, 2, 0) and (5, 1, 60). 

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


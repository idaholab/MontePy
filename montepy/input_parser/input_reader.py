# Copyright 2024-2025, Battelle Energy Alliance, LLC All Rights Reserved.
import montepy
from montepy.constants import DEFAULT_VERSION

import io
import os


def read_input(
    destination: str | os.PathLike | io.TextIOBase,
    mcnp_version: tuple[int, int, int] = DEFAULT_VERSION,
    replace: bool = True,
    *,
    jit_parse: bool = True,
):
    """Reads the specified MCNP Input file.

    The MCNP version must be a three component tuple e.g., (6, 2, 0) and (5, 1, 60).

    Notes
    -----
    if a stream is provided. It will not be closed by this function.

    .. warning::

        Probably should warn about just-in-time parsing.

    Parameters
    ----------
    destination : io.TextIOBase, str, os.PathLike
        the path to the input file to read, or a readable stream.
    mcnp_version : tuple
        The version of MCNP that the input is intended for.
    replace : bool
        replace all non-ASCII characters with a space (0x20)
    jit_parse : bool
        Whether to do just-in-time parsing

    Returns
    -------
    MCNP_Problem
        The MCNP_Problem instance representing this file.

    Raises
    ------
    UnsupportedFeature
        If an input format is used that MontePy does not support.
    MalformedInputError
        If an input has a broken syntax.
    NumberConflictError
        If two objects use the same number in the input file.
    BrokenObjectLinkError
        If a reference is made to an object that is not in the input
        file.
    UnknownElement
        If an isotope is specified for an unknown element.
    """
    problem = montepy.mcnp_problem.MCNP_Problem(destination)
    problem.mcnp_version = mcnp_version
    problem.parse_input(replace=replace, jit_parse=jit_parse)
    return problem

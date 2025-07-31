# Copyright 2024, Battelle Energy Alliance, LLC All Rights Reserved.
import montepy
from montepy.constants import DEFAULT_VERSION


def read_input(
    destination,
    mcnp_version: tuple[int] = DEFAULT_VERSION,
    replace: bool = True,
    multi_proc: bool = False,
    num_processes: int = None,
):
    """Reads the specified MCNP Input file.

    The MCNP version must be a three component tuple e.g., (6, 2, 0) and (5, 1, 60).

    Notes
    -----
    if a stream is provided. It will not be closed by this function.

    .. warning::

        If ``multi_proc=True`` is used on Windows extra care is needed.
        The entry point of the script needs to be import safe.
        See :ref:`windows_warning` for more details.

    .. versionchanged:: 1.2.0

        Added the ``multi_proc`` and ``num_processes`` arguments.

    Parameters
    ----------
    destination : io.TextIOBase, str, os.PathLike
        the path to the input file to read, or a readable stream.
    mcnp_version : tuple
        The version of MCNP that the input is intended for.
    replace : bool
        replace all non-ASCII characters with a space (0x20)
    multi_proc: bool
        If true multiprocessing will be used to speed up the parsing process, otherwise serial parsing is used.
    num_processes: int
        The number of python processes to start for parsing. If ``None`` the number of CPU cores will be used.

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
    RedundantParameterSpecification
        If an input specifies multiple conflicting parameters.
    """
    problem = montepy.mcnp_problem.MCNP_Problem(destination)
    problem.mcnp_version = mcnp_version
    problem.parse_input(
        replace=replace, multi_proc=multi_proc, num_processes=num_processes
    )
    return problem

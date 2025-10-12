# Copyright 2024-2025, Battelle Energy Alliance, LLC All Rights Reserved.
from collections import deque
import itertools
import io
import re
import os
import sly
import warnings

from montepy.constants import *
from montepy.exceptions import *
from montepy.input_parser.block_type import BlockType
from montepy.input_parser.input_file import MCNP_InputFile
from montepy.input_parser.mcnp_input import Input, Message, ReadInput, Title
from montepy.input_parser.read_parser import ReadParser
from montepy.utilities import is_comment


reading_queue = deque()


def read_input_syntax(input_file, mcnp_version=DEFAULT_VERSION, replace=True):
    """Creates a generator function to return a new MCNP input for
    every new one that is encountered.

    This is meant to just handle the MCNP input syntax, it does not
    semantically parse the inputs.

    The version must be a three component tuple e.g., (6, 2, 0) and (5, 1, 60).

    Parameters
    ----------
    input_file : MCNP_InputFile
        the path to the input file to be read
    mcnp_version : tuple
        The version of MCNP that the input is intended for.
    replace : bool
        replace all non-ASCII characters with a space (0x20)

    Returns
    -------
    generator
        a generator of MCNP_Object objects
    """
    global reading_queue
    reading_queue = deque()
    if input_file.is_stream:
        context = input_file
    else:
        context = input_file.open("r", replace=replace)
    with context as fh:
        yield from read_front_matters(fh, mcnp_version)
        yield from read_data(fh, mcnp_version)


def read_front_matters(fh, mcnp_version):
    """Reads the beginning of an MCNP file for all of the unusual data there.

    This is a generator function that will yield multiple :class:`MCNP_Input` instances.

    Warnings
    --------
    This function will move the file handle forward in state.

    Warnings
    --------
    This function will not close the file handle.

    Parameters
    ----------
    fh : MCNP_InputFile
        The file handle of the input file.
    mcnp_version : tuple
        The version of MCNP that the input is intended for.

    Returns
    -------
    MCNP_Object
        an instance of the Title class, and possible an instance of a
        Message class
    """
    is_in_message_block = False
    found_title = False
    lines = []
    raw_lines = []
    for i, line in enumerate(fh):
        if i == 0 and line.upper().startswith("MESSAGE:"):
            is_in_message_block = True
            raw_lines.append(line.rstrip())
            lines.append(line[9:])  # removes "MESSAGE: "
        elif is_in_message_block:
            if line.strip():
                raw_lines.append(line.rstrip())
                lines.append(line)
            # message block is terminated by a blank line
            else:
                yield Message(raw_lines, lines)
                is_in_message_block = False
        # title always follows complete message, or is first
        else:
            yield Title([line], line)
            break


def read_data(fh, mcnp_version, block_type=None, recursion=False):
    """Reads the bulk of an MCNP file for all of the MCNP data.

    This is a generator function that will yield multiple :class:`MCNP_Input` instances.

    Warnings
    --------
    This function will move the file handle forward in state.

    Warnings
    --------
    This function will not close the file handle.

    Parameters
    ----------
    fh : MCNP_InputFile
        The file handle of the input file.
    mcnp_version : tuple
        The version of MCNP that the input is intended for.
    block_type : BlockType
        The type of block this file is in. This is only used with
        partial files read using the ReadInput.
    recursion : bool
        Whether or not this is being called recursively. If True this
        has been called from read_data. This prevents the reading queue
        causing infinite recursion.

    Returns
    -------
    MCNP_Input
        MCNP_Input instances: Inputs that represent the data in the MCNP
        input.
    """
    current_file = fh
    line_length = get_max_line_length(mcnp_version)
    block_counter = 0
    if block_type is None:
        block_type = BlockType.CELL
    continue_input = False
    has_non_comments = False
    input_raw_lines = []
    terminate_reading = False

    def flush_block():
        nonlocal block_counter, block_type
        # keep parsing while there is input or termination has not been triggered
        if len(input_raw_lines) > 0 and not terminate_reading:
            yield from flush_input()
        block_counter += 1
        if block_counter < 3:
            block_type = BlockType(block_counter)

    def flush_input():
        nonlocal input_raw_lines, terminate_reading
        # IF 3  BLOCKS are parsed, the rest should be ignored with a warning and print 3 lines
        if block_counter == 3:
            joined_lines = "\n".join(input_raw_lines[0:3])
            msg = f"Unexpected input after line {current_file.lineno - 1}\n line content: {joined_lines}\n"
            warnings.warn(
                msg,
                UndefinedBlock,
                stacklevel=6,
            )
            terminate_reading = True
        start_line = current_file.lineno + 1 - len(input_raw_lines)
        input = Input(
            input_raw_lines,
            block_type,
            current_file,
            start_line,
        )
        try:
            read_input = ReadInput(
                input_raw_lines, block_type, current_file, start_line
            )
            reading_queue.append((block_type, read_input.file_name, current_file.path))
            yield None
        except ValueError as e:
            if isinstance(e, ParsingError):
                raise e
            yield input
        continue_input = False
        input_raw_lines = []

    for line in fh:
        line = line.expandtabs(TABSIZE)
        line_is_comment = is_comment(line)
        # transition to next block with blank line
        if not line.strip():
            yield from flush_block()
            has_non_comments = False
            continue
        # if a new input
        if (
            line[0:BLANK_SPACE_CONTINUE].strip()
            and not continue_input
            and not line_is_comment
            and has_non_comments
            and input_raw_lines
        ):
            yield from flush_input()
        # die if it is a vertical syntax format
        start_o_line = line[0:BLANK_SPACE_CONTINUE]
        # eliminate comments, and inputs that use # for other syntax
        if (
            "#" in start_o_line
            and not line_is_comment
            and start_o_line.strip().startswith("#")
        ):
            input_raw_lines.append(line.rstrip())
            input = next(flush_input())
            lineno = 1
            token = sly.lex.Token()
            token.value = "#"
            index = line[0:BLANK_SPACE_CONTINUE].index("#")
            err = {"message": "", "token": token, "line": lineno, "index": index}
            raise UnsupportedFeature(
                "Vertical Input encountered, which is not supported by Montepy",
                input,
                [err],
            )
        # cut line down to allowed length
        old_line = line
        line = line[:line_length]
        if len(old_line) != len(line):
            comment_free = old_line.split("$")[0]
            if len(comment_free.rstrip()) > line_length and not COMMENT_FINDER.match(
                line
            ):
                warnings.warn(
                    f"The line number {fh.lineno} exceeded the allowed line length of: {line_length} for MCNP{mcnp_version} "
                    f'and "{comment_free[line_length -1:].rstrip()}" was removed.',
                    LineOverRunWarning,
                )
            # if extra length is a comment keep it long
            else:
                line = old_line
        if line.endswith(" &\n"):
            continue_input = True
        else:
            continue_input = False
        has_non_comments = has_non_comments or not line_is_comment
        input_raw_lines.append(line.rstrip())
    yield from flush_block()

    if not recursion:
        path = os.path.dirname(fh.name)
        while reading_queue:
            block_type, file_name, parent = reading_queue.popleft()
            new_wrapper = MCNP_InputFile(os.path.join(path, file_name), parent)
            with new_wrapper.open("r") as sub_fh:
                new_wrapper = MCNP_InputFile(file_name, parent)
                for input in read_data(sub_fh, mcnp_version, block_type, True):
                    yield input

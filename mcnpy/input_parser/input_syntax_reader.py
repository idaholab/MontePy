from .block_type import BlockType
from collections import deque
from .. import errors
import itertools
import io
from mcnpy.input_parser.constants import *
from mcnpy.input_parser.mcnp_input import Card, Comment, Message, ReadCard, Title
import os
import warnings

reading_queue = []


def read_input_syntax(input_file, mcnp_version=DEFAULT_VERSION):
    """
    Creates a generator function to return a new MCNP input card for
    every new one that is encountered.

    This is meant to just handle the MCNP input syntax, it does not
    semantically parse the inputs.

    The version must be a three component tuple e.g., (6, 2, 0) and (5, 1, 60).


    :param input_file: the path to the input file to be read
    :type input_file: str
    :param mcnp_version: The version of MCNP that the input is intended for.
    :type mcnp_version: tuple
    :returns: a generator of MCNP_Input objects
    :rtype: generator
    """
    global reading_queue
    reading_queue = deque()
    with open(input_file, "r") as fh:
        yield from read_front_matters(fh, mcnp_version)
        yield from read_data(fh, mcnp_version)


def read_front_matters(fh, mcnp_version):
    """
    Reads the beginning of an MCNP file for all of the unusual data there.

    This is a generator function that will yield multiple MCNP_Input instances.

    Warning: this function will move the file handle forward in state.
    Warning: this function will not close the file handle

    :param fh: The file handle of the input file.
    :type fh: io.TextIoWrapper
    :param mcnp_version: The version of MCNP that the input is intended for.
    :type mcnp_version: tuple
    :return: an instance of the Title class, and possible an instance of a Message class
    :rtype: MCNP_Input
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
    """
    Reads the bulk of an MCNP file for all of the MCNP data.

    This is a generator function that will yield multiple MCNP_Input instances.

    Warning: this function will move the file handle forward in state.
    Warning: this function will not close the file handle

    :param fh: The file handle of the input file.
    :type fh: io.TextIoWrapper
    :param mcnp_version: The version of MCNP that the input is intended for.
    :type mcnp_version: tuple
    :param block_type: The type of block this file is in. This is only used with partial files read using the ReadCard.
    :type block_type: BlockType
    :param recusrion: Whether or not this is being called recursively. If True this has been called
                         from read_data. This prevents the reading queue causing infinite recursion.
    :type recursion: bool
    :return: MCNP_input instances, Card or Comment that represent the data in the MCNP input
    :rtype: MCNP_input

    """
    line_length = get_max_line_length(mcnp_version)
    block_counter = 0
    if block_type is None:
        block_type = BlockType.CELL
    is_in_comment = False
    continue_card = False
    comment_raw_lines = []
    card_raw_lines = []

    def flush_block():
        nonlocal block_counter, block_type, comment_raw_lines
        if len(card_raw_lines) > 0:
            yield from flush_card()
        if is_in_comment and comment_raw_lines:
            yield from flush_comment()
        block_counter += 1
        if block_counter < 3:
            block_type = BlockType(block_counter)

    def flush_comment():
        nonlocal comment_raw_lines
        words = []
        yield Comment(comment_raw_lines, len(card_raw_lines))
        comment_raw_lines = []
        is_in_comment = False

    def flush_card():
        nonlocal card_raw_lines
        card = Card(card_raw_lines, block_type)
        if len(card.words) > 0 and card.words[0].lower() == "read":
            card = ReadCard(card_raw_lines, block_type)
            reading_queue.append((block_type, card.file_name))
            yield None
        else:
            yield card
        continue_card = False
        card_raw_lines = []

    def is_comment(line):
        upper_start = line[0 : BLANK_SPACE_CONTINUE + 1].upper()
        non_blank_comment = upper_start and line.lstrip().upper().startswith("C ")
        if non_blank_comment:
            return True
        blank_comment = "C\n" == upper_start.lstrip() or "C\r\n" == upper_start.lstrip()
        return blank_comment or non_blank_comment

    for line in fh:
        # transition to next block with blank line
        if not line.strip():
            yield from flush_block()
            continue
        # if it's a C comment
        if is_comment(line):
            comment_raw_lines.append(line.rstrip()[:line_length])
            is_in_comment = True
        # if it's part of a card
        else:
            # if a new card
            if (
                line[0:BLANK_SPACE_CONTINUE].strip()
                and not continue_card
                and card_raw_lines
            ):
                yield from flush_card()
            # just terminated a comment
            if is_in_comment and comment_raw_lines:
                yield from flush_comment()
            # die if it is a vertical syntax format
            if "#" in line[0:BLANK_SPACE_CONTINUE]:
                raise errors.UnsupportedFeature("Vertical Input format is not allowed")
            # throw away comments
            line = line.split("$")[0]
            # cut line down to allowed length
            old_line = line
            line = line[:line_length]
            if len(old_line) != len(line):
                warnings.warn(
                    f"The line: {old_line} exceeded the allowed line length of: {line_length} for MCNP {mcnp_version}",
                    errors.LineOverRunWarning,
                )
            if line.endswith(" &\n"):
                continue_card = True
            else:
                continue_card = False
            card_raw_lines.append(line.rstrip())
    yield from flush_block()

    if not recursion:
        # ensure fh is a file reader, ignore StringIO
        if isinstance(fh, io.TextIOWrapper):
            path = os.path.dirname(fh.name)
            while reading_queue:
                block_type, file_name = reading_queue.popleft()
                with open(os.path.join(path, file_name), "r") as sub_fh:
                    for input_card in read_data(sub_fh, mcnp_version, block_type, True):
                        yield input_card

from .block_type import BlockType
from .. import errors
import itertools
from .mcnp_input import Card, Comment, Message, Title
import re

BLANK_SPACE_CONTINUE = 5

def read_input_syntax(input_file):
    """
    Creates a generator function to return a new MCNP input card for
    every new one that is encountered.

    This is meant to just handle the MCNP input syntax, it does not
    semantically parse the inputs.

    :param input_file: the path to the input file to be read
    :type input_file: str
    """
    with open(input_file, "r") as fh:
        yield from read_front_matters(fh)
        yield from read_data(fh)


def read_front_matters(fh):
    """
    Reads the beginning of an MCNP file for all of the unusual data there.

    This is a generator function that will yield multiple MCNP_Input instances.

    Warning: this function will move the file handle forward in state.
    Warning: this function will not close the file handle

    :param fh: The file handle of the input file.
    :type fh: io.TextIoWrapper
    :return: an instance of the Title class, and possible an instance of a Message class
    :rtype: MCNP_Input
    """
    is_in_message_block = False
    found_title = False
    lines = []
    for i, line in enumerate(fh):
        if i == 0 and line.startswith("MESSAGE:"):
            is_in_message_block = True
            lines.append(line.strip("MESSAGE: "))
        elif is_in_message_block:
            if line.strip():
                lines.append(line)
            # message block is terminated by a blank line
            else:
                yield Message(lines)
                is_in_message_block = False
        # title always follows complete message, or is first
        else:
            yield Title(line)
            break


def read_data(fh):
    """
    Reads the bulk of an MCNP file for all of the MCNP data.

    This is a generator function that will yield multiple MCNP_Input instances.

    Warning: this function will move the file handle forward in state.
    Warning: this function will not close the file handle

    :param fh: The file handle of the input file.
    :type fh: io.TextIoWrapper
    :return: MCNP_input instances, Card or Comment that represent the data in the MCNP input
    :rtype: MCNP_input

    """
    commentFinder = re.compile(f"^\s{{0,{BLANK_SPACE_CONTINUE-1}}}C\s", re.IGNORECASE)
    block_counter = 0
    block_type = BlockType.CELL
    is_in_comment = False
    continue_card = False
    words = []
    for line in fh:
        # transition to next block with blank line
        if not line.strip():
            # flush current card
            if is_in_comment:
                yield Comment(words)
            else:
                yield Card(block_type, words)
            words = []
            block_counter += 1
            if block_counter < 3:
                block_type = BlockType(block_counter)
            # if reached the final input block
            else:
                break
        # if not a new block
        else:
            if commentFinder.match(line):
                if not is_in_comment:
                    if words:
                        yield Card(block_type, words)
                    # removes leading comment info
                    words = [commentFinder.split(line)[1]]
                    is_in_comment = True
                else:
                    words.append(commentFinder.split(line)[1])
            # if not a comment
            else:
                # terminate comment
                if is_in_comment:
                    is_in_comment = False
                    yield Comment(words)
                    words = []
                if "#" in line[0:BLANK_SPACE_CONTINUE]:
                    raise errors.UnsupportedFeature(
                        "Vertical Input format is not allowed"
                    )
                # throw away comments
                line = line.split("$")[0]
                # removes continue card
                temp_words = line.replace(" &", "").split()
                # if beginning a new card
                if line[0:BLANK_SPACE_CONTINUE].strip() and not continue_card:
                    if words:
                        yield Card(block_type, words)
                    words = temp_words
                else:
                    words = words + temp_words
                if line.endswith(" &"):
                    continue_card = True
                else:
                    continue_card = False
    if is_in_comment:
        yield Comment(words)
    else:
        yield Card(block_type, words)

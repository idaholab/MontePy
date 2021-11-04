from enum import Enum, unique
import itertools
import re


def read_input(input_file):
    """
    Creates a generator function to return a new MCNP input card for 
    every new one that is encountered.

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
    for i,line in enumerate(fh):
        if i == 0 and line.startswith("MESSAGE:"):
            is_in_message_block = True
            lines.append(line.strip("MESSAGE: "))
        elif is_in_message_block:
            if line.strip():
                lines.append(line)
            #message block is terminated by a blank line
            else:
                yield Message(lines)
                is_in_message_block = False
        #title always follows complete message, or is first
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
    commentFinder = re.compile("^\s{0,4}C\s",re.IGNORECASE)
    block_counter = 0
    block_type = BlockType.CELL
    is_in_card = False
    is_in_comment = False
    continue_card = False
    words = []
    for line in fh:
        #transition to next block with blank line
        if not line.strip():
            block_counter += 1
            if block_counter < 3:
                block_type = BlockType(block_counter)
            #if reached the final input block
            else:
                break
        #if not a new block
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
            #if not a comment
            else:
                #terminate comment
                if is_in_comment:
                    is_in_comment = False
                    yield Comment(words)
                    words = []
                #throw away comments
                line = line.split("$")[0]
                #removes continue card
                temp_words = line.replace(" &","").split()
                # if beginning a new card
                if line[0:4].strip() and not continue_card:
                    if words:
                        yield Card(block_type, words)
                    words = temp_words
                else: 
                    words = words + temp_words
                if line.endswith(" &"):
                    continue_card = True
                else:
                    continue_card = False

class MCNP_Input:
    """
    Object to represent a single coherent MCNP input, such as a card.
    """
    pass

class Message(MCNP_Input):
    """
    Object to represent an MCNP message.
    
    These are blocks at the beginning of an input that are printed in the output.
    """
    def __init__(self, lines):
        """
        :param lines: the strings of each line in the message block
        :type lines: list
        """
        assert isinstance(lines, list)
        self.__lines = lines

    def __str__(self):
        ret = "MESSAGE:\n"
        for line in self.__lines:
            ret = ret + line  
        return ret

    @property
    def lines(self):
        """
        The lines of input for the message block.
        
        Each entry is a string of that line in the message block
        """
        return self.__lines

class Title(MCNP_Input):
    """
    Object to represent the title for an MCNP problem
    """
    def __init__(self, title):
        self.__title = title

    @property
    def title(self):
        "The string of the title set for this problem"
        return self.__title

    def __str__(self):
        return f"title: {self.__title}"

class Comment(MCNP_Input):
    """
    Object to represent a full line comment in an MCNP problem.
    """
    def __init__(self, lines):
        """
        :param lines: the strings of each line in this comment block
        :type lines: list
        """
        assert isinstance(lines, list)
        self.__lines = lines

    def __str__(self):
        ret = "COMMENT:\n"
        for line in self.__lines:
            ret = ret + line 
        return ret

    @property
    def lines(self):
        """
        The lines of input in this comment block.
       
        Each entry is a string of that line in the message block.
        The comment beginning "C " has been stripped out 
        """
        return self.__lines

class Card(MCNP_Input):
    """
    Represents a single MCNP "card" e.g. a single cell definition.
    """

    def __init__(self, block_type, words):
        """
        :param block_type: An enum showing which of three MCNP blocks this was inside of.
        :type block_type: BlockType
        :param words: a list of the string representation of the words for the card definition
                        for example a material definition may contain: 'M10', '10001.70c', '0.1'
        :type words: list
        """
        assert isinstance(block_type, BlockType)
        self.__words = words
        self.__block_type = block_type

    def __str__(self):
        return f"CARD: {self.__block_type}: {self.__words}"

    @property
    def words(self):
        """
        A list of the string representation of the words for the card definition.
          
        For example a material definition may contain: 'M10', '10001.70c', '0.1'
        """
        return self.__words

    @property
    def block_type(self):
        """
        Enum representing which block of the MCNP input this came from
        """
        return self.__block_type

@unique
class BlockType(Enum):
    CELL = 0
    SURFACE = 1
    DATA = 2


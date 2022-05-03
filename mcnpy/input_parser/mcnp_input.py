from abc import ABC, abstractmethod
from mcnpy.input_parser.block_type import BlockType
from mcnpy.input_parser.constants import BLANK_SPACE_CONTINUE
import re


class MCNP_Input(ABC):
    """
    Object to represent a single coherent MCNP input, such as a card.
    """

    def __init__(self, input_lines):
        """
        :param input_lines: the lines read straight from the input file.
        :type input_lines: list
        """
        assert isinstance(input_lines, list)
        for line in input_lines:
            assert isinstance(line, str)
        self._input_lines = input_lines
        self._mutated = False

    @property
    def input_lines(self):
        """The lines of the input read straight from the input file

        :rtype: list
        """
        return self._input_lines

    @property
    def mutated(self):
        """If true this input has been mutated by the user, and needs to be formatted

        :rtype: bool
        """
        return self._mutated

    @abstractmethod
    def format_for_mcnp_input(self, mcnp_version):
        """
        Creates a string representation of this card that can be
        written to file.

        :param mcnp_version: The tuple for the MCNP version that must be exported to.
        :type mcnp_version: tuple
        :return: a list of strings for the lines that this card will occupy.
        :rtype: list
        """
        pass


class Card(MCNP_Input):
    """
    Represents a single MCNP "card" e.g. a single cell definition.
    """

    def __init__(self, input_lines, block_type):
        """
        :param input_lines: the lines read straight from the input file.
        :type input_lines: list
        :param block_type: An enum showing which of three MCNP blocks this was inside of.
        :type block_type: BlockType
        """
        super().__init__(input_lines)
        assert isinstance(block_type, BlockType)
        words = []
        for line in input_lines:
            line = line.split("$")[0]
            words += line.replace(" &", "").split()
        self._words = words
        self._block_type = block_type

    def __str__(self):
        return f"CARD: {self._block_type}: {self._words}"

    @property
    def words(self):
        """
        A list of the string representation of the words for the card definition.

        For example a material definition may contain: 'M10', '10001.70c', '0.1'
        :rtype: list
        """
        return self._words

    @property
    def block_type(self):
        """
        Enum representing which block of the MCNP input this came from
        :rtype: BlockType
        """
        return self._block_type

    def format_for_mcnp_input(self, mcnp_version):
        pass


class ReadCard(Card):
    """
    A card for the read card that reads another input file
    """

    def __init__(self, input_lines, block_type):
        super().__init__(input_lines, block_type)
        file_finder = re.compile("file=(?P<file>[\S]+)", re.I)
        for word in self.words[1:]:
            match = file_finder.match(word)
            if match:
                self._file_name = match.group("file")

    @property
    def file_name(self):
        """
        The relative path to the filename specified in this read card.
        :rtype: str
        """
        return self._file_name


class Comment(MCNP_Input):
    """
    Object to represent a full line comment in an MCNP problem.
    """

    def __init__(self, input_lines, card_line=0):
        """
        :param input_lines: the lines read straight from the input file.
        :type input_lines: list
        :param card_line: The line number in a parent input card where this Comment appeared
        :type card_line: int
        """
        super().__init__(input_lines)
        buff = []
        for line in input_lines:
            buff.append(
                re.split(f"^\s{{0,{BLANK_SPACE_CONTINUE-1}}}C\s", line, re.I)[
                    0
                ].rstrip()
            )
        self._lines = buff
        self._cutting = False
        self._card_line = card_line

    def __str__(self):
        ret = "COMMENT:\n"
        for line in self._lines:
            ret += line + "\n"
        return ret

    @property
    def lines(self):
        """
        The lines of input in this comment block.

        Each entry is a string of that line in the message block.
        The comment beginning "C " has been stripped out
        :rtype: list
        """
        return self._lines

    def format_for_mcnp_input(self, mcnp_version):
        line_length = 0
        if mcnp_version[:2] == (6, 2):
            line_length = 128
        ret = []
        for line in self.lines:
            ret.append("C " + line[0 : line_length - 3])
        return ret

    @property
    def is_cutting_comment(self):
        """
        Whether or not this Comment "cuts" an input card.
        """
        return self._cutting

    def snip(self):
        """
        Set this Comment to be a cutting comment
        """
        self._cutting = True


class Message(MCNP_Input):
    """
    Object to represent an MCNP message.

    These are blocks at the beginning of an input that are printed in the output.
    """

    def __init__(self, input_lines, lines):
        """
        :param input_lines: the lines read straight from the input file.
        :type input_lines: list
        :param lines: the strings of each line in the message block
        :type lines: list
        """
        super().__init__(input_lines)
        assert isinstance(lines, list)
        buff = []
        for line in lines:
            buff.append(line.rstrip())
        self._lines = buff

    def __str__(self):
        ret = "MESSAGE:\n"
        for line in self._lines:
            ret += line + "\n"
        return ret

    @property
    def lines(self):
        """
        The lines of input for the message block.

        Each entry is a string of that line in the message block
        :rtype: list
        """
        return self._lines

    def format_for_mcnp_input(self, mcnp_version):
        ret = []
        line_length = 0
        if mcnp_version[:2] == (6, 2):
            line_length = 128
        for i, line in enumerate(self.lines):
            if i == 0:
                ret.append("MESSAGE: " + line[0 : line_length - 10])
            else:
                ret.append(line[0 : line_length - 1])
        ret.append("")
        return ret


class Title(MCNP_Input):
    """
    Object to represent the title for an MCNP problem
    """

    def __init__(self, input_lines, title):
        """
        :param input_lines: the lines read straight from the input file.
        :type input_lines: list
        :param title: The string for the title of the problem.
        :type title: str
        """
        super().__init__(input_lines)
        assert isinstance(title, str)
        self._title = title.rstrip()

    @property
    def title(self):
        """The string of the title set for this problem
        :rtype: str
        """
        return self._title

    def __str__(self):
        return f"TITLE: {self._title}"

    def format_for_mcnp_input(self, mcnp_version):
        line_length = 0
        if mcnp_version[:2] == (6, 2):
            line_length = 128
        return [self.title[0 : line_length - 1]]

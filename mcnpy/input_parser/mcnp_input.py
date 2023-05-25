from abc import ABC, abstractmethod
import math
from mcnpy.errors import *
from mcnpy.input_parser.block_type import BlockType
from mcnpy.constants import BLANK_SPACE_CONTINUE, get_max_line_length
from mcnpy.input_parser.read_parser import ReadParser
from mcnpy.input_parser.tokens import CellLexer, SurfaceLexer, DataLexer
import re


class Jump:
    """
     Class to represent a default entry represented by a "jump".


    |     I get up and nothing gets me down
    |     You got it tough, I've seen the toughest around
    |     And I know, baby, just how you feel
    |     You gotta roll with the punches to get to what's real

    |     Oh, can't you see me standing here?
    |     I got my back against the record machine
    |     I ain't the worst that you've seen
    |     Oh, can't you see what I mean?

    |    Ah, might as well ...
    """

    def __str__(self):
        return "J"

    def __repr__(self):
        return f"Jump: {hex(id(self))}"

    def __bool__(self):
        raise TypeError("Jump doesn't have a truthiness or falsiness")

    def __eq__(self, other):
        return type(self) == type(other)

    def lower(self):
        """
        Hop.

        :rtype: str
        """
        return "j"

    def title(self):
        """
        Skip.

        :rtype: str
        """
        return "Jump"

    def upper(self):
        """
        Jump.

        :rtype: str
        """
        return "J"


class ParsingNode(ABC):
    """
    Object to represent a single coherent MCNP input, such as an input.

    :param input_lines: the lines read straight from the input file.
    :type input_lines: list
    """

    def __init__(self, input_lines):
        if not isinstance(input_lines, list):
            raise TypeError("input_lines must be a list")
        for line in input_lines:
            if not isinstance(line, str):
                raise TypeError(f"element: {line} in input_lines must be a string")
        self._input_lines = input_lines
        self._mutated = False

    @property
    def input_lines(self):
        """The lines of the input read straight from the input file

        :rtype: list
        """
        return self._input_lines

    @property
    def input_text(self):
        return "\n".join(self.input_lines)

    @abstractmethod
    def format_for_mcnp_input(self, mcnp_version):
        """
        Creates a string representation of this input that can be
        written to file.

        :param mcnp_version: The tuple for the MCNP version that must be exported to.
        :type mcnp_version: tuple
        :return: a list of strings for the lines that this input will occupy.
        :rtype: list
        """
        pass


class Input(ParsingNode):
    """
    Represents a single MCNP "Input" e.g. a single cell definition.

    :param input_lines: the lines read straight from the input file.
    :type input_lines: list
    :param block_type: An enum showing which of three MCNP blocks this was inside of.
    :type block_type: BlockType
    """

    SPECIAL_COMMENT_PREFIXES = ["fc", "sc"]
    """Prefixes for special comments like tally comments.
    
    :rtype: list
    """

    def __init__(self, input_lines, block_type):
        super().__init__(input_lines)
        if not isinstance(block_type, BlockType):
            raise TypeError("block_type must be BlockType")
        self._block_type = block_type

    def __str__(self):
        return f"INPUT: {self._block_type}"

    def __repr__(self):
        return f"INPUT: {self._block_type}: {self.input_lines}"

    @property
    def block_type(self):
        """
        Enum representing which block of the MCNP input this came from.

        :rtype: BlockType
        """
        return self._block_type

    def format_for_mcnp_input(self, mcnp_version):
        pass

    def tokenize(self):
        if self.block_type == BlockType.CELL:
            lexer = CellLexer()
        elif self.block_type == BlockType.SURFACE:
            lexer = SurfaceLexer()
        else:
            lexer = DataLexer()
        for token in lexer.tokenize(self.input_text):
            yield token


class ReadInput(Input):
    """
    A input for the read input that reads another input file

    :param input_lines: the lines read straight from the input file.
    :type input_lines: list
    :param block_type: An enum showing which of three MCNP blocks this was inside of.
    :type block_type: BlockType
    """

    _parser = ReadParser()

    def __init__(self, input_lines, block_type):
        super().__init__(input_lines, block_type)
        parse_result = self._parser.parse(self.tokenize())
        if not parse_result:
            raise ValueError("Not a valid Read Input")
        self._tree = parse_result
        self._parameters = self._tree["parameters"]

    @property
    def file_name(self):
        """
        The relative path to the filename specified in this read input.

        :rtype: str
        """
        return self._parameters["file"]["data"].value

    def __str__(self):
        return f"READ INPUT: Block_Type: {self.block_type}"

    def __repr__(self):
        return (
            f"READ INPUT: {self._block_type}: {self.input_lines} File: {self.file_name}"
        )

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
        line_length = get_max_line_length(mcnp_version)
        ret = []
        for line in self.lines:
            ret.append("C " + line[0 : line_length - 3])
        return ret

    @property
    def is_cutting_comment(self):
        """
        Whether or not this Comment "cuts" an input input.

        :rtype: bool
        """
        return self._cutting

    @property
    def input_line_num(self):
        """
        Which line of the parent input this comment came from.

        :rtype: int
        """
        return self._input_line_num

    def snip(self):
        """
        Set this Comment to be a cutting comment.
        """
        self._cutting = True


class Message(ParsingNode):
    """
    Object to represent an MCNP message.

    These are blocks at the beginning of an input that are printed in the output.

    :param input_lines: the lines read straight from the input file.
    :type input_lines: list
    :param lines: the strings of each line in the message block
    :type lines: list
    """

    def __init__(self, input_lines, lines):
        super().__init__(input_lines)
        if not isinstance(lines, list):
            raise TypeError("lines must be a list")
        for line in lines:
            if not isinstance(line, str):
                raise TypeError(f"line {line} in lines must be a string")
        buff = []
        for line in lines:
            buff.append(line.rstrip())
        self._lines = buff

    def __str__(self):
        return f"MESSAGE: {len(self._lines)} lines"

    def __repr__(self):
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
        line_length = get_max_line_length(mcnp_version)
        for i, line in enumerate(self.lines):
            if i == 0:
                ret.append("MESSAGE: " + line[0 : line_length - 10])
            else:
                ret.append(line[0 : line_length - 1])
        ret.append("")
        return ret


class Title(ParsingNode):
    """
    Object to represent the title for an MCNP problem

    :param input_lines: the lines read straight from the input file.
    :type input_lines: list
    :param title: The string for the title of the problem.
    :type title: str
    """

    def __init__(self, input_lines, title):
        """
        :param input_lines: the lines read straight from the input file.
        :type input_lines: list
        :param title: The string for the title of the problem.
        :type title: str
        """
        super().__init__(input_lines)
        if not isinstance(title, str):
            raise TypeError("title must be a string")
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
        line_length = get_max_line_length(mcnp_version)
        return [self.title[0 : line_length - 1]]

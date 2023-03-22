from abc import ABC, abstractmethod
import math
from mcnpy.errors import *
from mcnpy.input_parser.block_type import BlockType
from mcnpy.input_parser.constants import BLANK_SPACE_CONTINUE, get_max_line_length
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

    def format(self):
        """"""
        # TODO remove this
        # TODO complete shortcut recompression
        return "J "


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

    @property
    def mutated(self):
        """If true this input has been mutated by the user, and needs to be formatted

        :rtype: bool
        """
        return self._mutated

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


def parse_input_shortcuts(words, input=None):
    """
    Parses MCNP input shortcuts.

    E.g., ``2R``, ``1 10I 100``, ``2J``

    Returns a list of strings with all shortcuts decompressed or changed out.
    Jumps will be changed to :class:`mcnpy.input_parser.mcnp_input.Jump`.

    :param words: the list of strings or "words".
    :type words: list
    :returns: modified version of words with all compressions expanded.
    :rtype: list
    """
    number_parser = re.compile(r"(\d+\.*\d*[e\+\-]*\d*)")
    ret = []
    for i, word in enumerate(words):
        if i == 0:
            ret.append(word)
            continue
        letters = "".join(c for c in word if c.isalpha()).lower()
        if len(letters) >= 1:
            number = number_parser.search(word)
            if number:
                number = float(number.group(1))
            if letters == "r":
                try:
                    last_val = ret[-1]
                    assert (
                        not isinstance(last_val, Jump) and last_val and len(ret) > 1
                    )  # force last_val to be truthy
                    if number:
                        number = int(number)
                    else:
                        number = 1
                    ret += [last_val] * number
                except (IndexError, AssertionError) as e:
                    raise MalformedInputError(
                        input, "The repeat shortcut must come after a value"
                    )
            elif letters == "i":
                try:

                    begin = float(number_parser.search(ret[-1]).group(1))
                    for char in ["i", "m", "r", "i", "log"]:
                        if char in words[i + 1].lower():
                            raise IndexError

                    end = float(number_parser.search(words[i + 1]).group(1))
                    if number:
                        number = int(number)
                    else:
                        number = 1
                    spacing = (end - begin) / (number + 1)
                    for i in range(number):
                        new_val = begin + spacing * (i + 1)
                        ret.append(f"{new_val:g}")
                except (IndexError, TypeError, ValueError, AttributeError) as e:
                    raise MalformedInputError(
                        input,
                        "The interpolate shortcut must come between two values",
                    )
            elif letters == "m":
                try:
                    last_val = float(number_parser.search(ret[-1]).group(1))
                    if number is None:
                        raise MalformedInputError(
                            input,
                            "The multiply shortcut must have a multiplying value",
                        )
                    new_val = number * last_val
                    ret.append(f"{new_val:g}")

                except (IndexError, TypeError, ValueError, AttributeError) as e:
                    raise MalformedInputError(
                        input, "The multiply shortcut must come after a value"
                    )

            elif letters == "j":
                if number:
                    number = int(number)
                else:
                    number = 1
                ret += [Jump()] * number
            elif letters in {"ilog", "log"}:
                try:
                    begin = math.log(float(number_parser.search(ret[-1]).group(1)), 10)
                    end = math.log(
                        float(number_parser.search(words[i + 1]).group(1)), 10
                    )
                    if number:
                        number = int(number)
                    else:
                        number = 1
                    spacing = (end - begin) / (number + 1)
                    for i in range(number):
                        new_val = 10 ** (begin + spacing * (i + 1))
                        ret.append(f"{new_val:g}")

                except (IndexError, TypeError, ValueError, AttributeError) as e:
                    raise MalformedInputError(
                        input,
                        "The log interpolation shortcut must come between two values",
                    )
            else:
                ret.append(word)
        else:
            ret.append(word)
    return ret


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


class Comment(ParsingNode):
    """
    Object to represent a full line comment in an MCNP problem.

    This represents only ``C`` style comments and not ``$`` style comments.

    :param input_lines: the lines read straight from the input file.
    :type input_lines: list
    :param input_line_num: The line number in a parent input input where this Comment appeared
    :type input_line_num: int
    """

    def __init__(self, input_lines, input_line_num=0):
        super().__init__(input_lines)
        buff = []
        for line in input_lines:
            fragments = re.split(
                rf"^\s{{0,{BLANK_SPACE_CONTINUE-1}}}C\s", line, flags=re.I
            )
            if len(fragments) > 1:
                comment_line = fragments[1].rstrip()
            else:
                comment_line = ""
            buff.append(comment_line)
        self._lines = buff
        self._cutting = False
        self._input_line_num = input_line_num

    def __str__(self):
        return f"COMMENT: {len(self._lines)} lines"

    def __repr__(self):
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

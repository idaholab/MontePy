# Copyright 2024, Battelle Energy Alliance, LLC All Rights Reserved.
from abc import ABC, abstractmethod
import math
from montepy.errors import *
from montepy.input_parser.block_type import BlockType
from montepy.constants import BLANK_SPACE_CONTINUE, get_max_line_length
from montepy.input_parser.read_parser import ReadParser
from montepy.input_parser.tokens import CellLexer, SurfaceLexer, DataLexer
from montepy.utilities import *
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

    .. versionadded:: 0.2.0
        This was added as part of the parser rework.

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

    @property
    def input_lines(self):
        """The lines of the input read straight from the input file

        :rtype: list
        """
        return self._input_lines

    @property
    def input_text(self):
        return "\n".join(self.input_lines) + "\n"

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


class Card(ParsingNode):  # pragma: no cover
    """
    .. warning::

        .. deprecated:: 0.2.0
            Punch cards are dead. Use :class:`~montepy.input_parser.mcnp_input.Input` instead.

    :raises DeprecatedError: punch cards are dead.
    """

    def __init__(self, *args, **kwargs):
        raise DeprecatedError(
            "This has been deprecated. Use montepy.input_parser.mcnp_input.Input instead"
        )


class Input(ParsingNode):
    """
    Represents a single MCNP "Input" e.g. a single cell definition.

    .. versionadded:: 0.2.0
        This was added as part of the parser rework, and rename.
        This was a replacement for :class:`Card`.

    :param input_lines: the lines read straight from the input file.
    :type input_lines: list
    :param block_type: An enum showing which of three MCNP blocks this was inside of.
    :type block_type: BlockType
    :param input_file: the wrapper for the input file this is read from.
    :type input_file: MCNP_InputFile
    :param lineno: the line number this input started at. 1-indexed.
    :type lineno: int
    """

    SPECIAL_COMMENT_PREFIXES = ["fc", "sc"]
    """Prefixes for special comments like tally comments.
    
    :rtype: list
    """

    def __init__(self, input_lines, block_type, input_file=None, lineno=None):
        super().__init__(input_lines)
        if not isinstance(block_type, BlockType):
            raise TypeError("block_type must be BlockType")
        self._block_type = block_type
        self._input_file = input_file
        self._lineno = lineno
        self._lexer = None

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

    @make_prop_pointer("_input_file")
    def input_file(self):
        """
        The file this input file was read from.

        :rtype: MCNP_InputFile
        """
        pass

    @make_prop_pointer("_lineno")
    def line_number(self):
        """
        The line number this input started on.

        This is 1-indexed.

        :rtype: int
        """
        pass

    def format_for_mcnp_input(self, mcnp_version):
        pass

    def tokenize(self):
        """
        Tokenizes this input as a stream of Tokens.

        This is a generator of Tokens.
        This is context dependent based on :func:`block_type`.

        * In a cell block :class:`~montepy.input_parser.tokens.CellLexer` is used.
        * In a surface block :class:`~montepy.input_parser.tokens.SurfaceLexer` is used.
        * In a data block :class:`~montepy.input_parser.tokens.DataLexer` is used.

        :returns: a generator of tokens.
        :rtype: Token
        """
        if self.block_type == BlockType.CELL:
            lexer = CellLexer()
        elif self.block_type == BlockType.SURFACE:
            lexer = SurfaceLexer()
        else:
            lexer = DataLexer()
        self._lexer = lexer
        # hacky way to capture final new line and remove it after lexing.
        generator = lexer.tokenize(self.input_text)
        token = None
        next_token = None
        try:
            token = next(generator)
            while True:
                if next_token:
                    token = next_token
                next_token = next(generator)
                yield token
        except StopIteration:
            if not token:
                return
            token.value = token.value.rstrip("\n")
            if token.value:
                yield token
        self._lexer = None

    @make_prop_pointer("_lexer")
    def lexer(self):
        """
        The current lexer being used to parse this input.

        If not currently tokenizing this will be None.
        :rtype:MCNP_Lexer
        """
        pass

    @property
    def words(self):  # pragma: no cover
        """
        .. warning::
            .. deprecated:: 0.2.0

            This has been deprecated, and removed.

        :raises DeprecationWarning: use the parser and tokenize workflow instead.
        """
        raise DeprecationWarning(
            "This has been deprecated. Use a parser and tokenize instead"
        )


class Comment(ParsingNode):  # pragma: no cover
    """
    .. warning::
        .. deprecated:: 0.2.0
            This has been replaced by :class:`~montepy.input_parser.syntax_node.CommentNode`.

    :raises DeprecationWarning: Can not be created anymore.
    """

    def __init__(self, *args, **kwargs):
        raise DeprecationWarning(
            "This has been deprecated and replaced by montepy.input_parser.syntax_node.CommentNode."
        )


class ReadInput(Input):
    """
    A input for the read input that reads another input file

    :param input_lines: the lines read straight from the input file.
    :type input_lines: list
    :param block_type: An enum showing which of three MCNP blocks this was inside of.
    :type block_type: BlockType
    :param input_file: the wrapper for the input file this is read from.
    :type input_file: MCNP_InputFile
    :param lineno: the line number this input started at. 1-indexed.
    :type lineno: int
    """

    _parser = ReadParser()

    def __init__(self, input_lines, block_type, input_file=None, lineno=None):
        super().__init__(input_lines, block_type, input_file, lineno)
        if not self.is_read_input(input_lines):
            raise ValueError("Not a valid Read Input")
        parse_result = self._parser.parse(self.tokenize(), self)
        if not parse_result:
            raise ParsingError(self, "", self._parser.log.clear_queue())
        self._tree = parse_result
        self._parameters = self._tree["parameters"]

    @staticmethod
    def is_read_input(input_lines):
        first_non_comment = ""
        for line in input_lines:
            if not is_comment(line):
                first_non_comment = line
                break
        words = first_non_comment.split()
        if len(words) > 0:
            first_word = words[0].lower()
            return first_word == "read"
        # this is a fall through catch that only happens for a blank input
        return False  # pragma: no cover

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


class ReadCard(Card):  # pragma: no cover
    """
    .. warning::

        .. deprecated:: 0.2.0
            Punch cards are dead. Use :class:`~montepy.input_parser.mcnp_input.ReadInput` instead.

    :raises DeprecatedError: punch cards are dead.
    """

    def __init__(self, *args, **kwargs):
        raise DeprecatedError(
            "This has been deprecated. Use montepy.input_parser.mcnp_input.ReadInput instead"
        )


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


def parse_card_shortcuts(*args, **kwargs):  # pragma: no cover
    """
    .. warning::
        .. deprecated:: 0.2.0
            This is no longer necessary and should not be called.

    :raises DeprecationWarning: This is not needed anymore.
    """
    raise DeprecationWarning(
        "This is deprecated and unnecessary. This will be automatically handled by montepy.input_parser.parser_base.MCNP_Parser."
    )

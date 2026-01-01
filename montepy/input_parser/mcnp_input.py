# Copyright 2024, Battelle Energy Alliance, LLC All Rights Reserved.
from abc import ABC, abstractmethod
import math
import re

from montepy.exceptions import *
from montepy.utilities import *
from montepy.input_parser.block_type import BlockType
from montepy.constants import BLANK_SPACE_CONTINUE, get_max_line_length
from montepy.input_parser.read_parser import ReadParser
from montepy.input_parser.tokens import CellLexer, SurfaceLexer, DataLexer
from montepy.utilities import *
import montepy.types as ty


class Jump:
    """Class to represent a default entry represented by a "jump".

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

    def __format__(self, spec):
        return format(str(self), spec)

    def __bool__(self):
        raise TypeError("Jump doesn't have a truthiness or falsiness")

    def __eq__(self, other):
        return type(self) == type(other)

    def lower(self):
        """Hop.

        Returns
        -------
        str
        """
        return "j"

    def title(self):
        """Skip.

        Returns
        -------
        str
        """
        return "Jump"

    def upper(self):
        """Jump.

        Returns
        -------
        str
        """
        return "J"


class ParsingNode(ABC):
    """Object to represent a single coherent MCNP input, such as an input.

    Parameters
    ----------
    input_lines : list
        the lines read straight from the input file.
    """

    @args_checked
    def __init__(self, input_lines: list[str]):
        self._input_lines = input_lines

    @property
    def input_lines(self):
        """The lines of the input read straight from the input file

        Returns
        -------
        list
        """
        return self._input_lines

    @property
    def input_text(self):
        return "\n".join(self.input_lines) + "\n"

    @abstractmethod
    def format_for_mcnp_input(self, mcnp_version):
        """Creates a string representation of this input that can be
        written to file.

        Parameters
        ----------
        mcnp_version : tuple
            The tuple for the MCNP version that must be exported to.

        Returns
        -------
        list
            a list of strings for the lines that this input will occupy.
        """
        pass


class Input(ParsingNode):
    """Represents a single MCNP "Input" e.g. a single cell definition.

    Parameters
    ----------
    input_lines : list
        the lines read straight from the input file.
    block_type : BlockType
        An enum showing which of three MCNP blocks this was inside of.
    input_file : MCNP_InputFile
        the wrapper for the input file this is read from.
    lineno : int
        the line number this input started at. 1-indexed.
    """

    SPECIAL_COMMENT_PREFIXES = ["fc", "sc"]
    """Prefixes for special comments like tally comments.

    Returns
    -------
    list
    """

    @args_checked
    def __init__(
        self, input_lines, block_type: BlockType, input_file=None, lineno=None
    ):
        super().__init__(input_lines)
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
        """Enum representing which block of the MCNP input this came from.

        Returns
        -------
        BlockType
        """
        return self._block_type

    @make_prop_pointer("_input_file")
    def input_file(self):
        """The file this input file was read from.

        Returns
        -------
        MCNP_InputFile
        """
        pass

    @make_prop_pointer("_lineno")
    def line_number(self):
        """The line number this input started on.

        This is 1-indexed.

        Returns
        -------
        int
        """
        pass

    def format_for_mcnp_input(self, mcnp_version):
        pass

    def tokenize(self):
        """Tokenizes this input as a stream of Tokens.

        This is a generator of Tokens.
        This is context dependent based on :func:`block_type`.

        * In a cell block :class:`~montepy.input_parser.tokens.CellLexer` is used.
        * In a surface block :class:`~montepy.input_parser.tokens.SurfaceLexer` is used.
        * In a data block :class:`~montepy.input_parser.tokens.DataLexer` is used.

        Returns
        -------
        Token
            a generator of tokens.
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
        # if closed upstream
        except GeneratorExit:
            generator.close()
        self._lexer = None

    @make_prop_pointer("_lexer")
    def lexer(self):
        """The current lexer being used to parse this input.

        If not currently tokenizing this will be None.

        Returns
        -------
        MCNP_Lexer
        """
        pass

    def search(self, search: str | re.Pattern) -> bool:
        """
        Searches this input for the given string, or compiled regular expression.

        Parameters
        ----------
        search : str | re.Pattern
            The pattern to search for.

        Returns
        -------
        bool
            Whether this
        """
        searcher = lambda line: search in line
        if isinstance(search, re.Pattern):
            searcher = lambda line: (search.match(line)) is not None
        for line in self.input_lines:
            if searcher(line):
                return True
        return False


class ReadInput(Input):
    """A input for the read input that reads another input file

    Parameters
    ----------
    input_lines : list
        the lines read straight from the input file.
    block_type : BlockType
        An enum showing which of three MCNP blocks this was inside of.
    input_file : MCNP_InputFile
        the wrapper for the input file this is read from.
    lineno : int
        the line number this input started at. 1-indexed.
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
        """The relative path to the filename specified in this read input.

        Returns
        -------
        str
        """
        return self._parameters["file"]["data"].value

    def __str__(self):
        return f"READ INPUT: Block_Type: {self.block_type}"

    def __repr__(self):
        return (
            f"READ INPUT: {self._block_type}: {self.input_lines} File: {self.file_name}"
        )


class Message(ParsingNode):
    """Object to represent an MCNP message.

    These are blocks at the beginning of an input that are printed in the output.

    Parameters
    ----------
    input_lines : list
        the lines read straight from the input file.
    lines : list
        the strings of each line in the message block
    """

    @args_checked
    def __init__(self, input_lines, lines: list[str]):
        super().__init__(input_lines)
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
        """The lines of input for the message block.

        Each entry is a string of that line in the message block

        Returns
        -------
        list
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
    """Object to represent the title for an MCNP problem

    Parameters
    ----------
    input_lines : list
        the lines read straight from the input file.
    title : str
        The string for the title of the problem.
    """

    @args_checked
    def __init__(self, input_lines, title: str):
        """
        Parameters
        ----------
        input_lines : list
            the lines read straight from the input file.
        title : str
            The string for the title of the problem.
        """
        super().__init__(input_lines)
        self._title = title.rstrip()

    @property
    def title(self):
        """The string of the title set for this problem

        Returns
        -------
        str
        """
        return self._title

    def __str__(self):
        return f"TITLE: {self._title}"

    def format_for_mcnp_input(self, mcnp_version):
        line_length = 0
        line_length = get_max_line_length(mcnp_version)
        return [self.title[0 : line_length - 1]]

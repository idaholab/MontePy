from abc import ABC, abstractmethod
from collections import deque
from enum import auto, Enum
import itertools
from mcnpy.input_parser.mcnp_input import SyntaxNode
from mcnpy.utilities import fortran_float


class ParseStatus(Enum):
    COMPLETE = auto()
    INCOMPLETE = auto()
    FAILED = auto()


def tokenize(input):
    _TOKEN_ORDER = [DataToken, SeperatorToken, CommentToken]
    class_iter = itertools.cycle(_TOKEN_ORDER)
    current_token = None
    letters = deque(input)
    while True:
        try:
            char = letters.popleft()
        except StopIteration:
            break
        if current_token is None:
            current_token = next(class_iter)()
        status, overflow = current_token.matches(char)
        if status in {ParseStatus.COMPLETE, ParseStatus.FAILED}:
            if status == ParseStatus.COMPLETE:
                yield current_token
            current_token = next(class_iter)()
            letters.appendleft(overflow)


class Token(SyntaxNode):
    """
    Class to represent a syntax Token

    """

    def __init__(self):
        self._original_input = None
        self._value = None
        self._buffer = ""

    @property
    def original_input(self):
        return self._original_input

    @property
    def value(self):
        return self._value

    @abstractmethod
    def format(self):
        pass

    @abstractmethod
    def parse(self):
        pass

    @abstractmethod
    def matches(self, char):
        pass

    def format_for_mcnp_input(self, mcnp_version):
        pass


class DataToken(Token):
    _ALLOWED_CHAR = set()
    _ALLOWED_SECOND_CHAR = {":"}
    _TERMINATORS = {" ", "\n"}

    def format():
        pass

    def parse(self):
        pass

    def matches(self, char):
        self._buffer += char
        if char.isalnum() or char in self._ALLOWED_CHAR:
            return (ParseStatus.INCOMPLETE, "")
        elif len(self._buffer) > 0 and char in self._ALLOWED_SECOND_CHAR:
            return (ParseStatus.INCOMPLETE, "")
        elif char.isspace() or char in self._TERMINATORS:
            self._original_input = self._buffer[:-1]
            del self._buffer
            return (ParseStatus.COMPLETE, char)
        else:
            return (ParseStatus.FAILED, self._buffer)


class IdentifierToken(DataToken):
    """
    Class to represent a Identifier Token.

    Object identifiers (an object number).
    """

    pass


class LiteralToken(DataToken):
    """
    Class to represent a literal token providing data.
    """

    def parse(self):
        self._value = fortran_float(self.original_input)

    def matches(self):
        try:
            self.parse()
            return True
        except ValueError:
            return False


class SeperatorToken(Token):
    pass


class CommentToken(Token):
    """
    Class to represent a token in a comment.
    """

    pass

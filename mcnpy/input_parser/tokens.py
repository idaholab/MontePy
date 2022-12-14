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
    _TOKEN_ORDER = [CommentToken, DataToken, SpaceToken, SeperatorToken]
    class_iter = iter(_TOKEN_ORDER)
    current_token = None
    letters = deque(input)
    while True:
        try:
            char = letters.popleft()
        except IndexError:
            break
        if current_token is None:
            current_token = next(class_iter)()
        status, overflow = current_token.matches(char)
        if status in {ParseStatus.COMPLETE, ParseStatus.FAILED}:
            if status == ParseStatus.COMPLETE:
                class_iter = iter(_TOKEN_ORDER)
                yield current_token
            current_token = next(class_iter)()
            if len(overflow) > 0:
                for char in overflow[::-1]:
                    letters.appendleft(char)


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
    def parse(self, validator=None):
        pass

    @abstractmethod
    def matches(self, char):
        pass

    def format_for_mcnp_input(self, mcnp_version):
        pass

    def print_nodes(self):
        return f"T: {self.original_input}"


class DataToken(Token):
    _ALLOWED_CHAR = {"-", "."}
    _ALLOWED_SECOND_CHAR = {":"}
    _TERMINATORS = {"(", ")", " ", "\n"}

    def __init__(self, token=None):
        super().__init__()
        if token:
            self._original_input = token.original_input

    def format():
        pass

    def parse(self, validator=None):
        pass

    def matches(self, char):
        self._buffer += char
        if char.isalnum() or char in self._ALLOWED_CHAR:
            return (ParseStatus.INCOMPLETE, "")
        elif len(self._buffer) > 0 and char in self._ALLOWED_SECOND_CHAR:
            return (ParseStatus.INCOMPLETE, "")
        elif len(self._buffer) > 1 and (char.isspace() or char in self._TERMINATORS):
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

    def parse(self, validator=None):
        try:
            self._value = int(self.original_input)
            if validator:
                assert validator(self.value)
            return True
        except (ValueError, AssertionError) as e:
            return False


class LiteralToken(DataToken):
    """
    Class to represent a literal token providing data.
    """

    def parse(self, validator=None):
        try:
            self._value = fortran_float(self.original_input)
            if validator:
                assert validator(self.value)
            return True
        except (ValueError, AssertionError) as e:
            return False

    def matches(self):
        try:
            self.parse()
            return True
        except ValueError:
            return False


class SpaceToken(Token):
    def parse(self, validator=None):
        self._value = self.original_input
        return True

    def format(self):
        pass

    def matches(self, char):
        self._buffer += char

        if char.isspace():
            return (ParseStatus.INCOMPLETE, "")
        else:
            if self._buffer[:-1].isspace():
                self._original_input = self._buffer[:-1]
                del self._buffer
                return (ParseStatus.COMPLETE, char)
            else:
                return (ParseStatus.FAILED, self._buffer)


class SeperatorToken(Token):
    _SEPERATOR_CHAR = {"(", ":", ")"}

    def parse(self, validator=None):
        self._value = self.original_input
        return True

    def format(self):
        pass

    def matches(self, char):
        self._buffer += char

        def flush_complete(char):
            self._original_input = self._buffer[:-1]
            del self._buffer
            return (ParseStatus.COMPLETE, char)

        if char in self._SEPERATOR_CHAR:
            self._original_input = self._buffer
            return (ParseStatus.COMPLETE, "")
        else:
            return (ParseStatus.FAILED, self._buffer)


class CommentToken(Token):
    """
    Class to represent a token in a comment.
    """

    _COMMENT_STARTER = {"$", "c ", "c\n", "c\t"}
    _LINE_TERMINATOR = "\n"

    def __init__(self):
        super().__init__()
        self._started = False

    def parse(self, validator=None):
        return True

    def format(self):
        pass

    def matches(self, char):
        self._buffer += char
        if not self._started:
            if self._buffer.lower() in self._COMMENT_STARTER:
                self._started = True
                if self._buffer.lower() == "c\n":
                    self._original_input = self._buffer[:]
                    del self._buffer
                    return (ParseStatus.COMPLETE, "")
                return (ParseStatus.INCOMPLETE, "")
            elif (self._buffer + " ").lower() in self._COMMENT_STARTER:
                return (ParseStatus.INCOMPLETE, "")
            else:
                return (ParseStatus.FAILED, self._buffer)
        else:
            if char == self._LINE_TERMINATOR:
                # actually consumes new line
                self._original_input = self._buffer[:]
                del self._buffer
                return (ParseStatus.COMPLETE, "")
            else:
                return (ParseStatus.INCOMPLETE, "")

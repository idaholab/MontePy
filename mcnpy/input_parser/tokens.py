from mcnpy.input_parser.mcnp_input import SyntaxNode
from mcnpy.utilities import fortran_float


class Token(SyntaxNode):
    """
    Class to represent a syntax Token

    :param chunk: the chunk that this token represents
    :type chunk: str
    """

    def __init__(self, chunk):
        self._original_input = chunk
        self._value = None

    @property
    def original_input(self):
        pass

    @property
    def value(self):
        pass

    @abstractmethod
    def format(self):
        pass

    @abstractmethod
    def parse(self):
        pass

    @abstractmethod
    def matches(self):
        pass


class IdentifierToken(Token):
    """
    Class to represent a Identifier Token.

    Object identifiers (an object number).
    """

    pass


class LiteralToken(Token):
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

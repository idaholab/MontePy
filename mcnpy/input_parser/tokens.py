from mcnpy.input_parser.mcnp_input import SyntaxNode


class Token(SyntaxNode):
    """
    Class to represent a syntax Token
    """

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

    pass


class CommentToken(Token):
    """
    Class to represent a token in a comment.
    """

    pass

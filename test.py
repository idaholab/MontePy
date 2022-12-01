import mcnpy
from mcnpy.input_parser.node_parser import NodeParser, TokenParser
from mcnpy.input_parser.tokens import (
    CommentToken,
    DataToken,
    IdentifierToken,
    LiteralToken,
    SeperatorToken,
    Token,
    tokenize,
)

Input = mcnpy.input_parser.mcnp_input.Input

input = Input(
    [
        "5 10 -0.5",
        "C this is a comment",
    ],
    mcnpy.input_parser.block_type.BlockType.CELL,
)
cell_parser = NodeParser(
    [1],
    children=[
        TokenParser(IdentifierToken, "_old_number"),
        TokenParser(SeperatorToken),
        TokenParser(IdentifierToken, "_material"),
        TokenParser(SeperatorToken),
        NodeParser({0, 1}, [TokenParser(LiteralToken, "_density")]),
    ],
)
cell_parser.parse(input)

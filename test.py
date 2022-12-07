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
        "5  $foo 10 -0.5",
        "10 -0.5",
        # "C this is a comment",
    ],
    mcnpy.input_parser.block_type.BlockType.CELL,
)
cell_parser = NodeParser(
    [1],
    "cell",
    children=[
        NodeParser(
            [1],
            "cell number",
            children=[
                TokenParser(IdentifierToken, map_to="_old_number"),
                TokenParser(SeperatorToken),
            ],
        ),
        NodeParser(
            [1],
            "material",
            children=[
                TokenParser(IdentifierToken, map_to="_material"),
                TokenParser(SeperatorToken),
            ],
        ),
        NodeParser(
            {0, 1},
            "density",
            children=[
                TokenParser(LiteralToken, map_to="_density"),
                TokenParser(SeperatorToken),
            ],
        ),
    ],
)
cell_node = cell_parser.parse(input)
print(cell_node.print_nodes())

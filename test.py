import itertools
import mcnpy
from mcnpy.input_parser.node_parser import NodeParser, TokenParser
from mcnpy.input_parser.tokens import (
    CommentToken,
    DataToken,
    IdentifierToken,
    LiteralToken,
    SpaceToken,
    SeperatorToken,
    Token,
    tokenize,
)

Input = mcnpy.input_parser.mcnp_input.Input
"""
input = Input(
    [
        "5  $foo 10 -0.5",
        "10 -0.5",
        "C this is a comment",
    ],
    mcnpy.input_parser.block_type.BlockType.CELL,
)
"""
input = Input(
    [
        "5 4",
    ],
    mcnpy.input_parser.block_type.BlockType.CELL,
)
positive = lambda x: x > 0
MAX_NUM = 1e9


class MinIter:
    def __init__(self, min_val):
        self._min = min_val

    def __contains__(self, val):
        return val >= self._min


class SurfaceParser(NodeParser):
    def __init__(self):
        super().__init__(
            MinIter(1),
            "surface geometry",
            allow_implicit_space=False,
            branches=[
                TokenParser(
                    IdentifierToken,
                    allowed_values=itertools.chain(
                        range(1, int(MAX_NUM)), range(-1, int(MAX_NUM), -1)
                    ),
                )
            ],
        )
        self._branches += [
            NodeParser(
                MinIter(1),
                "surface parentheses",
                allow_implicit_space=False,
                children=[
                    TokenParser(SeperatorToken, allowed_values="("),
                    SurfaceParser,
                    TokenParser(SeperatorToken, allowed_values=")"),
                ],
            ),
            NodeParser(
                MinIter(1),
                "Surface and",
                allow_implicit_space=False,
                children=[SurfaceParser, TokenParser(SpaceToken), SurfaceParser],
            ),
        ]


SurfaceParser()
value = SurfaceParser().parse(input)
print(value.parse_results.print_nodes())
cell_parser = NodeParser(
    [1],
    "cell",
    children=[
        NodeParser(
            [1],
            "cell number",
            children=[
                TokenParser(IdentifierToken, map_to="_old_number", validator=positive),
            ],
        ),
        NodeParser(
            [1],
            "material info",
            pass_through=True,
            branches=[
                NodeParser(
                    [1],
                    "material density",
                    children=[
                        NodeParser(
                            [1],
                            "material",
                            children=[
                                TokenParser(
                                    IdentifierToken,
                                    allowed_values=range(1, int(1e9)),
                                    validator=positive,
                                    map_to="_material",
                                ),
                            ],
                        ),
                        NodeParser(
                            [1],
                            "density",
                            children=[
                                TokenParser(LiteralToken, map_to="_density"),
                            ],
                        ),
                    ],
                ),
                NodeParser(
                    [1],
                    "void material",
                    children=[
                        TokenParser(
                            IdentifierToken, allowed_values=[0], map_to="_material"
                        ),
                    ],
                ),
            ],
        ),
    ],
)
"""
cell_node = cell_parser.parse(input)
print(cell_node.parse_results.print_nodes())
""
input = Input(
    [
        "5  $foo 10 -0.5",
        "0 ",
        "C this is a comment",
    ],
    mcnpy.input_parser.block_type.BlockType.CELL,
)
cell_parser.clear()
cell_node = cell_parser.parse(input)
print(cell_node.parse_results.print_nodes())
"""

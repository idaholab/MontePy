from abc import ABC, abstractmethod
from itertools import count


class NodeParser(ABC):
    def __init__(
        self,
        allowed_occurences=count(0),
        children=[],
        unordered_children=set(),
        branches=[],
        map_to=None,
    ):
        pass


class TokeParser(NodeParser):
    def __init__(self, token_class, map_to=None, allowed_values=None):
        pass


genericKeyValueParser = NodeParser(
    {1},
    children=[
        TokenParser(IdentifierToken, "_key"),
        TokeParser(SeperaterToken, allowed_values={"=", " "}),
        NodeParser(
            count(1),
            unordered_children={
                TokenParser(LiteralToken),
                TokenParser(SeperatorToken),
                TokenParser(IdentifierToken),
            },
            map_to="_value",
        ),
    ],
)

# TODO Delete prototype
cell_parser = NodeParser(
    [1],
    children=[
        TokenParser(IdentifierToken, "_old_number"),
        TokenParser(IdentifierToken, "_material"),
        NodeParser({0, 1}, TokenParser(LiteralToken, "_density")),
        SurfacePaser(),
        NodeParser(
            count(0),
            unorderd_children={
                genericKeyValueParser,
                VolumeCellParser,
                ImportanceParser,
                FillParser,
                UniverseParser,
            },
        ),
    ],
)

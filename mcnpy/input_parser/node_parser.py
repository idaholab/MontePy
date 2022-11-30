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
        self._allowed_occur = allowed_occurences
        if map_to is not None:
            if not isinstance(map_to, str):
                raise TypeError(f"Map_to must be a str {map_to} given")
        self._map_to = map_to
        lengths = [len(children), len(unordered_children), len(branches)]
        # if two arguments are non-zero length
        if sum(lengths) != max(lengths):
            raise ValueError(
                "Can only specify one of: children, unordered_children, or branches"
            )
        self._children = children
        self._unodered = unordered_children
        self._branches = branches

    def parse(self, input):
        input_iter = iter(input)
        if children:
            for child in children:
                # todo check that stuff matches and what not
                child.parse(input_iter)


class TokeParser(NodeParser):
    def __init__(self, token_class, map_to=None, allowed_values=None):
        if not issubclass(token_class, Token):
            raise TypeError("Token_class must be a subclass of Token")
        self._token_class = token_class
        if not isinstance(map_to, (str, type(None))):
            raise TypeError("Map_to must be a str")
        self._map_to = map_to
        self._allowed_values = allowed_values

    def parse():
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

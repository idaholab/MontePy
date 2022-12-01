from abc import ABC, abstractmethod
from itertools import count
from mcnpy.input_parser.tokens import (
    CommentToken,
    DataToken,
    IdentifierToken,
    LiteralToken,
    SeperatorToken,
    Token,
    tokenize,
)


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
        if self._children:
            self._child_iterator = iter(self._children)
            self._current_child = next(self._child_iterator)
        self._unodered = unordered_children
        self._branches = branches
        self._matches = 0
        self._token_buffer = []

    @property
    def children(self):
        return self._children

    def parse(self, input=None, token=None):
        if input:
            for token in tokenize(input):
                print(token)
                self._parse_token(token)
        elif token:
            self._parse_token(token)

    def _parse_token(self, token):
        self._token_buffer.append(token)
        if self.children:
            while True:
                status = self._current_child.parse(token=token)
                if status == True:
                    if isinstance(self._current_child, NodeParser):
                        if self._current_child.is_allowed_number_matches():
                            pass
                # TODO check that matches is right
                print(status)
                break

    @property
    def matches(self):
        return self._matches

    def is_allowed_number_matches(self):
        return self.matches in self._allowed_occur


class TokenParser(NodeParser):
    def __init__(self, token_class, map_to=None, allowed_values=None):
        if not issubclass(token_class, Token):
            raise TypeError("Token_class must be a subclass of Token")
        self._token_class = token_class
        if not isinstance(map_to, (str, type(None))):
            raise TypeError("Map_to must be a str")
        self._map_to = map_to
        self._allowed_values = allowed_values

    def parse(self, token):
        if isinstance(token, self._token_class) or issubclass(
            self._token_class, type(token)
        ):
            if isinstance(token, self._token_class):
                test_token = token
            else:
                test_token = self._token_class(token)
            if not test_token.parse():
                return False
            if self._allowed_values:
                if self._token_class == SeperatorToken:
                    if not self._allowed_values and not self.value.isspace():
                        return False
                if token.value not in self._allowed_values:
                    return False
            if self._map_to:
                setattr(self, self._map_to, token.value)
            return True
        else:
            return False


"""
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
"""

from abc import ABC, abstractmethod
from itertools import count
from mcnpy.input_parser.semantic_node import SemanticNode, IdentifierNode, SemanticLeaf
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
        name="",
        node_class = SemanticNode,
        children=[],
        unordered_children=set(),
        branches=[],
        map_to=None,
    ):
        self._allowed_occur = allowed_occurences
        self._name = name
        self._node_class = node_class
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
            self._loop_increment_child()
        self._unodered = unordered_children
        self._branches = branches
        self._matches = 0
        self._token_buffer = []
        self._nodes = self._node_class(self.name)

    def _increment_child(self):
        self._current_index, self._current_child = next(self._child_iterator)

    def _loop_increment_child(self):
        self._child_iterator = enumerate(self._children)
        self._increment_child()

    @property
    def name(self):
        return self._name

    def __str__(self):
        return f"NodeParser: {self._name}"

    @property
    def children(self):
        return self._children

    def parse(self, input=None, token=None):
        if input:
            for token in tokenize(input):
                self._parse_token(token)
        elif token:
            return self._parse_token(token)

    def _parse_token(self, token):
        self._token_buffer.append(token)
        if self.children:
            valid_match = False
            while True:
                status = self._current_child.parse(token=token)
                if status == True:
                    if not isinstance(self._current_child, TokenParser):
                        if self._current_child.is_allowed_number_matches():
                            valid_match = True
                            break
                        else:
                            continue
                    else:
                        valid_match = True
                        break
                else:
                    if isinstance(self._current_child, TokenParser) and isinstance(
                        token, CommentToken
                    ):
                        comment_parser = TokenParser(CommentToken)
                        if comment_parser.parse(token):
                            self._nodes.append(comment_parser)
                    break

            if valid_match:
                self._nodes.append(self._current_child)
                try:
                    self._increment_child()
                except StopIteration:
                    self._loop_increment_child()
                    self._matches += 1
                    self._token_buffer = []
                return True
            return False

    @property
    def matches(self):
        return self._matches

    def is_allowed_number_matches(self):
        return self.matches in self._allowed_occur

    def print_nodes(self):
        ret = []
        for node in self._nodes:
            ret.append(node.print_nodes())
        return f"N: {self.name} ({', '.join(ret)})"


class TokenParser(NodeParser):
    def __init__(self, token_class, node_class = SemanticLeaf, map_to=None, allowed_values=None):
        self._name = ""
        self._node_class = node_class
        if not issubclass(token_class, Token):
            raise TypeError("Token_class must be a subclass of Token")
        self._token_class = token_class
        if not isinstance(map_to, (str, type(None))):
            raise TypeError("Map_to must be a str")
        self._map_to = map_to
        self._allowed_values = allowed_values
        self._nodes = self._node_class()

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
            self._nodes.append( test_token)
            if self._map_to:
                setattr(self, self._map_to, token.value)
            return True
        else:
            return False

    def __str__(self):
        return f"TokenParser {self._token_class}"

    def print_nodes(self):
        return f"T: {self._nodes.original_input}"


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

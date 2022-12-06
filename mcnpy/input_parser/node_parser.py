from abc import ABC, abstractmethod
from collections import namedtuple
from itertools import count
from mcnpy.input_parser.semantic_node import SemanticNode, IdentifierNode
from mcnpy.input_parser.tokens import (
    CommentToken,
    DataToken,
    IdentifierToken,
    LiteralToken,
    SeperatorToken,
    Token,
    tokenize,
)

ParseResult = namedtuple(
    "ParseResult",
    ["parsed", "complete", "parse_results", "failed_tokens"],
    defaults=[False, None, None],
)


class NodeParser(ABC):
    def __init__(
        self,
        allowed_occurences=count(0),
        name="",
        node_class=SemanticNode,
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
        self._node = self._node_class(self.name)

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
                result = self._parse_token(token)
                if not result.parsed:
                    print("AAAHHHH")
                    print(result)
            print(token, result)
            if result.complete:
                return self._node
        elif token:
            return self._parse_token(token)

    def _parse_token(self, token):
        self._token_buffer.append(token)
        if self.children:
            valid_match = False
            print()
            print(self.name, token, token.original_input)
            parse_res = self._current_child.parse(token=token)
            print(f"Parent: {self.name}", parse_res)
            if parse_res.parsed == True:
                valid_match = True
            else:
                # TODO break out
                if isinstance(self._current_child, TokenParser) and isinstance(
                    token, CommentToken
                ):
                    comment_parser = TokenParser(CommentToken)
                    if comment_parser.parse(token):
                        self._node.append(comment_parser)
                        return ParseResult(True, False)

            if valid_match:
                print(self.name, self._matches)
                print(self.is_allowed_number_matches())
                if parse_res.complete:
                    if parse_res.parse_results:
                        self._node.append(parse_res.parse_results)
                    try:
                        print(f"incremented {self.name}")
                        self._increment_child()
                        return ParseResult(True, False)
                    except StopIteration:
                        return self._flush_complete_node()
                else:
                    return ParseResult(True, False)
            elif self.is_allowed_number_matches():
                return ParseResult(True, True, None)
            else:
                print("invalid match", self.name)
                return ParseResult(False, False, failed_tokens=self._token_buffer)

    def _flush_complete_node(self):
        self._loop_increment_child()
        self._matches += 1
        new_node = self._node
        self._node = self._node_class(self.name)
        buffer = self._token_buffer
        self._token_buffer = []
        if self.is_allowed_number_matches():
            return ParseResult(True, True, new_node)
        else:
            print(self.name)
            return ParseResult(False, failed_tokens=buffer)

    @property
    def matches(self):
        return self._matches

    def is_allowed_number_matches(self):
        return self.matches in self._allowed_occur


class TokenParser(NodeParser):
    def __init__(self, token_class, map_to=None, allowed_values=None):
        self._name = ""
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
                return ParseResult(
                    False,
                )
            if self._allowed_values:
                if self._token_class == SeperatorToken:
                    if not self._allowed_values and not self.value.isspace():
                        return ParseResult(
                            False,
                        )
                if token.value not in self._allowed_values:
                    return ParseResult(
                        False,
                    )
            if self._map_to:
                setattr(self, self._map_to, token.value)
            return ParseResult(True, True, test_token)
        else:
            return ParseResult(
                False,
            )

    def __str__(self):
        return f"TokenParser {self._token_class}"

    def print_node(self):
        return f"T: {self._node.original_input}"

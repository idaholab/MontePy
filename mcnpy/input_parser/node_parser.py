from abc import ABC, abstractmethod
from collections import deque, namedtuple
from itertools import count
from mcnpy.input_parser.semantic_node import SemanticNode, IdentifierNode
from mcnpy.input_parser.tokens import (
    CommentToken,
    DataToken,
    IdentifierToken,
    LiteralToken,
    SeperatorToken,
    SpaceToken,
    Token,
    tokenize,
)

ParseResult = namedtuple(
    "ParseResult",
    ["parsed", "complete", "could_complete", "parse_results", "failed_tokens"],
    defaults=[False, False, None, None],
)

# TODO implement clear function


class NodeParser(ABC):
    """
    A class to parse a node in ultimate semantic tree.

    The parser itself forms a tree structure. All objects passed describing the
    tree structure should be a NodeParser class.

    :param allowed_occurences: a container that supports "in" of the allowed number of occurences
    :type allowed_occurences: iterator
    :param name: name of this node, and the semantic node it parses
    :type name: str
    :param node_class: the class of the SemanticNode this will generate
    :type node_class: class
    :param children: A list of the children parsers of this node. They must match in order
    :type children: list
    :param unordered_children: children nodes that can match in any order or not at all. List order establishes match
                                priority
    :type unordered_children: list
    :param branches: Mutually exclusive possible matching nodes. Only one branch may match. List order is match order.
    :type branches: list
    """

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
        if self._branches:
            self._loop_increment_branch()
        self._matches = 0
        self._token_buffer = []
        self._node = self._node_class(self.name)
        self._end_of_tape = False

    def _increment_child(self):
        """
        Moves the child iterator ahead by one.
        """
        self._current_index, self._current_child = next(self._child_iterator)

    def _loop_increment_child(self):
        """
        Moves the child iterator back to the beginning.
        """
        self._child_iterator = enumerate(self._children)
        self._increment_child()

    def _increment_branch(self):
        self._current_index, self._current_branch = next(self._branch_iterator)

    def _loop_increment_branch(self):
        self._branch_iterator = enumerate(self._branches)
        self._increment_branch()

    @property
    def name(self):
        """
        This node's name.
        """
        return self._name

    def __str__(self):
        return f"NodeParser: {self._name}"

    @property
    def children(self):
        return self._children

    @property
    def branches(self):
        return self._branches

    def parse(self, input=None, token=None):
        """
        Parses the specified information.

        :param input: the input object to parse by the root node.
        :type input: Input
        :param token: the token to parse from the Input iterator.
        :type token: Token
        :returns: a ParseResult describing how it went.
        :rtype: ParseResult
        """
        if input:
            tokens = deque(tokenize(input))
            while True:
                # get next token
                try:
                    token = tokens.popleft()
                except IndexError:
                    break
                result = self._parse_token(token)
                # save failed tokens
                if not result.parsed:
                    for token in result.failed_tokens[::-1]:
                        tokens.appendleft(token)
            if result.complete or result.could_complete:
                return ParseResult(True, True, parse_results=self._node)
        elif token:
            return self._parse_token(token)

    def _parse_token(self, token):
        """
        Parses an individual token.
        """
        self._token_buffer.append(token)
        if self.children:
            return self._parse_token_with_children(token)
        elif self.branches:
            return self._parse_token_with_branches(token)
        else:
            return ParseResult(False, False, failed_tokens=self._token_buffer)

    def _parse_token_with_children(self, token):
        # get rid of implicit tokens (spaces, and comments) first
        if isinstance(token, (CommentToken, SpaceToken)):
            if isinstance(self._current_child, TokenParser):
                return self._handle_implicit_tokens(token)
            else:
                parse_res = self._current_child.parse(token=token)
                if not parse_res.parsed:
                    last_leaf_parent = self._node.get_last_leaf_parent()
                    if last_leaf_parent:
                        last_leaf_parent.append(token)
                        return ParseResult(
                            True, False, True, parse_results=last_leaf_parent
                        )
                    else:
                        return ParseResult(False, False, failed_tokens=[token])
                else:
                    return parse_res
        elif self._end_of_tape:
            raise ValueError("end of tape")
        parse_res = self._current_child.parse(token=token)
        if parse_res.parsed == True:
            if parse_res.complete:
                if parse_res.parse_results:
                    self._node.append(parse_res.parse_results)
                try:
                    self._increment_child()
                    return ParseResult(True, False)
                except StopIteration:
                    return self._flush_complete_node()
            else:
                return ParseResult(True, False, parse_res.could_complete)
        elif self.is_allowed_number_matches():
            return ParseResult(True, True, parse_results=None)

    def _parse_token_with_branches(self, token):
        """
        Parses the given token with the branches given.
        """
        if isinstance(token, (CommentToken, SpaceToken)):
            if isinstance(self._current_branch, TokenParser):
                return self._handle_implicit_tokens(token)
            else:
                parse_res = self._current_branch.parse(token=token)
                if not parse_res.parsed:
                    last_leaf_parent = self._node.get_last_leaf_parent()
                    if last_leaf_parent:
                        last_leaf_parent.append(token)
                        return ParseResult(
                            True, False, True, parse_results=last_leaf_parent
                        )
                    else:
                        return ParseResult(False, False, failed_tokens=[token])
                else:
                    return parse_res
        parse_res = self._current_branch.parse(token=token)
        if parse_res.parsed == True:
            if parse_res.complete:
                self._matches += 1
                if self.is_allowed_number_matches():
                    return parse_res
                else:
                    old_tokens = self._token_buffer
                    self._token_buffer = []
                    return ParseResult(False, False, failed_tokens=old_tokens)
            return parse_res
        else:
            try:
                self._increment_branch()
            except StopIteration:
                pass
                # self._loop_increment_branch()
            old_tokens = self._token_buffer
            self._token_buffer = []
            return ParseResult(False, False, failed_tokens=[old_tokens])

    def _handle_implicit_tokens(self, token):
        """
        Parses the implicit tokens: SpaceToken, and CommentToken
        """
        valid_match = False
        if isinstance(token, CommentToken):
            comment_parser = TokenParser(CommentToken)
            parse_res = comment_parser.parse(token)
            if parse_res.parsed:
                valid_match = True
        if isinstance(token, SpaceToken):
            space_parser = TokenParser(SpaceToken)
            parse_res = space_parser.parse(token)
            if parse_res.parsed:
                valid_match = True
        if valid_match:
            if len(self._node) > 0:
                self._node.append(parse_res.parse_results)
                if self._current_index == len(self._children) - 1:
                    return ParseResult(True, False, True, self._node)
                else:
                    return ParseResult(True, False)
            else:
                return ParseResult(False, False, failed_tokens=[token])

    def _flush_complete_node(self):
        self._matches += 1
        if self.is_allowed_number_matches(self.matches + 1):
            self._loop_increment_child()
        else:
            self._end_of_tape = True
        new_node = self._node
        buffer = self._token_buffer
        self._token_buffer = []
        if self.is_allowed_number_matches():
            return ParseResult(True, True, parse_results=new_node)
        else:
            return ParseResult(False, failed_tokens=buffer)

    @property
    def matches(self):
        return self._matches

    def is_allowed_number_matches(self, matches=None):
        if matches is None:
            matches = self.matches
        return matches in self._allowed_occur


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
                if test_token.value not in self._allowed_values:
                    return ParseResult(
                        False,
                    )
            # if self._map_to:
            #    setattr(self, self._map_to, token.value)
            return ParseResult(True, True, parse_results=test_token)
        else:
            return ParseResult(
                False,
            )

    def __str__(self):
        return f"TokenParser {self._token_class}"

    def print_node(self):
        return f"T: {self._node.original_input}"

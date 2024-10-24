# Copyright 2024, Battelle Energy Alliance, LLC All Rights Reserved.
from abc import ABC, abstractmethod
import collections
import copy
import enum
import math

from montepy import input_parser
from montepy import constants
from montepy.constants import rel_tol, abs_tol
from montepy.errors import *
from montepy.input_parser.shortcuts import Shortcuts
from montepy.geometry_operators import Operator
from montepy.particle import Particle
from montepy.utilities import fortran_float
import re
import warnings


class SyntaxNodeBase(ABC):
    """
    A base class for all syntax nodes.

    A syntax node is any component of the syntax tree
    for a parsed input.

    .. versionadded:: 0.2.0
        This was added with the major parser rework.

    :param name: a name for labeling this node.
    :type name: str
    """

    def __init__(self, name):
        self._name = name
        self._nodes = []

    def append(self, node):
        """
        Append the node to this node.

        :param node: node
        :type node: SyntaxNodeBase, str, None
        """
        self._nodes.append(node)

    @property
    def nodes(self):
        """
        The children nodes of this node.

        :returns: a list of the nodes.
        :rtype: list
        """
        return self._nodes

    def __len__(self):
        return len(self.nodes)

    @property
    def name(self):
        """
        The name for the node.

        :returns: the node's name.
        :rtype: str
        """
        return self._name

    @name.setter
    def name(self, name):
        if not isinstance(name, str):
            raise TypeError("Name must be a string")
        self._name = name

    @abstractmethod
    def format(self):
        """
        Generate a string representing the tree's current state.

        :returns: the MCNP representation of the tree's current state.
        :rtype: str
        """
        pass

    @property
    @abstractmethod
    def comments(self):
        """
        A generator of all comments contained in this tree.

        :returns: the comments in the tree.
        :rtype: Generator
        """
        pass

    def get_trailing_comment(self):
        """
        Get the trailing ``c`` style  comments if any.

        :returns: The trailing comments of this tree.
        :rtype: list
        """
        if len(self.nodes) == 0:
            return
        tail = self.nodes[-1]
        if isinstance(tail, SyntaxNodeBase):
            return tail.get_trailing_comment()

    def _delete_trailing_comment(self):
        """
        Deletes the trailing comment if any.
        """
        if len(self.nodes) == 0:
            return
        tail = self.nodes[-1]
        if isinstance(tail, SyntaxNodeBase):
            tail._delete_trailing_comment()

    def _grab_beginning_comment(self, extra_padding):
        """
        Consumes the provided comment, and moves it to the beginning of this node.

        :param extra_padding: the padding comment to add to the beginning of this padding.
        :type extra_padding: list
        """
        if len(self.nodes) == 0 or extra_padding is None:
            return
        head = self.nodes[0]
        if isinstance(head, SyntaxNodeBase):
            head._grab_beginning_comment(extra_padding)

    def check_for_graveyard_comments(self, has_following_input=False):
        """
        Checks if there is a graveyard comment that is preventing information from being part of the tree, and handles
        them.

        A graveyard comment is one that accidentally suppresses important information in the syntax tree.

        For example::

            imp:n=1 $ grave yard Vol=1

        Should be::

            imp:n=1 $ grave yard
            Vol=1

        These graveyards are handled by appending a new line, and the required number of continue spaces to the
        comment.

        .. versionadded:: 0.4.0

        :param has_following_input: Whether there is another input (cell modifier) after this tree that should be continued.
        :type has_following_input: bool
        :rtype: None
        """
        flatpack = self.flatten()
        if len(flatpack) == 0:
            return
        first = flatpack[0]
        if has_following_input:
            flatpack.append("")
        for second in flatpack[1:]:
            if isinstance(first, ValueNode):
                padding = first.padding
            elif isinstance(first, PaddingNode):
                padding = first
            else:
                padding = None
            if padding:
                if padding.has_graveyard_comment() and not isinstance(
                    second, PaddingNode
                ):
                    padding.append("\n")
                    padding.append(" " * constants.BLANK_SPACE_CONTINUE)
            first = second

    def flatten(self):
        """
        Flattens this tree structure into a list of leaves.

        .. versionadded:: 0.4.0

        :returns: a list of ValueNode and PaddingNode objects from this tree.
        :rtype: list
        """
        ret = []
        for node in self.nodes:
            if node is None:
                continue
            if isinstance(node, (ValueNode, PaddingNode, CommentNode, str)):
                ret.append(node)
            else:
                ret += node.flatten()
        return ret


class SyntaxNode(SyntaxNodeBase):
    """
    A general syntax node for handling inner tree nodes.

    This is a generalized wrapper for a dictionary.
    The order of the dictionary is significant.

    This does behave like a dict for collecting items. e.g.,

    .. code-block:: python

        value = syntax_node["start_pad"]
        if key in syntax_node:
            pass

    .. versionadded:: 0.2.0
        This was added with the major parser rework.

    :param name: a name for labeling this node.
    :type name: str
    :param parse_dict: the dictionary of the syntax tree nodes.
    :type parse_dict: dict
    """

    def __init__(self, name, parse_dict):
        super().__init__(name)
        self._name = name
        self._nodes = parse_dict

    def __getitem__(self, key):
        return self.nodes[key]

    def __contains__(self, key):
        return key in self.nodes

    def get_value(self, key):
        """
        Get a value from the syntax tree.

        :param key: the key for the item to get.
        :type key: str
        :returns: the node in the syntax tree.
        :rtype: SyntaxNodeBase
        :raises KeyError: if key is not in SyntaxNode
        """
        temp = self.nodes[key]
        if isinstance(temp, ValueNode):
            return temp.value
        else:
            raise KeyError(f"{key} is not a value leaf node")

    def __str__(self):
        return f"(Node: {self.name}: {self.nodes})"

    def __repr__(self):
        return str(self)

    def format(self):
        ret = ""
        for node in self.nodes.values():
            if isinstance(node, ValueNode):
                if node.value is not None:
                    ret += node.format()
            else:
                ret += node.format()
        return ret

    @property
    def comments(self):
        for node in self.nodes.values():
            yield from node.comments

    def get_trailing_comment(self):
        node = self._get_trailing_node()
        if node:
            return node.get_trailing_comment()

    def _grab_beginning_comment(self, extra_padding):
        """
        Consumes the provided comment, and moves it to the beginning of this node.

        :param extra_padding: the padding comment to add to the beginning of this padding.
        :type extra_padding: list
        """
        if len(self.nodes) == 0 or extra_padding is None:
            return
        head = next(iter(self.nodes.values()))
        if isinstance(head, SyntaxNodeBase):
            head._grab_beginning_comment(extra_padding)

    def _get_trailing_node(self):
        if len(self.nodes) == 0:
            return
        for node in reversed(self.nodes.values()):
            if node is not None:
                if isinstance(node, ValueNode):
                    if node.value is not None:
                        return node
                elif len(node) > 0:
                    return node

    def _delete_trailing_comment(self):
        node = self._get_trailing_node()
        node._delete_trailing_comment()

    def flatten(self):
        ret = []
        for node in self.nodes.values():
            if isinstance(node, (ValueNode, PaddingNode)):
                ret.append(node)
            else:
                ret += node.flatten()
        return ret


class GeometryTree(SyntaxNodeBase):
    """
    A syntax tree that is a binary tree for representing CSG geometry logic.

    .. versionadded:: 0.2.0
        This was added with the major parser rework.

    .. versionchanged:: 0.4.1
        Added left/right_short_type

    :param name: a name for labeling this node.
    :type name: str
    :param tokens: The nodes that are in the tree.
    :type tokens: dict
    :param op: The string representation of the Operator to use.
    :type op: str
    :param left: the node of the left side of the binary tree.
    :type left: GeometryTree, ValueNode
    :param right: the node of the right side of the binary tree.
    :type right: GeometryTree, ValueNode
    :param left_short_type: The type of Shortcut that right left leaf is involved in.
    :type left_short_type: Shortcuts
    :param right_short_type: The type of Shortcut that the right leaf is involved in.
    :type right_short_type: Shortcuts
    """

    def __init__(
        self,
        name,
        tokens,
        op,
        left,
        right=None,
        left_short_type=None,
        right_short_type=None,
    ):
        super().__init__(name)
        assert all(list(map(lambda v: isinstance(v, SyntaxNodeBase), tokens.values())))
        self._nodes = tokens
        self._operator = Operator(op)
        self._left_side = left
        self._right_side = right
        self._left_short_type = left_short_type
        self._right_short_type = right_short_type

    def __str__(self):
        return (
            f"Geometry: ( {self._left_side}"
            f" {f'Short:{self._left_short_type.value}' if self._left_short_type else ''}"
            f" {self._operator} {self._right_side} "
            f"{f'Short:{self._right_short_type.value}' if self._right_short_type else ''})"
        )

    def __repr__(self):
        return str(self)

    def format(self):
        if self._left_short_type or self._right_short_type:
            return self._format_shortcut()
        ret = ""
        for node in self.nodes.values():
            ret += node.format()
        return ret

    def mark_last_leaf_shortcut(self, short_type):
        """
        Mark the final (rightmost) leaf node in this tree as being a shortcut.

        :param short_type: the type of shortcut that this leaf is.
        :type short_type: Shortcuts
        """
        if self.right is not None:
            node = self.right
            if self._right_short_type:
                return
        else:
            node = self.left
            if self._left_short_type:
                return
        if isinstance(node, type(self)):
            return node.mark_last_leaf_shortcut(short_type)
        if self.right is not None:
            self._right_short_type = short_type
        else:
            self._left_short_type = short_type

    def _flatten_shortcut(self):
        """
        Flattens this tree into a ListNode.

        This will add ShortcutNodes as well.

        :rtype: ListNode
        """

        def add_leaf(list_node, leaf, short_type):
            end = list_node.nodes[-1] if len(list_node) > 0 else None

            def flush_shortcut():
                end.load_nodes(end.nodes)

            def start_shortcut():
                short = ShortcutNode(short_type=short_type)
                # give an interpolate it's old beginning to give it right
                # start value
                if short_type in {
                    Shortcuts.LOG_INTERPOLATE,
                    Shortcuts.INTERPOLATE,
                } and isinstance(end, ShortcutNode):
                    short.append(end.nodes[-1])
                    short._has_pseudo_start = True

                short.append(leaf)
                if not leaf.padding:
                    leaf.padding = PaddingNode(" ")
                list_node.append(short)

            if short_type:
                if isinstance(end, ShortcutNode):
                    if end.type == short_type:
                        end.append(leaf)
                    else:
                        flush_shortcut()
                        start_shortcut()
                else:
                    start_shortcut()
            else:
                if isinstance(end, ShortcutNode):
                    flush_shortcut()
                    list_node.append(leaf)
                else:
                    list_node.append(leaf)

        if isinstance(self.left, ValueNode):
            ret = ListNode("list wrapper")
            add_leaf(ret, self.left, self._left_short_type)
        else:
            ret = self.left._flatten_shortcut()
        if self.right is not None:
            if isinstance(self.right, ValueNode):
                add_leaf(ret, self.right, self._right_short_type)
            else:
                [ret.append(n) for n in self.right._flatten_shortcut()]
        return ret

    def _format_shortcut(self):
        """
        Handles formatting a subset of tree that has shortcuts in it.
        """
        list_wrap = self._flatten_shortcut()
        if isinstance(list_wrap.nodes[-1], ShortcutNode):
            list_wrap.nodes[-1].load_nodes(list_wrap.nodes[-1].nodes)
        return list_wrap.format()

    @property
    def comments(self):
        for node in self.nodes.values():
            yield from node.comments

    @property
    def left(self):
        """
        The left side of the binary tree.

        :returns: the left node of the syntax tree.
        :rtype: GeometryTree, ValueNode
        """
        return self._left_side

    @property
    def right(self):
        """
        The right side of the binary tree.

        :returns: the right node of the syntax tree.
        :rtype: GeometryTree, ValueNode
        """
        return self._right_side

    @property
    def operator(self):
        """
        The operator used for the binary tree.

        :returns: the operator used.
        :rtype: Operator
        """
        return self._operator

    def __iter__(self):
        """
        Iterates over the leafs
        """
        self._iter_l_r = False
        self._iter_complete = False
        self._sub_iter = None
        return self

    def __next__(self):
        if self._iter_complete:
            raise StopIteration
        if not self._iter_l_r:
            node = self.left
        if self._iter_l_r and self.right is not None:
            node = self.right
        if isinstance(node, ValueNode):
            if not self._iter_l_r:
                if self.right is not None:
                    self._iter_l_r = True
                else:
                    self._iter_complete = True
            else:
                self._iter_complete = True
            return node
        if self._sub_iter is None:
            self._sub_iter = iter(node)
        try:
            return next(self._sub_iter)
        except StopIteration:
            self._sub_iter = None
            if not self._iter_l_r:
                if self.right is not None:
                    self._iter_l_r = True
                else:
                    self._iter_complete = True
            else:
                raise StopIteration
            return next(self)

    def flatten(self):
        ret = []
        for node in self.nodes.values():
            if isinstance(node, (ValueNode, PaddingNode)):
                ret.append(node)
            else:
                ret += node.flatten()
        return ret


class PaddingNode(SyntaxNodeBase):
    """
    A syntax tree node to represent a collection of sequential padding elements.

    .. versionadded:: 0.2.0
        This was added with the major parser rework.

    :param token: The first padding token for this node.
    :type token: str
    :param is_comment: If the token provided is a comment.
    :type is_comment: bool
    """

    def __init__(self, token=None, is_comment=False):
        super().__init__("padding")
        if token is not None:
            self.append(token, is_comment)

    def __str__(self):
        return f"(Padding, {self._nodes})"

    def __repr__(self):
        return str(self)

    def __iadd__(self, other):
        if not isinstance(other, type(self)):
            raise TypeError(f"Can only combine with PaddingNodes. {other} given.")
        self._nodes += other.nodes
        return self

    @property
    def value(self):
        """
        A string representation of the contents of this node.

        All of the padding will be combined into a single string.

        :returns: a string sequence of the padding.
        :rtype: str
        """
        return "".join([val.format() for val in self.nodes])

    def is_space(self, i):
        """
        Determine if the value at i is a space or not.

        .. note::
            the newline, ``\\n``, by itself is not considered a space.

        :param i: the index of the element to check.
        :type i: int
        :returns: true iff the padding at that node is only spaces that are not ``\\n``.
        :raises IndexError: if the index i is not in ``self.nodes``.
        """
        val = self.nodes[i]
        if not isinstance(val, str):
            return False
        return len(val.strip()) == 0 and val != "\n"

    def has_space(self):
        """
        Determines if there is syntactically significant space anywhere in this node.

        :returns: True if there is syntactically significant (not in a comment) space.
        :rtype: bool
        """
        return any([self.is_space(i) for i in range(len(self))])

    def append(self, val, is_comment=False):
        """
        Append the node to this node.

        :param node: node
        :type node: str, CommentNode
        :param is_comment: whether or not the node is a comment.
        :type is_comment: bool
        """
        if is_comment and not isinstance(val, CommentNode):
            val = CommentNode(val)
        if isinstance(val, CommentNode):
            self.nodes.append(val)
            return
        parts = val.split("\n")
        if len(parts) > 1:
            for part in parts[:-1]:
                if part:
                    self._nodes += [part, "\n"]
                else:
                    self._nodes.append("\n")
            if parts[-1]:
                self._nodes.append(parts[-1])
        else:
            self._nodes.append(val)

    def format(self):
        ret = ""
        for node in self.nodes:
            if isinstance(node, str):
                ret += node
            else:
                ret += node.format()
        return ret

    @property
    def comments(self):
        for node in self.nodes:
            if isinstance(node, CommentNode):
                yield node

    def _get_first_comment(self):
        """
        Get the first index that is a ``c`` style comment.

        :returns: the index of the first comment, if there is no comment then None.
        :rtype: int, None
        """
        for i, item in enumerate(self.nodes):
            if isinstance(item, CommentNode) and not item.is_dollar:
                return i
        return None

    def get_trailing_comment(self):
        i = self._get_first_comment()
        if i is not None:
            return self.nodes[i:]
        return None

    def _delete_trailing_comment(self):
        i = self._get_first_comment()
        if i is not None:
            del self._nodes[i:]

    def _grab_beginning_comment(self, extra_padding):
        """
        Consumes the provided comment, and moves it to the beginning of this node.

        :param extra_padding: the padding comment to add to the beginning of this padding.
        :type extra_padding: list
        """
        if extra_padding[-1] != "\n":
            extra_padding.append("\n")
        self._nodes = extra_padding + self.nodes

    def __eq__(self, other):
        if not isinstance(other, (type(self), str)):
            raise "PaddingNode can only be compared to PaddingNode or str"
        if isinstance(other, type(self)):
            other = other.format()
        return self.format() == other

    def has_graveyard_comment(self):
        """
        Checks if there is a graveyard comment that is preventing information from being part of the tree.

        A graveyard comment is one that accidentally suppresses important information in the syntax tree.

        For example::

            imp:n=1 $ grave yard Vol=1

        Should be::

            imp:n=1 $ grave yard
            Vol=1

        .. versionadded:: 0.4.0

        :returns: True if this PaddingNode contains a graveyard comment.
        :rtype: bool
        """
        found = False
        for i, item in reversed(list(enumerate(self.nodes))):
            if isinstance(item, CommentNode):
                found = True
                break
        if not found:
            return False
        trail = self.nodes[i:]
        if len(trail) == 1:
            if trail[0].format().endswith("\n"):
                return False
            return True
        for node in trail[1:]:
            if node == "\n":
                return False
        return True


class CommentNode(SyntaxNodeBase):
    """
    Object to represent a comment in an MCNP problem.

    .. versionadded:: 0.2.0
        This was added with the major parser rework.

    :param input: the token from the lexer
    :type input: Token
    """

    _MATCHER = re.compile(
        rf"""(?P<delim>
                (\s{{0,{constants.BLANK_SPACE_CONTINUE-1}}}C\s?)
                |(\$\s?)
             )
            (?P<contents>.*)""",
        re.I | re.VERBOSE,
    )
    """
    A re matcher to confirm this is a C style comment.
    """

    def __init__(self, input):
        super().__init__("comment")
        is_dollar, node = self._convert_to_node(input)
        self._is_dollar = is_dollar
        self._nodes = [node]

    def _convert_to_node(self, token):
        """
        Converts the token to a Syntax Node to store.

        :param token: the token to convert.
        :type token: str
        :returns: the SyntaxNode of the Comment.
        :rtype: SyntaxNode
        """
        if match := self._MATCHER.match(token):
            start = match["delim"]
            comment_line = match["contents"]
            is_dollar = "$" in start
        else:
            start = token
            comment_line = ""
            is_dollar = "$" in start
        return (
            is_dollar,
            SyntaxNode(
                "comment",
                {
                    "delimiter": ValueNode(start, str),
                    "data": ValueNode(comment_line, str),
                },
            ),
        )

    def append(self, token):
        """
        Append the comment token to this node.

        :param token: the comment token
        :type token: str
        """
        is_dollar, node = self._convert_to_node(token)
        if is_dollar or self._is_dollar:
            raise TypeError(
                f"Cannot append multiple comments to a dollar comment. {token} given."
            )
        self._nodes.append(node)

    @property
    def is_dollar(self):
        """
        Whether or not this CommentNode is a dollar sign ($) comment.

        :returns: True iff this is a dollar sign comment.
        :rtype: bool
        """
        return self._is_dollar

    @property
    def contents(self):
        """
        The contents of the comments without delimiters (i.e., $/C).

        :returns: String of the contents
        :rtype: str
        """
        return "\n".join([node["data"].value for node in self.nodes])

    def format(self):
        ret = ""
        for node in self.nodes:
            ret += node.format()
        return ret

    @property
    def comments(self):
        yield from [self]

    def __str__(self):
        return self.format()

    def __repr__(self):
        ret = f"COMMENT: "
        for node in self.nodes:
            ret += node.format()
        return ret

    def __eq__(self, other):
        return str(self) == str(other)


class ValueNode(SyntaxNodeBase):
    """
    A syntax node to represent the leaf node.

    This stores the original input token, the current value,
    and the possible associated padding.

    .. versionadded:: 0.2.0
        This was added with the major parser rework.

    :param token: the original token for the ValueNode.
    :type token: str
    :param token_type: the type for the ValueNode.
    :type token_type: class
    :param padding: the padding for this node.
    :type padding: PaddingNode
    :param never_pad: If true an ending space will never be added to this.
    :type never_pad: bool
    """

    _FORMATTERS = {
        float: {
            "value_length": 0,
            "precision": 5,
            "zero_padding": 0,
            "sign": "-",
            "divider": "e",
            "exponent_length": 0,
            "exponent_zero_pad": 0,
            "as_int": False,
            "int_tolerance": 1e-6,
            "is_scientific": True,
        },
        int: {"value_length": 0, "zero_padding": 0, "sign": "-"},
        str: {"value_length": 0},
    }
    """
    The default formatters for each type.
    """

    _SCIENTIFIC_FINDER = re.compile(
        r"""
            [+\-]?                      # leading sign if any
            (?P<significand>\d+\.*\d*)  # the actual number
            ((?P<e>[eE])                 # non-optional e with +/-
            [+\-]?|
            [+\-])                  #non-optional +/- if fortran float is used
            (?P<exponent>\d+)                    #exponent
        """,
        re.VERBOSE,
    )
    """
    A regex for finding scientific notation.
    """

    def __init__(self, token, token_type, padding=None, never_pad=False):
        super().__init__("")
        self._token = token
        self._type = token_type
        self._formatter = self._FORMATTERS[token_type].copy()
        self._is_neg_id = False
        self._is_neg_val = False
        self._og_value = None
        self._never_pad = never_pad
        if token is None:
            self._value = None
        elif isinstance(token, input_parser.mcnp_input.Jump):
            self._value = None
        elif token_type == float:
            self._value = fortran_float(token)
        elif token_type == int:
            self._value = int(token)
        else:
            self._value = token
        self._og_value = self.value
        self._padding = padding
        self._nodes = [self]
        self._is_reversed = False

    def _convert_to_int(self):
        """
        Converts a float ValueNode to an int ValueNode.
        """
        if self._type not in {float, int}:
            raise ValueError(f"ValueNode must be a float to convert to int")
        self._type = int
        if self._token is not None and not isinstance(
            self._token, input_parser.mcnp_input.Jump
        ):
            try:
                self._value = int(self._token)
            except ValueError as e:
                parts = self._token.split(".")
                if len(parts) > 1 and int(parts[1]) == 0:
                    self._value = int(parts[0])
                else:
                    raise e
        self._formatter = self._FORMATTERS[int].copy()

    def _convert_to_enum(
        self, enum_class, allow_none=False, format_type=str, switch_to_upper=False
    ):
        """
        Converts the ValueNode to an Enum for allowed values.

        :param enum_class: the class for the enum to use.
        :type enum_class: Class
        :param allow_none: Whether or not to allow None as a value.
        :type allow_none: bool
        :param format_type: the base data type to format this ValueNode as.
        :type format_type: Class
        :param switch_to_upper: Whether or not to convert a string to upper case before convert to enum.
        :type switch_to_upper: bool
        """
        self._type = enum_class
        if switch_to_upper:
            value = self._value.upper()
        else:
            value = self._value
        if not (allow_none and self._value is None):
            self._value = enum_class(value)
        self._formatter = self._FORMATTERS[format_type].copy()

    @property
    def is_negatable_identifier(self):
        """
        Whether or not this value is a negatable identifier.

        Example use: the surface transform or periodic surface is switched based on positive
        or negative.

        This means:
            1. the ValueNode is an int.
            2. The ``value`` will always be positive.
            3. The ``is_negative`` property will be available.

        :returns: the state of this marker.
        :rtype: bool
        """
        return self._is_neg_id

    @is_negatable_identifier.setter
    def is_negatable_identifier(self, val):
        if val == True:
            self._convert_to_int()
            if self.value is not None:
                self._is_neg = self.value < 0
                self._value = abs(self._value)
            else:
                self._is_neg = None
        self._is_neg_id = val

    @property
    def is_negatable_float(self):
        """
        Whether or not this value is a negatable float.

        Example use: cell density.

        This means:
            1. the ValueNode is an int.
            2. The ``value`` will always be positive.
            3. The ``is_negative`` property will be available.

        :returns: the state of this marker.
        :rtype: bool
        """
        return self._is_neg_val

    @is_negatable_float.setter
    def is_negatable_float(self, val):
        if val == True:
            if self.value is not None:
                self._is_neg = self.value < 0
                self._value = abs(self._value)
            else:
                self._is_neg = None
        self._is_neg_val = val

    @property
    def is_negative(self):
        """
        Whether or not this value is negative.

        If neither :func:`is_negatable_float` or :func:`is_negatable_identifier` is true
        then this will return ``None``.

        :returns: true if this value is negative (either in input or through state).
        :rtype: bool, None
        """
        if self.is_negatable_identifier or self.is_negatable_float:
            return self._is_neg

    @is_negative.setter
    def is_negative(self, val):
        if self.is_negatable_identifier or self.is_negatable_float:
            self._is_neg = val

    def _reverse_engineer_formatting(self):
        """
        Tries its best to figure out and update the formatter based on the token's format.
        """
        if not self._is_reversed and self._token is not None:
            self._is_reversed = True
            token = self._token
            if isinstance(token, input_parser.mcnp_input.Jump):
                token = "J"
            if isinstance(token, (int, float)):
                token = str(token)
            self._formatter["value_length"] = len(token)
            if self.padding:
                if self.padding.is_space(0):
                    self._formatter["value_length"] += len(self.padding.nodes[0])

            if self._type == float or self._type == int:
                no_zero_pad = token.lstrip("0+-")
                length = len(token)
                delta = length - len(no_zero_pad)
                if token.startswith("+") or token.startswith("-"):
                    delta -= 1
                    if token.startswith("+"):
                        self._formatter["sign"] = "+"
                    if token.startswith("-"):
                        self._formatter["sign"] = " "
                if delta > 0:
                    self._formatter["zero_padding"] = length
                if self._type == float:
                    self._reverse_engineer_float()

    def _reverse_engineer_float(self):
        token = self._token
        if isinstance(token, float):
            token = str(token)
        if isinstance(token, input_parser.mcnp_input.Jump):
            token = "J"
        if match := self._SCIENTIFIC_FINDER.match(token):
            groups = match.groupdict(default="")
            self._formatter["is_scientific"] = True
            significand = groups["significand"]
            self._formatter["divider"] = groups["e"]
            # extra space for the "e" in scientific and... stuff
            self._formatter["zero_padding"] += 4
            exponent = groups["exponent"]
            temp_exp = exponent.lstrip("0")
            if exponent != temp_exp:
                self._formatter["exponent_length"] = len(exponent)
                self._formatter["exponent_zero_pad"] = len(exponent)
        else:
            self._formatter["is_scientific"] = False
            significand = token
        parts = significand.split(".")
        if len(parts) == 2:
            precision = len(parts[1])
        else:
            precision = self._FORMATTERS[float]["precision"]
            self._formatter["as_int"] = True

        self._formatter["precision"] = precision

    def _can_float_to_int_happen(self):
        """
        Checks if you can format a floating point as an int.

        E.g., 1.0 -> 1

        Considers if this was done in the input, and if the value is close to the int value.

        :rtype: bool.
        """
        if self._type != float or not self._formatter["as_int"]:
            return False
        nearest_int = round(self.value)
        if not math.isclose(nearest_int, self.value, rel_tol=rel_tol, abs_tol=abs_tol):
            return False
        return True

    @property
    def _print_value(self):
        """
        The print version of the value.

        This takes a float/int that is negatable, and negates it
        based on the ``is_negative`` value.

        :rtype: int, float
        """
        if self._type in {int, float} and self.is_negative:
            return -self.value
        return self.value

    @property
    def _value_changed(self):
        """
        Checks if the value has changed at all from first parsing.

        Used to shortcut formatting and reverse engineering.

        :rtype: bool
        """
        if self.value is None and self._og_value is None:
            return False
        if self.value is None or self._og_value is None:
            return True
        if self._type in {float, int}:
            return not math.isclose(
                self._print_value, self._og_value, rel_tol=rel_tol, abs_tol=abs_tol
            )
        return self.value != self._og_value

    def format(self):
        if not self._value_changed:
            return f"{self._token}{self.padding.format() if self.padding else ''}"
        if self.value is None:
            return ""
        self._reverse_engineer_formatting()
        if issubclass(self.type, enum.Enum):
            value = self.value.value
        else:
            value = self._print_value
        if self._type == int or self._can_float_to_int_happen():
            temp = "{value:0={sign}{zero_padding}d}".format(
                value=int(value), **self._formatter
            )
        elif self._type == float:
            # default to python general if new value
            if not self._is_reversed:
                temp = "{value:0={sign}{zero_padding}.{precision}g}".format(
                    value=value, **self._formatter
                )
            elif self._formatter["is_scientific"]:
                temp = "{value:0={sign}{zero_padding}.{precision}e}".format(
                    value=value, **self._formatter
                )
                temp = temp.replace("e", self._formatter["divider"])
                temp_match = self._SCIENTIFIC_FINDER.match(temp)
                exponent = temp_match.group("exponent")
                start, end = temp_match.span("exponent")
                new_exp_temp = "{value:0={zero_padding}d}".format(
                    value=int(exponent),
                    zero_padding=self._formatter["exponent_zero_pad"],
                )
                new_exp = "{temp:<{value_length}}".format(
                    temp=new_exp_temp, value_length=self._formatter["exponent_length"]
                )
                temp = temp[0:start] + new_exp + temp[end:]
            elif self._formatter["as_int"]:
                temp = "{value:0={sign}0{zero_padding}g}".format(
                    value=value, **self._formatter
                )
            else:
                temp = "{value:0={sign}0{zero_padding}.{precision}f}".format(
                    value=value, **self._formatter
                )
        else:
            temp = str(value)
        if self.padding:
            if self.padding.is_space(0):
                # if there was and end space, and we ran out of space, and there isn't
                # a saving space later on
                if len(temp) >= self._formatter["value_length"] and not (
                    len(self.padding) > 1
                    and (self.padding.is_space(1) or self.padding.nodes[1] == "\n")
                ):
                    pad_str = " "
                else:
                    pad_str = ""
                extra_pad_str = "".join([x.format() for x in self.padding.nodes[1:]])
            else:
                pad_str = ""
                extra_pad_str = "".join([x.format() for x in self.padding.nodes])
        else:
            pad_str = ""
            extra_pad_str = ""
        buffer = "{temp:<{value_length}}{padding}".format(
            temp=temp, padding=pad_str, **self._formatter
        )
        if len(buffer) > self._formatter["value_length"] and self._token is not None:
            warning = LineExpansionWarning(
                f"The value has expanded, and may change formatting. The original value was {self._token}, new value is {temp}."
            )
            warning.cause = "value"
            warning.og_value = self._token
            warning.new_value = temp
            warnings.warn(
                warning,
                stacklevel=2,
            )
        return buffer + extra_pad_str

    @property
    def comments(self):
        if self.padding is not None:
            yield from self.padding.comments
        else:
            yield from []

    def get_trailing_comment(self):
        if self.padding is None:
            return
        return self.padding.get_trailing_comment()

    def _delete_trailing_comment(self):
        if self.padding is None:
            return
        self.padding._delete_trailing_comment()

    @property
    def padding(self):
        """
        The padding if any for this ValueNode.

        :returns: the padding if any.
        :rtype: PaddingNode
        """
        return self._padding

    @padding.setter
    def padding(self, pad):
        self._padding = pad

    @property
    def type(self):
        """
        The data type for this ValueNode.

        Examples: float, int, str, Lattice

        :returns: the class for the value of this node.
        :rtype: Class
        """
        return self._type

    @property
    def token(self):
        """
        The original text (token) for this ValueNode.

        :returns: the original input.
        :rtype: str
        """
        return self._token

    def __str__(self):
        return f"(Value, {self._value}, padding: {self._padding})"

    def __repr__(self):
        return str(self)

    @property
    def value(self):
        """
        The current semantic value of this ValueNode.

        This is the parsed meaning in the type of ``self.type``,
        that can be updated. When this value is updated, next time format()
        is ran this value will be used.

        :returns: the node's value in type ``type``.
        :rtype: float, int, str, enum
        """
        return self._value

    @property
    def never_pad(self):
        """
        Whether or not this value node will not have extra spaces added.

        :returns: true if extra padding is not adding at the end if missing.
        :rtype: bool
        """
        return self._never_pad

    @never_pad.setter
    def never_pad(self, never_pad):
        self._never_pad = never_pad

    @value.setter
    def value(self, value):
        if self.is_negative is not None and value is not None:
            value = abs(value)
        self._check_if_needs_end_padding(value)
        self._value = value

    def _check_if_needs_end_padding(self, value):
        if value is None or self.value is not None or self._never_pad:
            return
        # if not followed by a trailing space
        if self.padding is None:
            self.padding = PaddingNode(" ")

    def __eq__(self, other):
        if not isinstance(other, (type(self), str, int, float)):
            raise TypeError(
                f"ValueNode can't be equal to {type(other)} type. {other} given."
            )
        if isinstance(other, ValueNode):
            other_val = other.value
            if self.type != other.type:
                return False
        else:
            other_val = other
            if self.type != type(other):
                return False

        if self.type == float and self.value is not None and other_val is not None:
            return math.isclose(self.value, other_val, rel_tol=rel_tol, abs_tol=abs_tol)
        return self.value == other_val


class ParticleNode(SyntaxNodeBase):
    """
    A node to hold particles information in a :class:`ClassifierNode`.

    .. versionadded:: 0.2.0
        This was added with the major parser rework.

    :param name: the name for the node.
    :type name: str
    :param token: the original token from parsing
    :type token: str
    """

    _letter_finder = re.compile(r"([a-zA-Z])")

    def __init__(self, name, token):
        super().__init__(name)
        self._nodes = [self]
        self._token = token
        self._order = []
        classifier_chunks = token.replace(":", "").split(",")
        self._particles = set()
        self._formatter = {"upper": False}
        for chunk in classifier_chunks:
            part = Particle(chunk.upper())
            self._particles.add(part)
            self._order.append(part)

    @property
    def token(self):
        """
        The original text (token) for this ParticleNode.

        :returns: the original input.
        :rtype: str
        """
        return self._token

    @property
    def particles(self):
        """
        The particles included in this node.

        :returns: a set of the particles being used.
        :rtype: set
        """
        return self._particles

    @particles.setter
    def particles(self, values):
        if not isinstance(values, (list, set)):
            raise TypeError(f"Particles must be a set. {values} given.")
        for value in values:
            if not isinstance(value, Particle):
                raise TypeError(f"All particles must be a Particle. {value} given")
        if isinstance(values, list):
            self._order = values
            values = set(values)
        self._particles = values

    def add(self, value):
        """
        Add a particle to this node.

        :param value: the particle to add.
        :type value: Particle
        """
        if not isinstance(value, Particle):
            raise TypeError(f"All particles must be a Particle. {value} given")
        self._order.append(value)
        self._particles.add(value)

    def remove(self, value):
        """
        Remove a particle from this node.

        :param value: the particle to remove.
        :type value: Particle
        """
        if not isinstance(value, Particle):
            raise TypeError(f"All particles must be a Particle. {value} given")
        self._particles.remove(value)
        self._order.remove(value)

    @property
    def _particles_sorted(self):
        """
        The particles in this node ordered in a nice-ish way.

        Ordering:
            1. User input.
            2. Order of particles appended
            3. randomly at the end if all else fails.

        :rtype: list
        """
        ret = self._order
        ret_set = set(ret)
        remainder = self.particles - ret_set
        extras = ret_set - self.particles
        for straggler in sorted(remainder):
            ret.append(straggler)
        for useless in extras:
            ret.remove(useless)
        return ret

    def format(self):
        self._reverse_engineer_format()
        if self._formatter["upper"]:
            parts = [p.value.upper() for p in self._particles_sorted]
        else:
            parts = [p.value.lower() for p in self._particles_sorted]
        return f":{','.join(parts)}"

    def _reverse_engineer_format(self):
        total_match = 0
        upper_match = 0
        for match in self._letter_finder.finditer(self._token):
            if match:
                if match.group(0).isupper():
                    upper_match += 1
                total_match += 1
        if upper_match / total_match >= 0.5:
            self._formatter["upper"] = True

    @property
    def comments(self):
        yield from []

    def __repr__(self):
        return self.format()

    def __iter__(self):
        return iter(self.particles)


class ListNode(SyntaxNodeBase):
    """
    A node to represent a list of values.

    .. versionadded:: 0.2.0
        This was added with the major parser rework.

    :param name: the name of this node.
    :type name: str
    """

    def __init__(self, name):
        super().__init__(name)
        self._shortcuts = []

    def __repr__(self):
        return f"(list: {self.name}, {self.nodes})"

    def update_with_new_values(self, new_vals):
        """
        Update this list node with new values.

        This will first try to find if any shortcuts in the original input match up with
        the new values. If so it will then "zip" out those shortcuts to consume
        as many neighbor nodes as possible.
        Finally, the internal shortcuts, and list will be updated to reflect the new state.

        :param new_vals: the new values (a list of ValueNodes)
        :type new_vals: list
        """
        if not new_vals:
            self._nodes = []
            return
        new_vals_cache = {id(v): v for v in new_vals}
        # bind shortcuts to single site in new values
        for shortcut in self._shortcuts:
            for node in shortcut.nodes:
                if id(node) in new_vals_cache:
                    new_vals_cache[id(node)] = shortcut
                    shortcut.nodes.clear()
                    break
        self._expand_shortcuts(new_vals, new_vals_cache)
        self._shortcuts = []
        self._nodes = []
        for key, node in new_vals_cache.items():
            if isinstance(node, ShortcutNode):
                if (
                    len(self._shortcuts) > 0 and node is not self._shortcuts[-1]
                ) or len(self._shortcuts) == 0:
                    self._shortcuts.append(node)
                    self._nodes.append(node)
            else:
                self._nodes.append(node)
        end = self._nodes[-1]
        # pop off final shortcut if it's a jump the user left off
        if (
            isinstance(end, ShortcutNode)
            and end._type == Shortcuts.JUMP
            and len(end._original) == 0
        ):
            self._nodes.pop()
            self._shortcuts.pop()

    def _expand_shortcuts(self, new_vals, new_vals_cache):
        """
        Expands the existing shortcuts, and tries to "zip out" and consume their neighbors.

        :param new_vals: the new values.
        :type new_vals: list
        :param new_vals_cache: a dictionary mapping the id of the ValueNode to the ValueNode
            or ShortcutNode. This is ordered the same as ``new_vals``.
        :type new_vals_cache: dict
        """

        def try_expansion(shortcut, value):
            status = shortcut.consume_edge_node(
                value, 1, i == last_end + 1 and last_end != 0
            )
            if status:
                new_vals_cache[id(value)] = shortcut
            else:
                new_vals_cache[id(value)] = value
            return status

        def try_reverse_expansion(shortcut, i, last_end):
            if i > 1:
                for value in new_vals[i - 1 : last_end : -1]:
                    if shortcut.consume_edge_node(value, -1):
                        new_vals_cache[id(value)] = shortcut
                    else:
                        new_vals_cache[id(value)] = value
                        return

        def check_for_orphan_jump(value):
            """
            Checks if the current Jump is not tied to an existing Shortcut
            """
            nonlocal shortcut
            if value.value is None and shortcut is None:
                shortcut = ShortcutNode(p=None, short_type=Shortcuts.JUMP)
                if shortcut.consume_edge_node(value, 1):
                    new_vals_cache[id(value)] = shortcut

        shortcut = None
        last_end = 0
        for i, value in enumerate(new_vals_cache.values()):
            # found a new shortcut
            if isinstance(value, ShortcutNode):
                # shortcuts bumped up against each other
                if shortcut is not None:
                    last_end = i - 1
                shortcut = value
                if try_expansion(shortcut, new_vals[i]):
                    try_reverse_expansion(shortcut, i, last_end)
                else:
                    shortcut = None
            # otherwise it is actually a value to expand as well
            else:
                if shortcut is not None:
                    if not try_expansion(shortcut, new_vals[i]):
                        last_end = i - 1
                        shortcut = None
                        check_for_orphan_jump(new_vals[i])
                else:
                    check_for_orphan_jump(new_vals[i])

    def append(self, val, from_parsing=False):
        """
        Append the node to this node.

        :param node: node
        :type node: ValueNode, ShortcutNode
        :param from_parsing: If this is being append from the parsers, and not elsewhere.
        :type from_parsing: bool
        """
        if isinstance(val, ShortcutNode):
            self._shortcuts.append(val)
        if len(self) > 0 and from_parsing:
            last = self[-1]
            if isinstance(last, ValueNode) and (
                (last.padding and not last.padding.has_space) or last.padding is None
            ):
                self[-1].never_pad = True
        super().append(val)

    @property
    def comments(self):
        for node in self.nodes:
            yield from node.comments

    def format(self):
        ret = ""
        length = len(self.nodes)
        last_node = None
        for i, node in enumerate(self.nodes):
            # adds extra padding
            if (
                isinstance(node, ValueNode)
                and node.padding is None
                and i < length - 1
                and not isinstance(self.nodes[i + 1], PaddingNode)
                and not node.never_pad
            ):
                node.padding = PaddingNode(" ")
            if isinstance(last_node, ShortcutNode) and isinstance(node, ShortcutNode):
                ret += node.format(last_node)
            else:
                ret += node.format()
            last_node = node
        return ret

    def __iter__(self):
        for node in self.nodes:
            if isinstance(node, ShortcutNode):
                yield from node.nodes
            else:
                yield node

    def __contains__(self, value):
        for node in self:
            if node == value:
                return True
        return False

    def __getitem__(self, indx):
        if isinstance(indx, slice):
            return self.__get_slice(indx)
        if indx >= 0:
            for i, item in enumerate(self):
                if i == indx:
                    return item
        else:
            items = list(self)
            return items[indx]
        raise IndexError(f"{indx} not in ListNode")

    def __get_slice(self, i: slice):
        """
        Helper function for __getitem__ with slices.
        """
        rstep = i.step if i.step is not None else 1
        rstart = i.start
        rstop = i.stop
        if rstep < 0:  # Backwards
            if rstart is None:
                rstart = len(self.nodes) - 1
            if rstop is None:
                rstop = 0
            rstop -= 1
        else:  # Forwards
            if rstart is None:
                rstart = 0
            if rstop is None:
                rstop = len(self.nodes) - 1
            rstop += 1
        buffer = []
        allowed_indices = range(rstart, rstop, rstep)
        for i, item in enumerate(self):
            if i in allowed_indices:
                buffer.append(item)
        ret = ListNode(f"{self.name}_slice")
        if rstep < 0:
            buffer.reverse()
        for val in buffer:
            ret.append(val)
        return ret

    def remove(self, obj):
        """
        Removes the given object from this list.

        :param obj: the object to remove.
        :type obj: ValueNode
        """
        self.nodes.remove(obj)

    def __eq__(self, other):
        if not isinstance(other, (type(self), list)):
            raise TypeError(
                f"ListNode can only be compared to a ListNode or List. {other} given."
            )
        if len(self) != len(other):
            return False
        for lhs, rhs in zip(self, other):
            if lhs != rhs:
                return False
        return True


class IsotopesNode(SyntaxNodeBase):
    """
    A node for representing isotopes and their concentration.

    This stores a list of tuples of ZAIDs and concentrations.

    .. versionadded:: 0.2.0
        This was added with the major parser rework.

    :param name: a name for labeling this node.
    :type name: str
    """

    def __init__(self, name):
        super().__init__(name)

    def append(self, isotope_fraction):
        """
        Append the node to this node.

        :param isotope_fraction: the isotope_fraction to add. This must be a tuple from
            A Yacc production. This will consist of: the string identifying the Yacc production,
            a ValueNode that is the ZAID, and a ValueNode of the concentration.
        :type isotope_fraction: tuple
        """
        isotope, concentration = isotope_fraction[1:3]
        self._nodes.append((isotope, concentration))

    def format(self):
        ret = ""
        for isotope, concentration in self.nodes:
            ret += isotope.format() + concentration.format()
        return ret

    def __repr__(self):
        return f"(Isotopes: {self.nodes})"

    def __iter__(self):
        return iter(self.nodes)

    @property
    def comments(self):
        for node in self.nodes:
            for value in node:
                yield from value.comments

    def get_trailing_comment(self):
        tail = self.nodes[-1]
        tail = tail[1]
        return tail.get_trailing_comment()

    def _delete_trailing_comment(self):
        tail = self.nodes[-1]
        tail = tail[1]
        tail._delete_trailing_comment()

    def flatten(self):
        ret = []
        for node_group in self.nodes:
            ret += node_group
        return ret


class ShortcutNode(ListNode):
    """
    A node that pretends to be a :class:`ListNode` but is actually representing a shortcut.

    This takes the shortcut tokens, and expands it into their "virtual" values.

    .. versionadded:: 0.2.0
        This was added with the major parser rework.

    :param p: the parsing object to parse.
    :type p: sly.yacc.YaccProduction
    :param short_type: the type of the shortcut.
    :type short_type: Shortcuts
    """

    _shortcut_names = {
        ("REPEAT", "NUM_REPEAT"): Shortcuts.REPEAT,
        ("JUMP", "NUM_JUMP"): Shortcuts.JUMP,
        ("INTERPOLATE", "NUM_INTERPOLATE"): Shortcuts.INTERPOLATE,
        ("LOG_INTERPOLATE", "NUM_LOG_INTERPOLATE"): Shortcuts.LOG_INTERPOLATE,
        ("MULTIPLY", "NUM_MULTIPLY"): Shortcuts.MULTIPLY,
    }
    _num_finder = re.compile(r"\d+")

    def __init__(self, p=None, short_type=None, data_type=float):
        self._type = None
        self._end_pad = None
        self._nodes = collections.deque()
        self._original = []
        self._full = False
        self._num_node = ValueNode(None, float, never_pad=True)
        self._data_type = data_type
        if p is not None:
            for search_strs, shortcut in self._shortcut_names.items():
                for search_str in search_strs:
                    if hasattr(p, search_str):
                        super().__init__(search_str.lower())
                        self._type = shortcut
            if self._type is None:
                raise ValueError("must use a valid shortcut")
            self._original = list(p)
            if self._type == Shortcuts.REPEAT:
                self._expand_repeat(p)
            elif self._type == Shortcuts.MULTIPLY:
                self._expand_multiply(p)
            elif self._type == Shortcuts.JUMP:
                self._expand_jump(p)
            elif self._type in {Shortcuts.INTERPOLATE, Shortcuts.LOG_INTERPOLATE}:
                self._expand_interpolate(p)
        elif short_type is not None:
            if not isinstance(short_type, Shortcuts):
                raise TypeError(f"Shortcut type must be Shortcuts. {short_type} given.")
            self._type = short_type
            if self._type in {
                Shortcuts.INTERPOLATE,
                Shortcuts.LOG_INTERPOLATE,
                Shortcuts.JUMP,
                Shortcuts.JUMP,
            }:
                self._num_node = ValueNode(None, int, never_pad=True)
            self._end_pad = PaddingNode(" ")

    def load_nodes(self, nodes):
        """
        Loads the given nodes into this shortcut, and update needed information.

        For interpolate nodes should start and end with the beginning/end of
        the interpolation.

        :param nodes: the nodes to be loaded.
        :type nodes: list
        """
        self._nodes = collections.deque(nodes)
        if self.type in {Shortcuts.INTERPOLATE, Shortcuts.LOG_INTERPOLATE}:
            self._begin = nodes[0].value
            self._end = nodes[-1].value
            if self.type == Shortcuts.LOG_INTERPOLATE:
                self._begin = math.log10(self._begin)
                self._end = math.log10(self._end)
            self._spacing = (self._end - self._begin) / (len(nodes) - 1)

    @property
    def end_padding(self):
        """
        The padding at the end of this shortcut.

        :rtype: PaddingNode
        """
        return self._end_pad

    @end_padding.setter
    def end_padding(self, padding):
        if not isinstance(padding, PaddingNode):
            raise TypeError(
                f"End padding must be of type PaddingNode. {padding} given."
            )
        self._end_pad = padding

    @property
    def type(self):
        """
        The Type of shortcut this ShortcutNode represents.

        :rtype: Shortcuts
        """
        return self._type

    def __repr__(self):
        return f"(shortcut:{self._type}: {self.nodes})"

    def _get_last_node(self, p):
        last = p[0]
        if isinstance(last, ValueNode):
            return collections.deque([last])
        return collections.deque()

    def _expand_repeat(self, p):
        self._nodes = self._get_last_node(p)
        repeat = p[1]
        try:
            repeat_num_str = repeat.lower().replace("r", "")
            repeat_num = int(repeat_num_str)
            self._num_node = ValueNode(repeat_num, int, never_pad=True)
        except ValueError:
            repeat_num = 1
            self._num_node = ValueNode(None, int, never_pad=True)
        if isinstance(p[0], ValueNode):
            last_val = p[0]
        else:
            if isinstance(p[0], GeometryTree):
                last_val = list(p[0])[-1]
            else:
                last_val = p[0].nodes[-1]
        if last_val.value is None:
            raise ValueError(f"Repeat cannot follow a jump. Given: {list(p)}")
        self._nodes += [copy.deepcopy(last_val) for i in range(repeat_num)]

    def _expand_multiply(self, p):
        self._nodes = self._get_last_node(p)
        mult_str = p[1].lower().replace("m", "")
        mult_val = fortran_float(mult_str)
        self._num_node = ValueNode(mult_str, float, never_pad=True)
        if isinstance(p[0], ValueNode):
            last_val = self.nodes[-1]
        elif isinstance(p[0], GeometryTree):
            if "right" in p[0].nodes:
                last_val = p[0].nodes["right"]
            else:
                last_val = p[0].nodes["left"]
        else:
            last_val = p[0].nodes[-1]
        if last_val.value is None:
            raise ValueError(f"Multiply cannot follow a jump. Given: {list(p)}")
        self._nodes.append(copy.deepcopy(last_val))
        self.nodes[-1].value *= mult_val

    def _expand_jump(self, p):
        try:
            jump_str = p[0].lower().replace("j", "")
            jump_num = int(jump_str)
            self._num_node = ValueNode(jump_str, int, never_pad=True)
        except ValueError:
            jump_num = 1
            self._num_node = ValueNode(None, int, never_pad=True)
        for i in range(jump_num):
            self._nodes.append(ValueNode(input_parser.mcnp_input.Jump(), float))

    def _expand_interpolate(self, p):
        if self._type == Shortcuts.LOG_INTERPOLATE:
            is_log = True
        else:
            is_log = False
        if hasattr(p, "geometry_term"):
            term = p.geometry_term
            if isinstance(term, GeometryTree):
                begin = list(term)[-1].value
            else:
                begin = term.value
            end = p.number_phrase.value
        else:
            if isinstance(p[0], ListNode):
                begin = p[0].nodes[-1].value
            else:
                begin = p[0].value
            end = p.number_phrase.value
        self._nodes = self._get_last_node(p)
        if begin is None:
            raise ValueError(f"Interpolates cannot follow a jump. Given: {list(p)}")
        match = self._num_finder.search(p[1])
        if match:
            number = int(match.group(0))
            self._num_node = ValueNode(match.group(0), int, never_pad=True)
        else:
            number = 1
            self._num_node = ValueNode(None, int, never_pad=True)
        if is_log:
            begin = math.log(begin, 10)
            end = math.log(end, 10)
        spacing = (end - begin) / (number + 1)
        for i in range(number):
            if is_log:
                new_val = 10 ** (begin + spacing * (i + 1))
            else:
                new_val = begin + spacing * (i + 1)
            self.append(
                ValueNode(
                    str(self._data_type(new_val)), self._data_type, never_pad=True
                )
            )
        self._begin = begin
        self._end = end
        self._spacing = spacing
        self.append(p.number_phrase)

    def _can_consume_node(self, node, direction, last_edge_shortcut=False):
        """
        If it's possible to consume this node.

        :param node: the node to consume
        :type node: ValueNode
        :param direction: the direct to go in. Must be in {-1, 1}
        :type direction: int
        :param last_edge_shortcut: Whether the previous node in the list was part of a different shortcut
        :type last_edge_shortcut: bool
        :returns: true it can be consumed.
        :rtype: bool
        """
        if self._type == Shortcuts.JUMP:
            if node.value is None:
                return True

        # REPEAT
        elif self._type == Shortcuts.REPEAT:
            if len(self.nodes) == 0 and node.value is not None:
                return True
            if direction == 1:
                edge = self.nodes[-1]
            else:
                edge = self.nodes[0]
            if edge.type != node.type or edge.value is None or node.value is None:
                return False
            if edge.type in {int, float} and math.isclose(
                edge.value, node.value, rel_tol=rel_tol, abs_tol=abs_tol
            ):
                return True
            elif edge.value == node.value:
                return True

        # INTERPOLATE
        elif self._type in {Shortcuts.INTERPOLATE, Shortcuts.LOG_INTERPOLATE}:
            return self._is_valid_interpolate_edge(node, direction)
        # Multiply can only ever have 1 value
        elif self._type == Shortcuts.MULTIPLY:
            # can't do a multiply with a Jump
            if node.value is None:
                return False
            if len(self.nodes) == 0:
                # clear out old state if needed
                self._full = False
                if last_edge_shortcut:
                    self._full = True
                return True
            if len(self.nodes) == 1 and not self._full:
                return True
        return False

    def _is_valid_interpolate_edge(self, node, direction):
        """
        Is a valid interpolation edge.

        :param node: the node to consume
        :type node: ValueNode
        :param direction: the direct to go in. Must be in {-1, 1}
        :type direction: int
        :returns: true it can be consumed.
        :rtype: bool
        """
        # kill jumps immediately
        if node.value is None:
            return False
        if len(self.nodes) == 0:
            new_val = self._begin if direction == 1 else self._end
            if self._type == Shortcuts.LOG_INTERPOLATE:
                new_val = 10**new_val
        else:
            edge = self.nodes[-1] if direction == 1 else self.nodes[0]
            edge = edge.value
            if self._type == Shortcuts.LOG_INTERPOLATE:
                edge = math.log(edge, 10)
                new_val = 10 ** (edge + direction * self._spacing)
            else:
                new_val = edge + direction * self._spacing
        return math.isclose(new_val, node.value, rel_tol=rel_tol, abs_tol=abs_tol)

    def consume_edge_node(self, node, direction, last_edge_shortcut=False):
        """
        Tries to consume the given edge.

        If it can be consumed the node is appended to the internal nodes.

        :param node: the node to consume
        :type node: ValueNode
        :param direction: the direct to go in. Must be in {-1, 1}
        :type direction: int
        :param last_edge_shortcut: Whether or the previous node in the list was
            part of a different shortcut
        :type last_edge_shortcut: bool
        :returns: True if the node was consumed.
        :rtype: bool
        """
        if self._can_consume_node(node, direction, last_edge_shortcut):
            if direction == 1:
                self._nodes.append(node)
            else:
                self._nodes.appendleft(node)
            return True
        return False

    def format(self, leading_node=None):
        if self._type == Shortcuts.JUMP:
            temp = self._format_jump()
        # repeat
        elif self._type == Shortcuts.REPEAT:
            temp = self._format_repeat(leading_node)
        # multiply
        elif self._type == Shortcuts.MULTIPLY:
            temp = self._format_multiply(leading_node)
        # interpolate
        elif self._type in {Shortcuts.INTERPOLATE, Shortcuts.LOG_INTERPOLATE}:
            temp = self._format_interpolate(leading_node)
        if self.end_padding:
            pad_str = self.end_padding.format()
        else:
            pad_str = ""
        return f"{temp}{pad_str}"

    def _format_jump(self):
        num_jumps = len(self.nodes)
        if num_jumps == 0:
            return ""
        if len(self._original) > 0 and "j" in self._original[0]:
            j = "j"
        else:
            j = "J"
        length = len(self._original)
        self._num_node.value = num_jumps
        if num_jumps == 1 and (
            length == 0 or (length > 0 and "1" not in self._original[0])
        ):
            num_jumps = ""
        else:
            num_jumps = self._num_node

        return f"{num_jumps.format()}{j}"

    def _can_use_last_node(self, node, start=None):
        """
        Determine if the previous node can be used as the start to this node
        (and therefore skip the start of this one).

        Last node can be used if
        - it's a basic ValueNode that matches this repeat
        - it's also a shortcut, with the same edge values.

        :param node: the previous node to test.
        :type node: ValueNode, ShortcutNode
        :param start: the starting value for this node (specifically for interpolation)
        :type start: float
        :returns: True if the node given can be used.
        :rtype: bool
        """
        if isinstance(node, ValueNode):
            value = node.value
        elif isinstance(node, ShortcutNode):
            value = node.nodes[-1].value
        else:
            return False
        if value is None:
            return False
        if start is None:
            start = self.nodes[0].value
        return math.isclose(start, value)

    def _format_repeat(self, leading_node=None):

        if self._can_use_last_node(leading_node):
            first_val = ""
            num_extra = 0
        else:
            first_val = self.nodes[0].format()
            num_extra = 1
        num_repeats = len(self.nodes) - num_extra
        self._num_node.value = num_repeats
        if len(self._original) >= 2 and "r" in self._original[1]:
            r = "r"
        else:
            r = "R"
        if (
            num_repeats == 1
            and len(self._original) >= 2
            and "1" not in self._original[1]
        ):
            num_repeats = ""
        else:
            num_repeats = self._num_node
        return f"{first_val}{num_repeats.format()}{r}"

    def _format_multiply(self, leading_node=None):
        # Multiply doesn't usually consume other nodes
        if leading_node is not None and len(self) == 1:
            first_val = leading_node.nodes[-1]
            first_val_str = ""
        else:
            first_val = self.nodes[0]
            first_val_str = first_val
        if self._original and "m" in self._original[-1]:
            m = "m"
        else:
            m = "M"
        self._num_node.value = self.nodes[-1].value / first_val.value
        return f"{first_val_str.format()}{self._num_node.format()}{m}"

    def _format_interpolate(self, leading_node=None):
        begin = self._begin
        if self.type == Shortcuts.LOG_INTERPOLATE:
            begin = 10**begin
        if self._can_use_last_node(leading_node, begin):
            start = ""
            num_extra_nodes = 1
            if hasattr(self, "_has_pseudo_start"):
                num_extra_nodes += 1
        else:
            start = self.nodes[0]
            num_extra_nodes = 2
        end = self.nodes[-1]
        num_interp = len(self.nodes) - num_extra_nodes
        self._num_node.value = num_interp
        interp = "I"
        can_match = False
        if len(self._original) > 0:
            if match := re.match(r"\d*(\w+)", self._original[1]):
                can_match = True
                interp = match.group(1)
        if not can_match:
            if self._type == Shortcuts.LOG_INTERPOLATE:
                interp = "ILOG"
        if (
            num_interp == 1
            and len(self._original) >= 2
            and "1" not in self._original[1]
        ):
            num_interp = ""
        else:
            num_interp = self._num_node
        if len(self._original) >= 3:
            padding = self._original[2]
        else:
            padding = PaddingNode(" ")
        return f"{start.format()}{num_interp.format()}{interp}{padding.format()}{end.format()}"


class ClassifierNode(SyntaxNodeBase):
    """
    A node to represent the classifier for a :class:`montepy.data_input.DataInput`

    .. versionadded:: 0.2.0
        This was added with the major parser rework.

    e.g., represents ``M4``, ``F104:n,p``, ``IMP:n,e``.
    """

    def __init__(self):
        super().__init__("classifier")
        self._prefix = None
        self._number = None
        self._particles = None
        self._modifier = None
        self._padding = None
        self._nodes = []

    @property
    def prefix(self):
        """
        The prefix for the classifier.

        That is the string that tells what type of input this is.

        E.g.: ``M`` in ``M4`` or ``IMP`` in ``IMP:n``.

        :returns: the prefix
        :rtype: ValueNode
        """
        return self._prefix

    @prefix.setter
    def prefix(self, pref):
        self.append(pref)
        self._prefix = pref

    @property
    def number(self):
        """
        The number if any for the classifier.

        :returns: the number holder for this classifier.
        :rtype: ValueNode
        """
        return self._number

    @number.setter
    def number(self, number):
        self.append(number)
        self._number = number

    @property
    def particles(self):
        """
        The particles if any tied to this classifier.

        :returns: the particles used.
        :rtype: ParticleNode
        """
        return self._particles

    @particles.setter
    def particles(self, part):
        self.append(part)
        self._particles = part

    @property
    def modifier(self):
        """
        The modifier for this classifier if any.

        A modifier is a prefix character that changes the inputs behavior,
        e.g.: ``*`` or ``+``.

        :returns: the modifier
        :rtype: ValueNode
        """
        return self._modifier

    @modifier.setter
    def modifier(self, mod):
        self.append(mod)
        self._modifier = mod

    @property
    def padding(self):
        """
        The padding for this classifier.

        .. Note::
            None of the ValueNodes in this object should have padding.

        :returns: the padding after the classifier.
        :rtype: PaddingNode
        """
        return self._padding

    @padding.setter
    def padding(self, val):
        self.append(val)
        self._padding = val

    def format(self):
        if self.modifier:
            ret = self.modifier.format()
        else:
            ret = ""
        ret += self.prefix.format()
        if self.number:
            ret += self.number.format()
        if self.particles:
            ret += self.particles.format()
        if self.padding:
            ret += self.padding.format()
        return ret

    def __str__(self):
        return self.format()

    def __repr__(self):
        return (
            f"(Classifier: mod: {self.modifier}, prefix: {self.prefix}, "
            f"number: {self.number}, particles: {self.particles},"
            f" padding: {self.padding})"
        )

    @property
    def comments(self):
        if self.padding is not None:
            yield from self.padding.comments
        else:
            yield from []

    def get_trailing_comment(self):
        if self.padding:
            return self.padding.get_trailing_comment()

    def _delete_trailing_comment(self):
        if self.padding:
            self.padding._delete_trailing_comment()

    def flatten(self):
        ret = []
        if self.modifier:
            ret.append(self.modifier)
        ret.append(self.prefix)
        if self.number:
            ret.append(self.number)
        if self.particles:
            ret.append(self.particles)
        if self.padding:
            ret.append(self.padding)
        return ret


class ParametersNode(SyntaxNodeBase):
    """
    A node to hold the parameters, key-value pairs, for this input.

    This behaves like a dictionary and is accessible by their key*

    .. versionadded:: 0.2.0
        This was added with the major parser rework.

    .. Note::
        How to access values.

        The internal dictionary doesn't use the full classifier directly,
        because some parameters should not be both allowed: e.g., ``fill`` and ``*fill``.
        The key is a string that is all lower case, and only uses the classifiers prefix,
        and particles.

        So to access a cell's fill information you would run:

        .. code-block:: python

            parameters["fill"]

        And to access the n,p importance:

        .. code-block:: python

            parameters["imp:n,p"]
    """

    def __init__(self):
        super().__init__("parameters")
        self._nodes = {}

    def append(self, val, is_default=False):
        """
        Append the node to this node.

        This takes a syntax node, which requires the keys:
            ``["classifier", "seperator", "data"]``

        :param val: the parameter to append.
        :type val: SyntaxNode
        :param is_default: whether this parameter was added as a default tree not from the user.
        :type is_default: bool
        """
        classifier = val["classifier"]
        key = (
            classifier.prefix.value
            + (str(classifier.particles) if classifier.particles else "")
        ).lower()
        if key in self._nodes:
            raise RedundantParameterSpecification(key, val)
        if is_default:
            val._is_default = True
        self._nodes[key] = val

    def __str__(self):
        return f"(Parameters, {self.nodes})"

    def __repr__(self):
        return str(self)

    def __getitem__(self, key):
        return self.nodes[key.lower()]

    def __contains__(self, key):
        return key.lower() in self.nodes

    def format(self):
        ret = ""
        for node in self.nodes.values():
            ret += node.format()
        return ret

    def get_trailing_comment(self):
        for node in reversed(self.nodes.values()):
            if hasattr(node, "_is_default"):
                continue
            return node.get_trailing_comment()

    def _delete_trailing_comment(self):
        for node in reversed(self.nodes.values()):
            if hasattr(node, "_is_default"):
                continue
            node._delete_trailing_comment()

    @property
    def comments(self):
        for node in self.nodes.values():
            if isinstance(node, SyntaxNodeBase):
                yield from node.comments

    def flatten(self):
        ret = []
        for node in self.nodes.values():
            if isinstance(node, (ValueNode, PaddingNode)):
                ret.append(node)
            else:
                ret += node.flatten()
        return ret

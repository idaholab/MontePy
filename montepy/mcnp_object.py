# Copyright 2024, Battelle Energy Alliance, LLC All Rights Reserved.
from abc import ABC, abstractmethod
import copy
import itertools as it
from montepy.errors import *
from montepy.constants import (
    BLANK_SPACE_CONTINUE,
    get_max_line_length,
    rel_tol,
    abs_tol,
)
from montepy.input_parser.syntax_node import (
    CommentNode,
    PaddingNode,
    ParametersNode,
    ValueNode,
)
import montepy
import numpy as np
import textwrap
import warnings
import weakref


class MCNP_Object(ABC):
    """
    Abstract class for semantic representations of MCNP inputs.

    .. versionchanged:: 0.2.0
        Generally significant changes for parser rework.
        For init removed ``comments``, and added ``parser`` as arguments.

    :param input: The Input syntax object this will wrap and parse.
    :type input: Input
    :param parser: The parser object to parse the input with.
    :type parser: MCNP_Lexer
    """

    def __init__(self, input, parser):
        self._problem_ref = None
        self._parameters = ParametersNode()
        self._input = None
        if input:
            if not isinstance(input, montepy.input_parser.mcnp_input.Input):
                raise TypeError("input must be an Input")
            try:
                try:
                    parser.restart()
                # raised if restarted without ever parsing
                except AttributeError as e:
                    pass
                self._tree = parser.parse(input.tokenize(), input)
                self._input = input
            except ValueError as e:
                raise MalformedInputError(
                    input, f"Error parsing object of type: {type(self)}: {e.args[0]}"
                )
            if self._tree is None:
                raise ParsingError(
                    input,
                    "",
                    parser.log.clear_queue(),
                )
            if "parameters" in self._tree:
                self._parameters = self._tree["parameters"]

    def __setattr__(self, key, value):
        # handle properties first
        if hasattr(type(self), key):
            descriptor = getattr(type(self), key)
            if isinstance(descriptor, property):
                descriptor.__set__(self, value)
                return
        # handle _private second
        if key.startswith("_"):
            self.__dict__[key] = value
        else:
            raise AttributeError(
                f"'{type(self).__name__}' object has no attribute '{key}'",
                obj=self,
                name=key,
            )

    @staticmethod
    def _generate_default_node(value_type, default, padding=" "):
        """
        Generates a "default" or blank ValueNode.

        None is generally a safe default value to provide.

        .. versionadded:: 0.2.0

        :param value_type: the data type for the ValueNode.
        :type value_type: Class
        :param default: the default value to provide (type needs to agree with value_type)
        :type default: value_type
        :param padding: the string to provide to the PaddingNode. If None no PaddingNode will be added.
        :type padding: str, None
        :returns: a new ValueNode with the requested information.
        :rtype: ValueNode
        """
        if padding:
            padding_node = PaddingNode(padding)
        else:
            padding_node = None
        if default is None or isinstance(default, montepy.input_parser.mcnp_input.Jump):
            return ValueNode(default, value_type, padding_node)
        return ValueNode(str(default), value_type, padding_node)

    @property
    def parameters(self):
        """
        A dictionary of the additional parameters for the object.

        e.g.: ``1 0 -1 u=1 imp:n=0.5`` has the parameters
        ``{"U": "1", "IMP:N": "0.5"}``

        :returns: a dictionary of the key-value pairs of the parameters.
        :rytpe: dict
        """
        return self._parameters

    @abstractmethod
    def _update_values(self):
        """
        Method to update values in syntax tree with new values.

        Generally when :func:`~montepy.utilities.make_prop_val_node` this is not necessary to do,
        but when :func:`~montepy.utilities.make_prop_pointer` is used it is necessary.
        The most common need is to update a value based on the number for an object pointed at,
        e.g., the material number in a cell definition.

        .. versionadded:: 0.2.0

        """
        pass

    def format_for_mcnp_input(self, mcnp_version):
        """
        Creates a string representation of this MCNP_Object that can be
        written to file.

        :param mcnp_version: The tuple for the MCNP version that must be exported to.
        :type mcnp_version: tuple
        :return: a list of strings for the lines that this input will occupy.
        :rtype: list
        """
        self.validate()
        self._update_values()
        self._tree.check_for_graveyard_comments()
        lines = self.wrap_string_for_mcnp(self._tree.format(), mcnp_version, True)
        return lines

    @property
    def comments(self):
        """
        The comments associated with this input if any.

        This includes all ``C`` comments before this card that aren't part of another card,
        and any comments that are inside this card.

        :returns: a list of the comments associated with this comment.
        :rtype: list
        """
        return list(self._tree.comments)

    @property
    def leading_comments(self):
        """
        Any comments that come before the beginning of the input proper.

        .. versionadded:: 0.2.0

        :returns: the leading comments.
        :rtype: list
        """
        return list(self._tree["start_pad"].comments)

    @leading_comments.setter
    def leading_comments(self, comments):
        if not isinstance(comments, (list, tuple, CommentNode)):
            raise TypeError(
                f"Comments must be a CommentNode, or a list of Comments. {comments} given."
            )
        if isinstance(comments, CommentNode):
            comments = [comments]
        for i, comment in enumerate(comments):
            if not isinstance(comment, CommentNode):
                raise TypeError(
                    f"Comment must be a CommentNode. {comment} given at index {i}."
                )
        new_nodes = list(*zip(comments, it.cycle(["\n"])))
        if self._tree["start_pad"] is None:
            self._tree["start_pad"] = syntax_node.PaddingNode(" ")
        self._tree["start_pad"]._nodes = new_nodes

    @leading_comments.deleter
    def leading_comments(self):
        self._tree["start_pad"]._delete_trailing_comment()

    @staticmethod
    def wrap_string_for_mcnp(string, mcnp_version, is_first_line):
        """
        Wraps the list of the words to be a well formed MCNP input.

        multi-line inputs will be handled by using the indentation format,
        and not the "&" method.

        :param string: A long string with new lines in it,
                    that needs to be chunked appropriately for MCNP inputs
        :type string: str
        :param mcnp_version: the tuple for the MCNP that must be formatted for.
        :type mcnp_version: tuple
        :param is_first_line: If true this will be the beginning of an MCNP input.
                             The first line will not be indented.
        :type is_first_line: bool
        :returns: A list of strings that can be written to an input file, one item to a line.
        :rtype: list
        """
        line_length = get_max_line_length(mcnp_version)
        indent_length = BLANK_SPACE_CONTINUE
        strings = string.splitlines()
        if is_first_line:
            initial_indent = 0
        else:
            initial_indent = indent_length
        wrapper = textwrap.TextWrapper(
            width=line_length,
            initial_indent=" " * initial_indent,
            subsequent_indent=" " * indent_length,
            drop_whitespace=False,
        )
        ret = []
        for line in strings:
            buffer = wrapper.wrap(line)
            if len(buffer) > 1:
                warning = LineExpansionWarning(
                    f"The line exceeded the maximum length allowed by MCNP, and was split. The line was:\n{line}"
                )
                warning.cause = "line"
                warning.og_value = line
                warning.new_value = buffer
                warnings.warn(
                    warning,
                    LineExpansionWarning,
                    stacklevel=2,
                )
            ret += buffer
        return ret

    def validate(self):
        """
        Validates that the object is in a usable state.

        :raises: IllegalState if any condition exists that make the object incomplete.
        """
        pass

    def link_to_problem(self, problem):
        """Links the input to the parent problem for this input.

        This is done so that inputs can find links to other objects.

        :param problem: The problem to link this input to.
        :type problem: MCNP_Problem
        """
        if not isinstance(problem, (montepy.mcnp_problem.MCNP_Problem, type(None))):
            raise TypeError("problem must be an MCNP_Problem")
        if problem is None:
            self._problem_ref = None
        else:
            self._problem_ref = weakref.ref(problem)

    @property
    def _problem(self):
        if self._problem_ref is not None:
            return self._problem_ref()
        return None

    @_problem.setter
    def _problem(self, problem):
        if problem is None:
            self._problem_ref = None
            return
        self.link_to_problem(problem)

    @property
    def trailing_comment(self):
        """
        The trailing comments and padding of an input.

        Generally this will be blank as these will be moved to be a leading comment for the next input.

        :returns: the trailing ``c`` style comments and intermixed padding (e.g., new lines)
        :rtype: list
        """
        return self._tree.get_trailing_comment()

    def _delete_trailing_comment(self):
        self._tree._delete_trailing_comment()

    def _grab_beginning_comment(self, padding):
        if padding:
            self._tree["start_pad"]._grab_beginning_comment(padding)

    def __getstate__(self):
        state = self.__dict__.copy()
        weakref_key = "_problem_ref"
        if weakref_key in state:
            del state[weakref_key]
        return state

    def __setstate__(self, crunchy_data):
        crunchy_data["_problem_ref"] = None
        self.__dict__.update(crunchy_data)

    def clone(self):
        """
        Create a new independent instance of this object.

        :returns: a new instance identical to this object.
        :rtype: type(self)
        """
        return copy.deepcopy(self)

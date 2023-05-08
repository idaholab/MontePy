from abc import ABC, abstractmethod
import itertools as it
from mcnpy.errors import *
from mcnpy.constants import BLANK_SPACE_CONTINUE, get_max_line_length, rel_tol, abs_tol
from mcnpy.input_parser.syntax_node import (
    CommentNode,
    PaddingNode,
    ParametersNode,
    ValueNode,
)
import mcnpy
import numpy as np
import textwrap


class MCNP_Object(ABC):
    """
    Abstract class for semantic representations of MCNP inputs.

    :param input: The Input syntax object this will wrap and parse.
    :type input: Input
    :param parser: The parser object to parse the input with.
    :type parser: MCNP_Lexer
    """

    def __init__(self, input, parser):
        self._problem = None
        self._parameters = ParametersNode()
        if input:
            if not isinstance(input, mcnpy.input_parser.mcnp_input.Input):
                raise TypeError("input must be an Input")
            try:
                self._tree = parser.parse(input.tokenize())
            except ValueError as e:
                raise ValueError(
                    f"Error parsing object of type: {type(self)}: {e.args[0]}"
                )
            if self._tree is None:
                raise MalformedInputError(
                    input, "There is a syntax error with the input."
                )
            if "parameters" in self._tree:
                self._parameters = self._tree["parameters"]
        else:
            self._input_lines = []
            self._mutated = True

    @staticmethod
    def _generate_default_node(value_type, default, padding=" "):
        if padding:
            padding_node = PaddingNode(padding)
        else:
            padding_node = None
        if default is None or isinstance(default, mcnpy.input_parser.mcnp_input.Jump):
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
        return self.wrap_string_for_mcnp(self._tree.format(), mcnp_version, True)

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
        """ """
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
    def leading_comments(self, comments):
        self._tree["start_pad"] = None

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
            if line.strip():
                ret += wrapper.wrap(line)
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
        if not isinstance(problem, mcnpy.mcnp_problem.MCNP_Problem):
            raise TypeError("problem must be an MCNP_Problem")
        self._problem = problem

    @property
    def trailing_comment(self):
        return self._tree.get_trailing_comment()

    def _delete_trailing_comment(self):
        self._tree._delete_trailing_comment()

    def _grab_beginning_comment(self, padding):
        if padding:
            self._tree["start_pad"]._grab_beginning_comment(padding)

from abc import ABC, abstractmethod
from mcnpy.errors import *
from mcnpy.input_parser.constants import BLANK_SPACE_CONTINUE, get_max_line_length
from mcnpy.input_parser.syntax_node import PaddingNode, ParametersNode, ValueNode
import mcnpy
import numpy as np
import textwrap


class MCNP_Object(ABC):
    """
    Abstract class for semantic representations of MCNP inputs.

    :param input: The Input syntax object this will wrap and parse.
    :type input: Input
    :param comments: The Comments that proceeded this input or were inside of this if any
    :type Comments: list
    """

    def __init__(self, input, parser, comments=None):
        self._problem = None
        self._parameters = ParametersNode()
        if input:
            if not isinstance(input, mcnpy.input_parser.mcnp_input.Input):
                raise TypeError("input must be an Input")
            self._input_lines = input.input_lines
            self._tree = parser.parse(input.tokenize())
            if self._tree is None:
                raise MalformedInputError(
                    input, "There is a syntax error with the input."
                )
            if "parameters" in self._tree:
                self._parameters = self._tree["parameters"]
        else:
            self._input_lines = []
            self._mutated = True
        if comments:
            self._comments = comments
        else:
            self._comments = []

    @staticmethod
    def _generate_default_node(value_type, default, padding=" "):
        if padding:
            padding_node = PaddingNode(padding)
        else:
            padding_node = None
        if default is None:
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
        return self._comments

    @comments.setter
    def comments(self, comments):
        if not isinstance(comments, list):
            raise TypeError("comments must be a list")
        for comment in comments:
            if not isinstance(comment, Comment):
                raise TypeError(f"Element {comment} in comments is not a Comment")
        self._mutated = True
        self._comments = comments

    @comments.deleter
    def comments(self):
        self._comment = []

    @property
    def input_lines(self):
        """The raw input lines read from the input file

        :rtype: list
        """
        return self._input_lines

    @property
    @abstractmethod
    def allowed_keywords(self):
        """
        The allowed keywords for this class of MCNP_Object.

        The allowed keywords that would appear in the parameters block.
        For instance for cells the keywords ``IMP`` and ``VOL`` are allowed.
        The allowed keywords need to be in upper case.

        :returns: A set of the allowed keywords. If there are none this should return the empty set.
        :rtype: set
        """
        pass

    @staticmethod
    def wrap_words_for_mcnp(words, mcnp_version, is_first_line):
        """
        Wraps the list of the words to be a well formed MCNP input.

        multi-line inputs will be handled by using the indentation format,
        and not the "&" method.

        :param words: A list of the "words" or data-grams that needed to added to this input.
                      Each word will be separated by at least one space.
        :type words: list
        :param mcnp_version: the tuple for the MCNP that must be formatted for.
        :type mcnp_version: tuple
        :param is_first_line: If true this will be the beginning of an MCNP Input.
                             The first line will not be indented.
        :type is_first_line: bool
        :returns: A list of strings that can be written to an input file, one item to a line.
        :rtype: list
        """
        string = " ".join(words)
        return MCNP_Object.wrap_string_for_mcnp(string, mcnp_version, is_first_line)

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
        )
        ret = []
        for line in strings:
            ret += wrapper.wrap(line)
        return ret

    @staticmethod
    def compress_repeat_values(values, threshold=1e-6):
        """
        Takes a list of floats, and tries to compress it using repeats.

        E.g., 1 1 1 1 would compress to 1 3R

        :param values: a list of float values to try to compress
        :type values: list
        :param threshold: the minimum threshold to consider two values different
        :type threshold: float
        :returns: a list of MCNP word strings that have repeat compression
        :rtype: list
        """
        ret = []
        last_value = None
        float_formatter = "{:n}"
        repeat_counter = 0

        def flush_repeats():
            nonlocal repeat_counter, ret
            if repeat_counter >= 2:
                ret.append(f"{repeat_counter}R")
            elif repeat_counter == 1:
                ret.append(float_formatter.format(last_value))
            repeat_counter = 0

        for value in values:
            if isinstance(value, mcnpy.input_parser.mcnp_input.Jump):
                ret.append(value)
                last_value = None
            elif last_value:
                if np.isclose(value, last_value, atol=threshold):
                    repeat_counter += 1
                else:
                    flush_repeats()
                    ret.append(float_formatter.format(value))
                    last_value = value
            else:
                ret.append(float_formatter.format(value))
                last_value = value
                repeat_counter = 0
        flush_repeats()
        return ret

    @staticmethod
    def compress_jump_values(values):
        """
        Takes a list of strings and jump values and combines repeated jump values.

        e.g., 1 1 J J 3 J becomes 1 1 2J 3 J

        :param values: a list of string and Jump values to try to compress
        :type values: list
        :returns: a list of MCNP word strings that have jump compression
        :rtype: list
        """
        ret = []
        jump_counter = 0

        def flush_jumps():
            nonlocal jump_counter, ret
            if jump_counter == 1:
                ret.append("J")
            elif jump_counter >= 1:
                ret.append(f"{jump_counter}J")
            jump_counter = 0

        for value in values:
            if isinstance(value, mcnpy.input_parser.mcnp_input.Jump):
                jump_counter += 1
            else:
                flush_jumps()
                ret.append(value)
        flush_jumps()
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
            self._tree["start_pad"].grab_beginning_comment(padding)

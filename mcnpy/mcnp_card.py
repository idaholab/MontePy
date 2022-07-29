from abc import ABC, abstractmethod
from mcnpy.input_parser.constants import BLANK_SPACE_CONTINUE, get_max_line_length
from mcnpy.input_parser.mcnp_input import Comment
import mcnpy
import numpy as np
import textwrap


class MCNP_Card(ABC):
    """
    Abstract class for semantic representations of MCNP input cards.
    """

    def __init__(self, input_card, comments=None):
        """
        :param input_card: The Card syntax object this will wrap and parse.
        :type input_card: Card
        :param comments: The Comments that proceeded this card or were inside of this if any
        :type Comments: list
        """
        self._problem = None
        self._parameters = {}
        if input_card:
            if not isinstance(input_card, mcnpy.input_parser.mcnp_input.Card):
                raise TypeError("input_card must be a Card")
            if not isinstance(comments, (list, Comment, type(None))):
                raise TypeError("comments must be either a Comment, a list, or None")
            self._words = input_card.words
            self._parse_key_value_pairs()
            if isinstance(comments, list):
                for comment in comments:
                    if not isinstance(comment, Comment):
                        raise TypeError(
                            f"object {comment} in comments is not a Comment"
                        )
            elif isinstance(comments, Comment):
                comments = [comments]
            self._input_lines = input_card.input_lines
            self._mutated = False
        else:
            self._input_lines = []
            self._mutated = True
        if comments:
            self._comments = comments
        else:
            self._comments = []

    def _parse_key_value_pairs(self):
        if self.allowed_keywords:
            for i, word in enumerate(self.words):
                if any([char.isalpha() for char in word]):
                    break
            fragments = []
            for word in self.words[i:]:
                fragments.extend(word.split("="))
            # cut out these words from further parsing
            self._words = self.words[:i]
            key = ""
            value = []

            def flush_pair(key, value):
                self._parameters[key.upper()] = " ".join(value)

            for i, fragment in enumerate(fragments):
                keyword = fragment.split(":")[0].upper()
                if keyword in self.allowed_keywords:
                    if i != 0:
                        flush_pair(key, value)
                        value = []
                    key = fragment
                else:
                    value.append(fragment)
                if i == len(fragments) - 1:
                    if key and value:
                        flush_pair(key, value)

    @property
    def parameters(self):
        """
        A dictionary of the additional parameters for the cell.

        e.g.: Universes, and imp:n
        """
        return self._parameters

    @abstractmethod
    def format_for_mcnp_input(self, mcnp_version):
        """
        Creates a string representation of this card that can be
        written to file.

        :param mcnp_version: The tuple for the MCNP version that must be exported to.
        :type mcnp_version: tuple
        :return: a list of strings for the lines that this card will occupy.
        :rtype: list
        """
        ret = []
        if self.comments:
            if not self.mutated:
                ret += self.comments[0].format_for_mcnp_input(mcnp_version)
            else:
                for comment in self.comments:
                    ret += comment.format_for_mcnp_input(mcnp_version)
        return ret

    def _format_for_mcnp_unmutated(self, mcnp_version):
        """
        Creates a string representation of this card that can be
        written to file when the card did not mutate.

        TODO add to developer's guide.

        :param mcnp_version: The tuple for the MCNP version that must be exported to.
        :type mcnp_version: tuple
        :return: a list of strings for the lines that this card will occupy.
        :rtype: list
        """
        ret = []
        comments_dict = {}
        if self.comments:
            for comment in self.comments:
                if comment.is_cutting_comment:
                    comments_dict[comment.card_line] = comment
            ret += self.comments[0].format_for_mcnp_input(mcnp_version)
        for i, line in enumerate(self.input_lines):
            if i in comments_dict:
                ret += comments_dict[i].format_for_mcnp_input(mcnp_version)
            ret.append(line)
        return ret

    @property
    def comments(self):
        """
        The preceding comment block to this card if any.

        :rtype: Comment
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
    def mutated(self):
        """True if the user has changed a property of this card

        :rtype: bool
        """
        return self._mutated

    @property
    @abstractmethod
    def allowed_keywords(self):
        """
        The allowed keywords for this class of MCNP_Card.

        The allowed keywords need to be in upper case.

        :returns: A set of the allowed keywords. If there are none this should return the empty set.
        :rtype: set
        """
        pass

    @staticmethod
    def wrap_words_for_mcnp(words, mcnp_version, is_first_line):
        """
        Wraps the list of the words to be a well formed MCNP input.

        multi-line cards will be handled by using the indentation format,
        and not the "&" method.

        :param words: A list of the "words" or data-grams that needed to added to this card.
                      Each word will be separated by at least one space.
        :type words: list
        :param mcnp_version: the tuple for the MCNP that must be formatted for.
        :type mcnp_version: tuple
        :param is_first_line: If true this will be the beginning of an MCNP card.
                             The first line will not be indented.
        :type is_first_line: bool
        :returns: A list of strings that can be written to an input file, one item to a line.
        :rtype: list
        """
        string = " ".join(words)
        return MCNP_Card.wrap_string_for_mcnp(string, mcnp_version, is_first_line)

    @staticmethod
    def wrap_string_for_mcnp(string, mcnp_version, is_first_line):
        """
        Wraps the list of the words to be a well formed MCNP input.

        multi-line cards will be handled by using the indentation format,
        and not the "&" method.

        :param string: A long string that needs to be chunked appropriately for MCNP inputs
        :type string: str
        :param mcnp_version: the tuple for the MCNP that must be formatted for.
        :type mcnp_version: tuple
        :param is_first_line: If true this will be the beginning of an MCNP card.
                             The first line will not be indented.
        :type is_first_line: bool
        :returns: A list of strings that can be written to an input file, one item to a line.
        :rtype: list
        """
        line_length = get_max_line_length(mcnp_version)
        indent_length = BLANK_SPACE_CONTINUE
        if is_first_line:
            initial_indent = 0
        else:
            initial_indent = indent_length
        wrapper = textwrap.TextWrapper(
            width=line_length,
            initial_indent=" " * initial_indent,
            subsequent_indent=" " * indent_length,
        )
        return wrapper.wrap(string)

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
        for value in values:
            if last_value:
                if np.isclose(value, last_value, atol=threshold):
                    repeat_counter += 1
                else:
                    if repeat_counter >= 2:
                        ret.append(f"{repeat_counter}R")
                        repeat_counter = 0
                    elif repeat_counter == 1:
                        ret.append(float_formatter.format(last_value))
                    ret.append(float_formatter.format(value))
                    last_value = value
            else:
                ret.append(float_formatter.format(value))
                last_value = value
                repeat_counter = 0

        return ret

    @staticmethod
    def compress_jump_values(values):
        """
        Takes a list of strings and jump values and combines repeated jump values.

        e.g., 1 1 J J 3 J becomes 11 2J 3 J
        :param values: a list of string and Jump values to try to compress
        :type values: list
        :returns: a list of MCNP word strings that have repeat compression
        :rtype: list
        """
        ret = []
        jump_counter = 0
        for value in values:
            if isinstance(value, mcnpy.input_parser.mcnp_input.Jump):
                jump_counter += 1
            else:
                if jump_counter == 1:
                    ret.append("J")
                elif jump_counter >= 1:
                    ret.append(f"{jump_counter}J")
                jump_counter = 0
                ret.append(value)
        return ret

    @property
    def words(self):
        """
        The words from the input file for this card.

        """
        return self._words

    def link_to_problem(self, problem):
        """Links the card to the parent problem for this card.

        This is done so that cards can find links to other objects.

        :param problem: The problem to link this card to.
        :type type: MCNP_Problem
        """
        if not isinstance(problem, mcnpy.mcnp_problem.MCNP_Problem):
            raise TypeError("problem must be an MCNP_Problem")
        self._problem = problem

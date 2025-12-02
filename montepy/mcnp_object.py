# Copyright 2024-2025, Battelle Energy Alliance, LLC All Rights Reserved.
from __future__ import annotations
from abc import ABC, ABCMeta, abstractmethod
import copy
import itertools as it
import re
import textwrap
import warnings
import weakref

from montepy.exceptions import *
from montepy.constants import (
    BLANK_SPACE_CONTINUE,
    COMMENT_FINDER,
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
from montepy.input_parser.mcnp_input import Input
from montepy.utilities import *

# must be last for circular imports
import montepy
from montepy._exception_context import _ExceptionContextAdder
from montepy.utilities import *
import montepy.types as ty

InitInput = montepy.input_parser.mcnp_input.Input | str


class MCNP_Object(ABC, metaclass=_ExceptionContextAdder):
    """Abstract class for semantic representations of MCNP inputs.

    .. versionchanged:: 1.2.0
        * Removed parser as an argument (now an abstract property)
        * Added jit_parse argument

    Parameters
    ----------
    input : Input | str
        The Input syntax object this will wrap and parse.
    jit_parse : bool
        Parse the object just-in-time, when the information is actually needed, if True.
    """

    def __init__(self, input: InitInput, *, jit_parse: bool = True, **kwargs):
        try:
            self._BLOCK_TYPE
        except AttributeError:
            self._BLOCK_TYPE = montepy.input_parser.block_type.BlockType.DATA
        self._problem_ref = None
        self._parameters = ParametersNode()
        self._input = None
        self._init_blank()
        if input:
            self._parse_input(input, jit_parse)
            if jit_parse:
                return
        else:
            self._generate_default_tree(**kwargs)
        self._parse_tree()

    def _parse_input(self, input, jit_parse):
        if isinstance(input, str):
            input = montepy.input_parser.mcnp_input.Input(
                input.split("\n"), self._BLOCK_TYPE
            )
        if jit_parse:
            try:
                return self._jit_light_init(input)
            # fall back to full parsing on any errors
            except Exception:
                jit_parse = False
        parser = self._parser()
        try:
            try:
                parser.restart()
            # raised if restarted without ever parsing
            except AttributeError as e:
                pass
            tokenizer = input.tokenize()
            self._tree = parser.parse(tokenizer, input)
            # consume token stream
            tokenizer.close()
            self._input = input
        except ValueError as e:
            if isinstance(e, UnsupportedFeature):
                raise e
            raise MalformedInputError(
                input, f"Error parsing object of type: {type(self)}: {e.args[0]}"
            ).with_traceback(e.__traceback__)
        if self._tree is None:
            raise ParsingError(
                input,
                "",
                parser.log.clear_queue(),
            )
        if "parameters" in self._tree:
            self._parameters = self._tree["parameters"]

    @staticmethod
    @abstractmethod
    def _parser():
        pass

    @abstractmethod
    def _init_blank(self):
        pass

    @abstractmethod
    def _parse_tree(self):
        pass

    @abstractmethod
    def _generate_default_tree(self, **kwargs):
        pass

    def __setattr__(self, key, value):
        # handle properties first
        if hasattr(type(self), key):
            descriptor = getattr(type(self), key)
            if isinstance(descriptor, property):
                descriptor.__set__(self, value)
                return
        # handle _private second
        if key.startswith("_"):
            super().__setattr__(key, value)
        else:
            raise AttributeError(
                f"'{type(self).__name__}' object has no attribute '{key}'",
                obj=self,
                name=key,
            )

    def _jit_light_init(self, input: Input):
        self._not_parsed = True
        self._input = input
        parser = self._JitParser()
        tokenizer = input.tokenize()
        bare_tree = parser.parse(tokenizer)
        tokenizer.close()
        for key, node in bare_tree.nodes.items():
            setattr(self, f"_{key}", node)
        self._tree = bare_tree
        return self

    _KEYS_TO_PRESERVE = set()

    def full_parse(self):
        # TODO deprecate update_pointers
        # TODO test for catastrophic surface, material, transform renumbering
        # TODO update str and repr to be jit safe
        # TODO update push to cell method
        # TODO handle material-thermal linking
        if hasattr(self, "_not_parsed") and self._not_parsed:
            del self._not_parsed
            problem = self._problem
            old_data = {k: getattr(self, k) for k in self._KEYS_TO_PRESERVE}
            self.__init__(self._input, jit_parse=False)
            [setattr(self, k, v) for k, v in old_data.items()]
            if problem:
                self.link_to_problem(problem)

    def search(self, search: str | re.Pattern) -> bool:
        """
        Searches this input for the given string, or compiled regular expression.

        Parameters
        ----------
        search : str | re.Pattern
            The pattern to search for.

        Returns
        -------
        bool
            Whether this
        """
        if self._input is None:
            return
        return self._input.search(search)

    @staticmethod
    def _generate_default_node(
        value_type: type, default: str, padding: str = " ", never_pad: bool = False
    ):
        """Generates a "default" or blank ValueNode.

        None is generally a safe default value to provide.

        .. versionchanged:: 1.0.0
            Added ``never_pad`` argument.

        Parameters
        ----------
        value_type : Class
            the data type for the ValueNode.
        default : value_type
            the default value to provide (type needs to agree with
            value_type)
        padding : str, None
            the string to provide to the PaddingNode. If None no
            PaddingNode will be added.
        never_pad: bool
            Whether to never add trailing padding. True means extra padding is suppressed.

        Returns
        -------
        ValueNode
            a new ValueNode with the requested information.
        """
        if padding:
            padding_node = PaddingNode(padding)
        else:
            padding_node = None
        if default is None or isinstance(default, montepy.input_parser.mcnp_input.Jump):
            return ValueNode(default, value_type, padding_node, never_pad)
        return ValueNode(str(default), value_type, padding_node, never_pad)

    @property
    @needs_full_ast
    def parameters(self) -> dict[str, str]:
        """A dictionary of the additional parameters for the object.

        e.g.: ``1 0 -1 u=1 imp:n=0.5`` has the parameters
        ``{"U": "1", "IMP:N": "0.5"}``

        Returns
        -------
        unknown
            a dictionary of the key-value pairs of the parameters.


        :rytpe: dict
        """
        return self._parameters

    @needs_full_ast
    @abstractmethod
    def _update_values(self):
        """Method to update values in syntax tree with new values.

        Generally when :func:`~montepy.utilities.make_prop_val_node` this is not necessary to do,
        but when :func:`~montepy.utilities.make_prop_pointer` is used it is necessary.
        The most common need is to update a value based on the number for an object pointed at,
        e.g., the material number in a cell definition.

        """
        pass

    @args_checked
    def format_for_mcnp_input(self, mcnp_version: ty.VersionType) -> list[str]:
        """Creates a list of strings representing this MCNP_Object that can be
        written to file.

        Parameters
        ----------
        mcnp_version : ty.VersionType
            The tuple for the MCNP version that must be exported to.

        Returns
        -------
        list
            a list of strings for the lines that this input will occupy.
        """
        if hasattr(self, "_not_parsed"):
            return self._input.input_lines
        self.validate()
        self._update_values()
        self._tree.check_for_graveyard_comments()
        message = None
        with warnings.catch_warnings(record=True) as ws:
            lines = self.wrap_string_for_mcnp(self._tree.format(), mcnp_version, True)
        self._flush_line_expansion_warning(lines, ws)
        return lines

    @args_checked
    def mcnp_str(self, mcnp_version: ty.VersionType = None) -> str:
        """Returns a string of this input as it would appear in an MCNP input file.

        ..versionadded:: 1.0.0

        Parameters
        ----------
        mcnp_version: ty.VersionType
            The tuple for the MCNP version that must be exported to.

        Returns
        -------
        str
            The string that would have been printed in a file
        """
        if mcnp_version is None:
            if self._problem is not None:
                mcnp_version = self._problem.mcnp_version
            else:
                mcnp_version = montepy.MCNP_VERSION
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            return "\n".join(self.format_for_mcnp_input(mcnp_version))

    def _flush_line_expansion_warning(self, lines, ws):
        if not ws:
            return
        message = f"""The input had a value expand that may change formatting.
The new input was:\n\n"""
        for line in lines:
            message += f"    {line}"
        width = 15
        message += f"\n\n    {'old value': ^{width}s} {'new value': ^{width}s}"
        message += f"\n    {'':-^{width}s} {'':-^{width}s}\n"
        olds = []
        news = []
        for w in ws:
            warning = w.message
            formatter = f"    {{w.og_value: >{width}}} {{w.new_value: >{width}}}\n"
            message += formatter.format(w=warning)
            olds.append(warning.og_value)
            news.append(warning.new_value)
        if message is not None:
            warning = LineExpansionWarning(message)
            warning.olds = olds
            warning.news = news
            warnings.warn(warning, stacklevel=4)

    @property
    @needs_full_ast
    def comments(self) -> list[PaddingNode]:
        """The comments associated with this input if any.

        This includes all ``C`` comments before this card that aren't part of another card,
        and any comments that are inside this card.

        Returns
        -------
        list
            a list of the comments associated with this comment.
        """
        return list(self._tree.comments)

    @property
    @needs_full_ast
    def leading_comments(self) -> list[PaddingNode]:
        """Any comments that come before the beginning of the input proper.

        Returns
        -------
        list
            the leading comments.
        """
        possible_comments = list(self._tree["start_pad"].comments)
        if (
            not possible_comments
            and not hasattr(self, "_grabbed_leading")
            and self._problem
        ):
            leading_comments = self._problem._get_leading_comment(self)
            if leading_comments:
                self._grab_beginning_comment(leading_comments)
                self._grabbed_leading = True
                return self.leading_comments
        return possible_comments

    @leading_comments.setter
    @needs_full_cst
    @args_checked
    def leading_comments(self, comments: ty.Iterable[CommentNode | str] | CommentNode):
        if isinstance(comments, CommentNode):
            comments = [comments]
        new_nodes = list(*zip(comments, it.cycle(["\n"])))
        if self._tree["start_pad"] is None:
            self._tree["start_pad"] = PaddingNode(" ")
        self._tree["start_pad"]._nodes = new_nodes

    @leading_comments.deleter
    @needs_full_cst
    def leading_comments(self):
        self._tree["start_pad"]._delete_trailing_comment()

    @staticmethod
    @args_checked
    def wrap_string_for_mcnp(
        string: str,
        mcnp_version: ty.VersionType,
        is_first_line: bool,
        suppress_blank_end: bool = True,
    ) -> list[str]:
        """Wraps the list of the words to be a well formed MCNP input.

        multi-line inputs will be handled by using the indentation format,
        and not the "&" method.

        Parameters
        ----------
        string : str
            A long string with new lines in it, that needs to be chunked
            appropriately for MCNP inputs
        mcnp_version : tuple
            the tuple for the MCNP that must be formatted for.
        is_first_line : bool
            If true this will be the beginning of an MCNP input. The
            first line will not be indented.
        suppress_blank_end : bool
            Whether or not to suppress any blank lines that would be
            added to the end. Good for anywhere but cell modifiers in
            the cell block.

        Returns
        -------
        list
            A list of strings that can be written to an input file, one
            item to a line.
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
                # don't warn for comments, nor line wrap
                # this order assumes that comment overruns are rare
                if COMMENT_FINDER.match(line):
                    buffer = [line]
                elif "$" in line:
                    parts = line.split("$")
                    buffer = wrapper.wrap(parts[0])
                    buffer[-1] = "$".join([buffer[-1]] + parts[1:])
                else:
                    warning = LineExpansionWarning(
                        f"The line exceeded the maximum length allowed by MCNP, and was split. The line was:\n{line}"
                    )
                    warning.cause = "line"
                    warning.og_value = "1 line"
                    warning.new_value = f"{len(buffer)} lines"
                    warnings.warn(
                        warning,
                        LineExpansionWarning,
                        stacklevel=2,
                    )
            # lazy final guard against extra lines
            if suppress_blank_end:
                buffer = [s for s in buffer if s.strip()]
            ret += buffer
        return ret

    def validate(self):
        """Validates that the object is in a usable state."""
        pass

    @args_checked
    def link_to_problem(self, problem: montepy.mcnp_problem.MCNP_Problem = None):
        """Links the input to the parent problem for this input.

        This is done so that inputs can find links to other objects.

        Parameters
        ----------
        problem : MCNP_Problem
            The problem to link this input to.
        """
        if problem is None:
            self._problem_ref = None
        else:
            self._problem_ref = weakref.ref(problem)

    @property
    def _problem(self) -> montepy.MCNP_Problem:
        if self._problem_ref is not None:
            return self._problem_ref()
        return None

    @_problem.setter
    def _problem(self, problem):
        """
        The problem this object is associated with if any.

        Returns
        -------
        montepy.MCNP_Problem | None
        """
        if problem is None:
            self._problem_ref = None
            return
        self.link_to_problem(problem)

    @property
    @needs_full_ast
    def trailing_comment(self) -> list[PaddingNode]:
        """The trailing comments and padding of an input.

        Generally this will be blank as these will be moved to be a leading comment for the next input.

        Returns
        -------
        list
            the trailing ``c`` style comments and intermixed padding
            (e.g., new lines)
        """
        return self._tree.get_trailing_comment()

    def _delete_trailing_comment(self):
        """
        Deletes trailing comments from an object when it has been moved to another object.
        """
        self._tree._delete_trailing_comment()

    def _grab_beginning_comment(self, padding: list[PaddingNode], last_obj=None):
        if padding:
            self._tree["start_pad"]._grab_beginning_comment(padding)

    def __getstate__(self):
        state = self.__dict__.copy()
        bad_keys = {"_problem_ref", "_parser"}
        for key in bad_keys:
            if key in state:
                del state[key]
        return state

    def __setstate__(self, crunchy_data):
        crunchy_data["_problem_ref"] = None
        self.__dict__.update(crunchy_data)

    def clone(self) -> montepy.mcnp_object.MCNP_Object:
        """Create a new independent instance of this object.

        Returns
        -------
        type(self)
            a new instance identical to this object.
        """
        return copy.deepcopy(self)

    def __str__(self):
        # TODO ensure this doesn't pull attributes on JIT_parsed objects.
        # Switch to hooks system.
        pass

    def __repr__(self):
        pass

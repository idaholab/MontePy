# Copyright 2024-2025, Battelle Energy Alliance, LLC All Rights Reserved.
from __future__ import annotations
from abc import ABC, ABCMeta, abstractmethod
import copy
import functools
import itertools as it
import sys
import textwrap
from typing import Union
import warnings
import weakref

from montepy.errors import *
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

InitInput = Union[Input, str]


class _ExceptionContextAdder(ABCMeta):
    """A metaclass for wrapping all class properties and methods in :func:`~montepy.errors.add_line_number_to_exception`."""

    @staticmethod
    def _wrap_attr_call(func):
        """Wraps the function, and returns the modified function."""

        @functools.wraps(func)
        def wrapped(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                if len(args) > 0 and isinstance(args[0], MCNP_Object):
                    self = args[0]
                    if hasattr(self, "_handling_exception"):
                        raise e
                    self._handling_exception = True
                    try:
                        add_line_number_to_exception(e, self)
                    finally:
                        del self._handling_exception
                else:
                    raise e

        if isinstance(func, staticmethod):
            return staticmethod(wrapped)
        if isinstance(func, classmethod):
            return classmethod(wrapped)
        return wrapped

    def __new__(meta, classname, bases, attributes):
        """This will replace all properties and callable attributes with
        wrapped versions.
        """
        new_attrs = {}
        for key, value in attributes.items():
            new_attrs[key] = value
            continue
            if key.startswith("_"):
                new_attrs[key] = value
            if callable(value):
                new_attrs[key] = _ExceptionContextAdder._wrap_attr_call(value)
            elif isinstance(value, property):
                new_props = {}
                for attr_name in {"fget", "fset", "fdel", "doc"}:
                    try:
                        assert getattr(value, attr_name)
                        new_props[attr_name] = _ExceptionContextAdder._wrap_attr_call(
                            getattr(value, attr_name)
                        )
                    except (AttributeError, AssertionError):
                        new_props[attr_name] = None

                new_attrs[key] = property(**new_props)
            else:
                new_attrs[key] = value
        cls = super().__new__(meta, classname, bases, new_attrs)
        return cls


class MCNP_Object(ABC, metaclass=_ExceptionContextAdder):
    """Abstract class for semantic representations of MCNP inputs.

    Parameters
    ----------
    input : Union[Input, str]
        The Input syntax object this will wrap and parse.
    parser : MCNP_Parser
        The parser object to parse the input with.
    """

    def __init__(
        self,
        input: InitInput,
        parser: montepy.input_parser.parser_base.MCNP_Parser,
    ):
        try:
            self._BLOCK_TYPE
        except AttributeError:
            self._BLOCK_TYPE = montepy.input_parser.block_type.BlockType.DATA
        self._problem_ref = None
        self._parameters = ParametersNode()
        self._input = None
        if input:
            if not isinstance(input, (montepy.input_parser.mcnp_input.Input, str)):
                raise TypeError(f"input must be an Input or str. {input} given.")
            if isinstance(input, str):
                input = montepy.input_parser.mcnp_input.Input(
                    input.split("\n"), self._BLOCK_TYPE
                )
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
            # kwargs added in 3.10
            if sys.version_info >= (3, 10):
                raise AttributeError(
                    f"'{type(self).__name__}' object has no attribute '{key}'",
                    obj=self,
                    name=key,
                )
            raise AttributeError(
                f"'{type(self).__name__}' object has no attribute '{key}'",
            )

    @classmethod
    def _jit_light_init(cls, input: Input):
        instance = cls.__new__(cls)
        instance._not_parsed = True
        instance._input = input
        parser = cls._JitParser()
        tokenizer = input.tokenize()
        bare_tree = parser.parse(tokenizer)
        tokenizer.close()
        for key, node in bare_tree.nodes.items():
            setattr(instance, f"_{key}", node)
        return instance

    def full_parse(self):
        if hasattr(self, "_not_parsed") and self._not_parsed:
            del self._not_parsed
            self.__init__(self._input)
            problem = self._problem
            if problem:
                self.link_to_problem(self._problem)
                args = (problem.cells, problem.surfaces, problem.data_inputs)
                if isinstance(self, montepy.surafaces.Surface):
                    args = args[1:]
                elif isinstance(self, montepy.data_inputs.data_input.DataInputAbstract):
                    args = args[2:]
                self.update_pointers(*args)

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

    @needs_full_tree
    @property
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

    @needs_full_tree
    @abstractmethod
    def _update_values(self):
        """Method to update values in syntax tree with new values.

        Generally when :func:`~montepy.utilities.make_prop_val_node` this is not necessary to do,
        but when :func:`~montepy.utilities.make_prop_pointer` is used it is necessary.
        The most common need is to update a value based on the number for an object pointed at,
        e.g., the material number in a cell definition.

        """
        pass

    def format_for_mcnp_input(self, mcnp_version: tuple[int]) -> list[str]:
        """Creates a list of strings representing this MCNP_Object that can be
        written to file.

        Parameters
        ----------
        mcnp_version : tuple[int]
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

    def mcnp_str(self, mcnp_version: tuple[int] = None):
        """Returns a string of this input as it would appear in an MCNP input file.

        ..versionadded:: 1.0.0

        Parameters
        ----------
        mcnp_version: tuple[int]
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

    @needs_full_tree
    @property
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
    @needs_full_tree
    def leading_comments(self) -> list[PaddingNode]:
        """Any comments that come before the beginning of the input proper.

        Returns
        -------
        list
            the leading comments.
        """
        return list(self._tree["start_pad"].comments)

    @leading_comments.setter
    @needs_full_tree
    def leading_comments(self, comments):
        if not isinstance(comments, (list, tuple, CommentNode)):
            raise TypeError(
                f"Comments must be a CommentNode, or a list of Comments. {comments} given."
            )
        if isinstance(comments, CommentNode):
            comments = [comments]
        if isinstance(comments, (list, tuple)):
            for comment in comments:
                if not isinstance(comment, CommentNode):
                    raise TypeError(
                        f"Comments must be a CommentNode, or a list of Comments. {comment} given."
                    )

        for i, comment in enumerate(comments):
            if not isinstance(comment, CommentNode):
                raise TypeError(
                    f"Comment must be a CommentNode. {comment} given at index {i}."
                )
        new_nodes = list(*zip(comments, it.cycle(["\n"])))
        if self._tree["start_pad"] is None:
            self._tree["start_pad"] = PaddingNode(" ")
        self._tree["start_pad"]._nodes = new_nodes

    @leading_comments.deleter
    @needs_full_tree
    def leading_comments(self):
        self._tree["start_pad"]._delete_trailing_comment()

    @staticmethod
    def wrap_string_for_mcnp(
        string, mcnp_version, is_first_line, suppress_blank_end=True
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

    def link_to_problem(self, problem: montepy.mcnp_problem.MCNP_Problem):
        """Links the input to the parent problem for this input.

        This is done so that inputs can find links to other objects.

        Parameters
        ----------
        problem : MCNP_Problem
            The problem to link this input to.
        """
        if not isinstance(problem, (montepy.mcnp_problem.MCNP_Problem, type(None))):
            raise TypeError("problem must be an MCNP_Problem")
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
        if problem is None:
            self._problem_ref = None
            return
        self.link_to_problem(problem)

    @needs_full_tree
    @property
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

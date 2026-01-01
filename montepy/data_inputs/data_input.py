# Copyright 2024, Battelle Energy Alliance, LLC All Rights Reserved.
from __future__ import annotations
from abc import abstractmethod
import copy
import re

import montepy
from montepy.utilities import *
from montepy.exceptions import *
from montepy.input_parser import syntax_node
from montepy.input_parser.data_parser import (
    ClassifierParser,
    DataParser,
    JitDataParser,
    ParamOnlyDataParser,
)
from montepy.input_parser.mcnp_input import Input
from montepy.input_parser import syntax_node
from montepy.particle import Particle
from montepy.mcnp_object import MCNP_Object, InitInput
import montepy.types as ty


class _ClassifierInput(Input):
    """A specialized subclass that returns only 1 useful token."""

    def tokenize(self):
        """Returns one token after all starting comments and spaces."""
        last_in_comment = True
        for token in super().tokenize():
            if token is None:
                break
            if last_in_comment:
                if token.type not in {"COMMENT", "SPACE"}:
                    last_in_comment = False
            else:
                if token.type == "SPACE":
                    break
            yield token


class DataInputAbstract(MCNP_Object):
    """Parent class to describe all MCNP data inputs.

    Parameters
    ----------
    input : Input | str
        the Input object representing this data input
    fast_parse : bool
        Whether or not to only parse the first word for the type of
        data.
    """

    _parser = DataParser

    _classifier_parser = ClassifierParser

    _JitParser = JitDataParser

    def __init__(
        self, input: InitInput = None, fast_parse=False, *, jit_parse: bool = True
    ):
        if not fast_parse:
            super().__init__(input, jit_parse=jit_parse)
        else:
            self._parse_classifier(input, jit_parse=jit_parse)

    def _parse_classifier(self, input, parsing_func=None, jit_parse=True):
        if input:
            if isinstance(input, str):
                input = _ClassifierInput(
                    input.split("\n"),
                    montepy.input_parser.block_type.BlockType.DATA,
                )
            else:
                input = copy.copy(input)
                input.__class__ = _ClassifierInput
        self._old_parser = self._parser
        self._parser = self._classifier_parser
        if parsing_func is None:
            super().__init__(input, jit_parse=jit_parse)
        else:
            parsing_func(input, jit_parse=jit_parse)
        self._parser = self._old_parser
        del self._old_parser

    def _generate_default_tree(self):
        ret = {}
        ret["start_pad"] = syntax_node.PaddingNode()
        ret["classifier"] = syntax_node.ClassifierNode()
        ret["classifier"].prefix = syntax_node.ValueNode(
            None, str, padding=None, never_pad=True
        )
        ret["keyword"] = syntax_node.ValueNode(None, str, padding=None)
        ret["data"] = syntax_node.ListNode("empty data")
        ret["parameters"] = syntax_node.ParametersNode()
        self._tree = syntax_node.SyntaxNode("blank data tree", ret)

    def _init_blank(self):
        self._particles = None

    def _parse_tree(self):
        self.__split_name(self._input)

    def _jit_light_init(self, input: Input):
        super()._jit_light_init(input)
        classifier = self._classifier
        self._prefix = classifier.prefix.value
        self._input_number = classifier.number
        self._number = self._input_number
        if classifier.particles:
            self._particles = classifier.particles.particles
        self._modifier = classifier.modifier
        self.__enforce_name(input)

    @staticmethod
    @abstractmethod
    def _class_prefix() -> str:
        """The text part of the input identifier.

        For example: for a material the prefix is ``m``

        this must be lower case

        Returns
        -------
        str
            the string of the prefix that identifies a input of this
            class.
        """
        pass

    @staticmethod
    @abstractmethod
    def _has_number() -> bool:
        """Whether or not this class supports numbering.

        For example: ``kcode`` doesn't allow numbers but tallies do allow it e.g., ``f7``

        Returns
        -------
        bool
            True if this class allows numbers
        """
        pass

    @staticmethod
    @abstractmethod
    def _has_classifier() -> ty.PositiveInt:
        """Whether or not this class supports particle classifiers.

        For example: ``kcode`` doesn't allow particle types but tallies do allow it e.g., ``f7:n``

        * 0 : not allowed
        * 1 : is optional
        * 2 : is mandatory

        Returns
        -------
        int
            True if this class particle classifiers
        """
        pass

    @property
    def particle_classifiers(self) -> list[montepy.Particle]:
        """The particle class part of the input identifier as a parsed list.

        This is parsed from the input that was read.

        For example: the classifier for ``F7:n`` is ``:n``, and ``imp:n,p`` is ``:n,p``
        This will be parsed as a list: ``[<Particle.NEUTRON: 'N'>, <Particle.PHOTON: 'P'>]``.

        Returns
        -------
        list[montepy.Particle]
            the particles listed in the input if any. Otherwise None
        """
        if self._particles:
            return self._particles
        return None

    @property
    def prefix(self) -> str:
        """The text part of the input identifier parsed from the input.

        For example: for a material like: ``m20`` the prefix is ``m``.
        this will always be lower case.
        Can also be called the mnemonic.

        Returns
        -------
        str
            The prefix read from the input
        """
        return self._prefix.lower()

    @property
    def prefix_modifier(self) -> str:
        """The modifier to a name prefix that was parsed from the input.

        For example: for a transform: ``*tr5`` the modifier is ``*``

        Returns
        -------
        str
            the prefix modifier that was parsed if any. None if
            otherwise.
        """
        return self._modifier

    @property
    @needs_full_ast
    def data(self) -> syntax_node.ListNode:
        """The syntax tree actually holding the data.

        Returns
        -------
        ListNode
            The syntax tree with the information.
        """
        return self._tree["data"]

    @property
    def classifier(self):
        """The syntax tree object holding the data classifier.

        For example this would container information like ``M4``, or ``F104:n``.

        Returns
        -------
        ClassifierNode
            the classifier for this data_input.
        """
        return self._tree["classifier"]

    def validate(self):
        pass

    def _update_values(self):
        pass

    def update_pointers(self, data_inputs):
        """Connects data inputs to each other

        Parameters
        ----------
        data_inputs : list
            a list of the data inputs in the problem

        Returns
        -------
        bool, None
            True iff this input should be removed from
            ``problem.data_inputs``
        """
        pass

    def __split_name(self, input):
        """Parses the name of the data input as a prefix, number, and a particle classifier.

        This populates the properties:
            prefix
            _input_number
            classifier

        Parameters
        ----------
        input : input
            the input object representing this data input

        Raises
        ------
        MalformedInputError
            if the name is invalid for this DataInput
        """
        self._classifier = self._tree["classifier"]
        try:
            self.__enforce_name(input)
        except MalformedInputError as e:
            if input:
                raise e
        self._input_number = self._classifier.number
        self._prefix = self._classifier._prefix.value
        if self._classifier.particles:
            self._particles = self._classifier.particles.particles
        self._modifier = self._classifier.modifier

    def __enforce_name(self, input):
        """Checks that the name is valid.

        Parameters
        ----------
        input : input
            the input object representing this data input

        Raises
        ------
        MalformedInputError
            if the name is invalid for this DataInput
        """
        classifier = self._classifier
        if self._class_prefix:
            if (
                classifier.prefix.value is None
                or classifier.prefix.value.lower() != self._class_prefix()
            ):
                raise MalformedInputError(
                    input,
                    f"{classifier.format()} has the wrong prefix for {type(self)}",
                )
            if self._has_number():
                try:
                    num = classifier.number.value
                    assert num is not None
                    assert num >= 0
                except (AttributeError, AssertionError) as e:
                    raise MalformedInputError(
                        input,
                        f"{classifier} does not contain a valid number",
                    )
            if not self._has_number() and classifier.number is not None:
                raise MalformedInputError(
                    input,
                    f"{classifier} cannot have a number for {type(self)}",
                )
            if self._has_classifier() == 2 and classifier.particles is None:
                raise MalformedInputError(
                    input,
                    f"{classifier} doesn't have a particle classifier for {type(self)}",
                )
            if self._has_classifier() == 0 and classifier.particles is not None:
                raise MalformedInputError(
                    input,
                    f"{classifier} cannot have a particle classifier for {type(self)}",
                )

    def __lt__(self, other):
        type_comp = self.prefix < other.prefix
        if type_comp:
            return type_comp
        elif self.prefix > other.prefix:
            return type_comp
        else:  # otherwise first part is equal
            return self._input_number.value < other._input_number.value


class DataInput(DataInputAbstract):
    """Catch-all for all other MCNP data inputs.

    Parameters
    ----------
    input : Input | str
        the Input object representing this data input
    fast_parse : bool
        Whether or not to only parse the first word for the type of
        data.
    prefix : str
        The input prefix found during parsing (internal use only)
    """

    @args_checked
    def __init__(
        self,
        input: InitInput = None,
        *,
        fast_parse: bool = False,
        prefix: str = None,
        jit_parse: bool = True,
    ):
        if prefix:
            self._load_correct_parser(prefix)
        super().__init__(input, fast_parse, jit_parse=jit_parse)

    @property
    def _class_prefix(self):
        return None

    @property
    def _has_number(self):  # pragma: no cover
        return None

    @property
    def _has_classifier(self):  # pragma: no cover
        return None

    def _load_correct_parser(self, prefix):
        """Decides if a specialized parser needs to be loaded for barebone
        special cases.

        .. versionadded:: 0.3.0
        """
        PARAM_PARSER = ParamOnlyDataParser
        TALLY_PARSER = montepy.input_parser.tally_parser.TallyParser
        PARSER_PREFIX_MAP = {
            "f": TALLY_PARSER,
            "fm": TALLY_PARSER,
            "fs": montepy.input_parser.tally_seg_parser.TallySegmentParser,
            "sdef": PARAM_PARSER,
        }
        if prefix.lower() in PARSER_PREFIX_MAP:
            self._parser = PARSER_PREFIX_MAP[prefix.lower()]()


class ForbiddenDataInput(DataInputAbstract):
    """MCNP data input that is not actually parsed and only parroted out.

    Current inputs that are in "parser jail":

    * ``DE``
    * ``SDEF``

    Parameters
    ----------
    input : Input | str
        the Input object representing this data input
    fast_parse : bool
        Whether or not to only parse the first word for the type of
        data.
    prefix : str
        The input prefix found during parsing (internal use only)
    """

    @args_checked
    def __init__(
        self,
        input: InitInput = None,
        fast_parse: bool = False,
        prefix: str = None,
        *,
        jit_parse: bool = True,
    ):
        super().__init__(input, True, jit_parse=jit_parse)
        if isinstance(input, str):
            input = montepy.input_parser.mcnp_input.Input(
                input.split("\n"), self._BLOCK_TYPE
            )
        self._input = input

    @property
    def _class_prefix(self):
        return None

    @property
    def _has_number(self):  # pragma: no cover
        return None

    @property
    def _has_classifier(self):  # pragma: no cover
        return None

    def _error_out(self):
        """ """
        raise UnsupportedFeature(
            f"Inputs of type: {self.classifier.prefix} are not supported yet "
            "due to their complex syntax."
            "These will be written out correctly, but cannot be edited",
            input,
        )

    @property
    def _prop_error(self):
        self._error_out()

    data = _prop_error
    """
    Not supported.

    .. warning::

        Because this input was not parsed these data are not available.

    raises
    ------
    UnsupportedFeature 
        when called.
    """

    @args_checked
    def format_for_mcnp_input(self, mcnp_version: ty.VersionType) -> list[str]:
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
        return self._input.input_lines

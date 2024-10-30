# Copyright 2024, Battelle Energy Alliance, LLC All Rights Reserved.
from abc import abstractmethod
import copy

import montepy
from montepy.errors import *
from montepy.input_parser.data_parser import (
    ClassifierParser,
    DataParser,
    ParamOnlyDataParser,
)
from montepy.input_parser.mcnp_input import Input
from montepy.particle import Particle
from montepy.mcnp_object import MCNP_Object

import re


class _ClassifierInput(Input):
    """
    A specialized subclass that returns only 1 useful token.
    """

    def tokenize(self):
        """
        Returns one token after all starting comments and spaces.
        """
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
    """
    Parent class to describe all MCNP data inputs.

    :param input: the Input object representing this data input
    :type input: Input
    :param fast_parse: Whether or not to only parse the first word for the type of data.
    :type fast_parse: bool
    """

    _parser = DataParser()

    _classifier_parser = ClassifierParser()

    def __init__(self, input=None, fast_parse=False):
        self._particles = None
        if not fast_parse:
            super().__init__(input, self._parser)
            if input:
                self.__split_name(input)
        else:
            input = copy.copy(input)
            input.__class__ = _ClassifierInput
            super().__init__(input, self._classifier_parser)
            self.__split_name(input)

    @staticmethod
    @abstractmethod
    def _class_prefix():
        """The text part of the input identifier.

        For example: for a material the prefix is ``m``

        this must be lower case

        :returns: the string of the prefix that identifies a input of this class.
        :rtype: str
        """
        pass

    @staticmethod
    @abstractmethod
    def _has_number():
        """Whether or not this class supports numbering.

        For example: ``kcode`` doesn't allow numbers but tallies do allow it e.g., ``f7``

        :returns: True if this class allows numbers
        :rtype: bool
        """
        pass

    @staticmethod
    @abstractmethod
    def _has_classifier():
        """Whether or not this class supports particle classifiers.

        For example: ``kcode`` doesn't allow particle types but tallies do allow it e.g., ``f7:n``

        * 0 : not allowed
        * 1 : is optional
        * 2 : is mandatory

        :returns: True if this class particle classifiers
        :rtype: int
        """
        pass

    @property
    def particle_classifiers(self):
        """The particle class part of the card identifier as a parsed list.

        This is parsed from the input that was read.

        For example: the classifier for ``F7:n`` is ``:n``, and ``imp:n,p`` is ``:n,p``
        This will be parsed as a list: ``[<Particle.NEUTRON: 'N'>, <Particle.PHOTON: 'P'>]``.

        :returns: the particles listed in the input if any. Otherwise None
        :rtype: list
        """
        if self._particles:
            return self._particles
        return None

    @property
    def prefix(self):
        """The text part of the card identifier parsed from the input.

        For example: for a material like: m20 the prefix is 'm'
        this will always be lower case.

        :returns: The prefix read from the input
        :rtype: str
        """
        return self._prefix.lower()

    @property
    def prefix_modifier(self):
        """The modifier to a name prefix that was parsed from the input.

        For example: for a transform: ``*tr5`` the modifier is ``*``

        :returns: the prefix modifier that was parsed if any. None if otherwise.
        :rtype: str
        """
        return self._modifier

    @property
    def data(self):
        """
        The syntax tree actually holding the data.

        :returns: The syntax tree with the information.
        :rtype: ListNode
        """
        return self._tree["data"]

    @property
    def classifier(self):
        """
        The syntax tree object holding the data classifier.

        For example this would container information like ``M4``, or ``F104:n``.

        :returns: the classifier for this data_input.
        :rtype: ClassifierNode
        """
        return self._tree["classifier"]

    def validate(self):
        pass

    def _update_values(self):
        pass

    def update_pointers(self, data_inputs):
        """
        Connects data inputs to each other

        :param data_inputs: a list of the data inputs in the problem
        :type data_inputs: list
        :returns: True iff this input should be removed from ``problem.data_inputs``
        :rtype: bool, None
        """
        pass

    def __str__(self):
        return f"DATA INPUT: {self._tree['classifier']}"

    def __repr__(self):
        return str(self)

    def __split_name(self, input):
        """
        Parses the name of the data input as a prefix, number, and a particle classifier.

        This populates the properties:
            prefix
            _input_number
            classifier

        :param input: the input object representing this data input
        :type input: input
        :raises MalformedInputError: if the name is invalid for this DataInput
        """
        self._classifier = self._tree["classifier"]
        self.__enforce_name(input)
        self._input_number = self._classifier.number
        self._prefix = self._classifier._prefix.value
        if self._classifier.particles:
            self._particles = self._classifier.particles.particles
        self._modifier = self._classifier.modifier

    def __enforce_name(self, input):
        """
        Checks that the name is valid.

        :param input: the input object representing this data input
        :type input: input
        :raises MalformedInputError: if the name is invalid for this DataInput
        """
        classifier = self._classifier
        if self._class_prefix:
            if classifier.prefix.value.lower() != self._class_prefix():
                raise MalformedInputError(
                    input,
                    f"{self._tree['classifier'].format()} has the wrong prefix for {type(self)}",
                )
            if self._has_number():
                try:
                    num = classifier.number.value
                    assert num > 0
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

    @property
    def class_prefix(self):  # pragma: no cover
        """The text part of the card identifier.

        For example: for a material the prefix is ``m``

        this must be lower case

        .. deprecated:: 0.2.0
            This has been moved to :func:`_class_prefix`

        :returns: the string of the prefix that identifies a card of this class.
        :rtype: str
        :raises DeprecationWarning: always raised.
        """
        warnings.warn(
            "This has been moved to the property _class_prefix.",
            DeprecationWarning,
            stacklevl=2,
        )

    @property
    def has_number(self):  # pragma: no cover
        """Whether or not this class supports numbering.

        For example: ``kcode`` doesn't allow numbers but tallies do allow it e.g., ``f7``

        .. deprecated:: 0.2.0
            This has been moved to :func:`_has_number`

        :returns: True if this class allows numbers
        :rtype: bool
        :raises DeprecationWarning: always raised.
        """
        warnings.warn(
            "This has been moved to the property _has_number.",
            DeprecationWarning,
            stacklevl=2,
        )

    @property
    def has_classifier(self):  # pragma: no cover
        """Whether or not this class supports particle classifiers.

        For example: ``kcode`` doesn't allow particle types but tallies do allow it e.g., ``f7:n``

        * 0 : not allowed
        * 1 : is optional
        * 2 : is mandatory

        .. deprecated:: 0.2.0
            This has been moved to :func:`_has_classifier`


        :returns: True if this class particle classifiers
        :rtype: int
        :raises DeprecationWarning: always raised.
        """
        warnings.warn(
            "This has been moved to the property _has_classifier.",
            DeprecationWarning,
            stacklevl=2,
        )


class DataInput(DataInputAbstract):
    """
    Catch-all for all other MCNP data inputs.

    :param input: the Input object representing this data input
    :type input: Input
    :param fast_parse: Whether or not to only parse the first word for the type of data.
    :type fast_parse: bool
    :param prefix: The input prefix found during parsing (internal use only)
    :type prefix: str
    """

    def __init__(self, input=None, fast_parse=False, prefix=None):
        if prefix:
            self._load_correct_parser(prefix)
        super().__init__(input, fast_parse)

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
        """
        Decides if a specialized parser needs to be loaded for barebone
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

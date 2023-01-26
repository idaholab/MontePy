from abc import abstractmethod
from mcnpy.errors import *
from mcnpy.input_parser.data_parser import DataParser
from mcnpy.particle import Particle
from mcnpy.mcnp_object import MCNP_Object
import re


class DataInputAbstract(MCNP_Object):
    """
    Parent class to describe all MCNP data inputs.

    :param input: the Input object representing this data input
    :type input: Input
    :param comments: The list of Comments that may proceed this or be entwined with it.
    :type comments: list
    """

    _parser = DataParser()

    def __init__(self, input=None, comments=None):
        """
        :param input: the Input object representing this data input
        :type input: Input
        :param comments: The list of Comments that may proceed this or be entwined with it.
        :type comments: list
        """
        super().__init__(input, self._parser, comments)
        if input:
            self.__split_name()
        else:
            self._words = []

    @property
    def allowed_keywords(self):
        return set()

    @property
    def words(self):
        """
        The words of the data input, not parsed.

        :rtype: list
        """
        return self._words

    @words.setter
    def words(self, words):
        if not isinstance(words, list):
            raise TypeError("words must be a list")
        for word in words:
            if not isinstance(word, str):
                raise TypeError(f"element in words: {word} is not a string")
        self._mutated = True
        self._words = words

    @property
    @abstractmethod
    def _class_prefix(self):
        """The text part of the input identifier.

        For example: for a material the prefix is ``m``

        this must be lower case

        :returns: the string of the prefix that identifies a input of this class.
        :rtype: str
        """
        pass

    @property
    @abstractmethod
    def _has_number(self):
        """Whether or not this class supports numbering.

        For example: ``kcode`` doesn't allow numbers but tallies do allow it e.g., ``f7``

        :returns: True if this class allows numbers
        :rtype: bool
        """
        pass

    @property
    @abstractmethod
    def _has_classifier(self):
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
        if self._classifiers:
            return self._classifiers
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

    def format_for_mcnp_input(self, mcnp_version):
        ret = super().format_for_mcnp_input(mcnp_version)
        if self.mutated:
            ret += DataInput.wrap_words_for_mcnp(self.words, mcnp_version, True)
        else:
            ret = self._format_for_mcnp_unmutated(mcnp_version)
        return ret

    def update_pointers(self, data_inputs):
        """
        Connects data inputs to each other

        :param data_inputs: a list of the data inputs in the problem
        :type data_inputs: list
        """
        pass

    def __str__(self):
        return f"DATA INPUT: {self._words}"

    def __split_name(self):
        """
        Parses the name of the data input as a prefix, number, and a particle classifier.

        This populates the properties:
            prefix
            _input_number
            classifier

        :raises MalformedInputError: if the name is invalid for this DataInput

        """
        self._classifier = self._tree["classifier"]
        self.__enforce_name()
        self._input_number = self._classifier.number
        self._prefix = self._classifier._prefix.value
        if self._classifier.particles:
            self._classifiers = self._classifier.particles.particles
        self._modifier = self._classifier.modifier

    def __enforce_name(self):
        """
        Checks that the name is valid.

        :raises MalformedInputError: if the name is invalid for this DataInput
        """
        classifier = self._classifier
        if self._class_prefix:
            if classifier.prefix.value.lower() != self._class_prefix:
                raise MalformedInputError(
                    self.words, f"{self.words[0]} has the wrong prefix for {type(self)}"
                )
            if self._has_number:
                try:
                    num = classifier.number.value
                    assert num > 0
                except (AssertionError) as e:
                    raise MalformedInputError(
                        self.words, f"{self.words[0]} does not contain a valid number"
                    )
            if not self._has_number and classifier.number is not None:
                raise MalformedInputError(
                    self.words, f"{self.words[0]} cannot have a number for {type(self)}"
                )
            if self._has_classifier == 2 and classifier.particles is None:
                raise MalformedInputError(
                    self.words,
                    f"{self.words[0]} doesn't have a particle classifier for {type(self)}",
                )
            if self._has_classifier == 0 and classifier.particles is not None:
                raise MalformedInputError(
                    self.words,
                    f"{self.words[0]} cannot have a particle classifier for {type(self)}",
                )

    @staticmethod
    def _parse_particle_classifiers(classifier_str):
        """
        Parses a particle classifier string.

        Interprets ``:n,p`` (from ``imp:n,p``) as:
            ``[<Particle.NEUTRON: 'N'>, <Particle.PHOTON: 'P'>]``

        :param classifier_str: the input classifier string from the input name.
        :type classifier_str: str
        :returns: a list of the ParticleTypes in the classifier
        :rtype: list
        """
        if classifier_str:
            classifier_chunks = classifier_str.replace(":", "").split(",")
            ret = []
            for chunk in classifier_chunks:
                ret.append(Particle(chunk.upper()))
            return ret

    def __lt__(self, other):
        type_comp = self.prefix < other.prefix
        if type_comp:
            return type_comp
        elif self.prefix > other.prefix:
            return type_comp
        else:  # otherwise first part is equal
            return self._input_number < other._input_number


class DataInput(DataInputAbstract):
    """
    Catch-all for all other MCNP data inputs.

    :param input_card: the Card object representing this data card
    :type input_card: Card
    :param comments: The list of Comments that may proceed this or be entwined with it.
    :type comments: list
    """

    @property
    def _class_prefix(self):
        return None

    @property
    def _has_number(self):
        return None

    @property
    def _has_classifier(self):
        return None

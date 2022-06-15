from abc import abstractmethod
from mcnpy.errors import *
from mcnpy.mcnp_card import MCNP_Card
import re


class DataCardAbstract(MCNP_Card):
    """
    Parent class to describe all MCNP data inputs.
    """

    _MODIFIERS = [r"\*"]
    _NUMBER_EXTRAS = [r"\-"]
    _CLASSIFIER_EXTRAS = [":", ","]
    _NAME_PARSER = re.compile(
        (
            rf"^(?P<modifier>[{''.join(_MODIFIERS)}]+)*"
            rf"(?P<prefix>[a-z]+)"
            rf"(?P<number>[\d{''.join(_NUMBER_EXTRAS)}]+)*"
            rf"(?P<classifier>:[a-z{''.join(_CLASSIFIER_EXTRAS)}]+)*$"
        ),
        re.I,
    )

    def __init__(self, input_card=None, comment=None):
        """
        :param input_card: the Card object representing this data card
        :type input_card: Card
        :param comment: The Comment that may proceed this
        :type comment: Comment
        """
        super().__init__(input_card, comment)
        if input_card:
            self._words = input_card.words
            self.__split_name()
        else:
            self._words = []

    @property
    def words(self):
        """
        The words of the data card, not parsed.

        :rtype: list
        """
        return self._words

    @words.setter
    def words(self, words):
        assert isinstance(words, list)
        for word in words:
            assert isinstance(word, str)
        self._mutated = True
        self._words = words

    @property
    @abstractmethod
    def class_prefix(self):
        """The text part of the card identifier.

        For example: for a material the prefix is 'm'

        this must be lower case

        :returns: the string of the prefix that identifies a card of this class.
        :rtype: str
        """
        pass

    @property
    @abstractmethod
    def has_number(self):
        """Whether or not this class supports numbering.

        For example: `kcode` doesn't allow numbers but tallies do allow it e.g.: `f7`

        :returns: True if this class allows numbers
        :rtype: bool
        """
        pass

    @property
    @abstractmethod
    def has_classifier(self):
        """Whether or not this class supports particle classifiers.

        For example: `kcode` doesn't allow numbers but tallies do allow it e.g.: `f7:n`

        0 : not allowed
        1 : is optional
        2 : is mandatory

        :returns: True if this class particle classifiers
        :rtype: int
        """
        pass

    @property
    def particle_classifier(self):
        """The particle class part of the card identifier.

        For example: the classifier for `F7:n` is `:n`, and `imp:n,p` is `:n,p`
        :rtype: str
        """
        if self._classifier:
            return self._classifier.lower()
        return None

    @property
    def prefix(self):
        """The text part of the card identifier.

        For example: for a material like: m20 the prefix is 'm'

        this will always be lower case
        :rtype: str
        """
        return self._prefix.lower()

    @property
    def prefix_modifier(self):
        """The modifier to a name prefix.

        For example: for a transform: *tr5 the modifier is *
        :rtype: str
        """
        return self._modifier

    def format_for_mcnp_input(self, mcnp_version):
        ret = super().format_for_mcnp_input(mcnp_version)
        if self.mutated:
            ret += DataCard.wrap_words_for_mcnp(self.words, mcnp_version, True)
        else:
            ret = self._format_for_mcnp_unmutated(mcnp_version)
        return ret

    def update_pointers(self, data_cards):
        """
        Connects data cards to each other

        :param data_cards: a list of the data cards in the problem
        :type data_cards: list
        """
        pass

    def __str__(self):
        return f"DATA CARD: {self._words}"

    def __split_name(self):
        """
        Parses the name of the data card as a prefix, number, and a particle classifier.

        This populates the properties:
            prefix
            _input_number
            classifier

        :raises MalformedInputError: if the name is invalid for this DataCard

        """
        name = self._words[0]
        match = self._NAME_PARSER.match(name)
        if match is None:
            raise MalformedInputError(
                self.words, f"{self.words[0]} is not a valid starting word"
            )
        match_dict = match.groupdict()
        self.__enforce_name(match_dict)
        number = match_dict["number"]
        if number:
            self._input_number = int(number)
        else:
            self._input_number = None
        self._prefix = match_dict["prefix"]
        self._classifier = match_dict["classifier"]
        self._modifier = match_dict["modifier"]

    def __enforce_name(self, match_dict):
        """
        Checks that the name is valid.

        :param match_dict: the matching dictionary from the parsing regex.
        :type match_dict: dict
        :raises MalformedInputError: if the name is invalid for this DataCard
        """
        print(match_dict)
        if self.class_prefix:
            if match_dict["prefix"].lower() != self.class_prefix:
                raise MalformedInputError(
                    self.words, f"{self.words[0]} has the wrong prefix for {type(self)}"
                )
            if self.has_number:
                try:
                    int(match_dict["number"])
                except (ValueError, TypeError) as e:
                    raise MalformedInputError(
                        self.words, f"{self.words[0]} does not contain a valid number"
                    )
            if not self.has_number and match_dict["number"] is not None:
                raise MalformedInputError(
                    self.words, f"{self.words[0]} cannot have a number for {type(self)}"
                )
            if self.has_classifier == 2 and match_dict["classifier"] is None:
                raise MalformedInputError(
                    self.words,
                    f"{self.words[0]} doesn't have a particle classifier for {type(self)}",
                )
            if self.has_classifier == 0 and match_dict["classifier"] is not None:
                raise MalformedInputError(
                    self.words,
                    f"{self.words[0]} cannot have a particle classifier for {type(self)}",
                )

    def __lt__(self, other):
        type_comp = self.prefix < other.prefix
        if type_comp:
            return type_comp
        elif self.prefix > other.prefix:
            return type_comp
        else:  # otherwise first part is equal
            return self._input_number < other._input_number


class DataCard(DataCardAbstract):
    @property
    def class_prefix(self):
        return None

    @property
    def has_number(self):
        return None

    @property
    def has_classifier(self):
        return None

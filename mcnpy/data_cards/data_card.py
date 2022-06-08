from mcnpy.errors import *
from mcnpy.mcnp_card import MCNP_Card


class DataCard(MCNP_Card):
    """
    Parent class to describe all MCNP data inputs.
    """

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

    def __split_name__(self):
        name = self._words[0]
        prefix_extras = [":"]
        number_extras = ["-"]
        names = [
            "".join(c for c in name if c.isalpha() or c in prefix_extras) or None,
            "".join(c for c in name if c.isdigit() or c in number_extras) or None,
        ]
        if names[1]:
            names[1] = int(names[1])
        return names

    def __lt__(self, other):
        self_parts = self.__split_name__()
        other_parts = other.__split_name__()
        type_comp = self_parts[0] < other_parts[0]
        if type_comp:
            return type_comp
        elif self_parts[0] > other_parts[0]:
            return type_comp
        else:  # otherwise first part is equal
            return self_parts[1] < other_parts[1]

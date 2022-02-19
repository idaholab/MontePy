from mcnpy.errors import *
from mcnpy.mcnp_card import MCNP_Card


class DataCard(MCNP_Card):
    """
    Parent class to describe all MCNP data inputs.
    """

    def __init__(self, input_card, comment=None):
        """
        :param input_card: the Card object representing this data card
        :type input_card: Card
        :param comment: The Comment that may proceed this
        :type comment: Comment
        """
        super().__init__(input_card, comment)
        if input_card:
            self.__words = input_card.words
        else:
            self.__words = []

    @property
    def words(self):
        """
        The words of the data card, not parsed.

        :rtype: list
        """
        return self.__words

    def format_for_mcnp_input(self, mcnp_version):
        ret = super().format_for_mcnp_input(mcnp_version)
        if self.mutated:
            ret += DataCard.wrap_words_for_mcnp(self.words, mcnp_version, True)
        else:
            ret += self.input_lines
        return ret

    def update_pointers(self, data_cards):
        """
        Connects data cards to each other

        :param data_cards: a list of the data cards in the problem
        :type data_cards: list
        """
        pass

    def __str__(self):
        return f"DATA CARD: {self.__words}"

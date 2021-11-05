from .material import Material
from .mcnp_card import MCNP_Card


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
        super().__init__(comment)
        self.__words = input_card.words

    @property
    def words(self):
        """
        The words of the data card, not parsed.

        :rtype: list
        """
        return self.__words

    def format_for_mcnp_input(self):
        pass

    @staticmethod
    def parse_data(input_card, comment=None):
        """
        Parses the data card as the appropriate object if it is supported.

        :param input_card: the Card object for this Data card
        :type input_card: Card
        :param comment: the Comment that may proceed this.
        :type comment: Comment
        :return: the parsed DataCard object
        :rtype: DataCard
        """
        identifier = input_card.words[0]

        #material finder
        if "m" in identifier.lower():
            return Material(input_card, comment)
        else:
            return DataCard(input_card, comment)

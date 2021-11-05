from .mcnp_card import MCNP_Card


class DataCard(MCNP_Card):
    """
    Parent class to describe all MCNP data inputs.
    """

    def __init__(self, input_card, comment=None):
        """"""
        pass

    def format_for_mcnp_input(self):
        pass

    @staticmethod
    def parse_data(cls, input_card, comment=None):
        """"""
        pass

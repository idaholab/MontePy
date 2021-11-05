from .mcnp_card import MCNP_Card

class DataCard(MCNP_Card):
    """
    Parent class to describe all MCNP data inputs.
    """
    

    def format_for_mcnp_input(self):
        pass

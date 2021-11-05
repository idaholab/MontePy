from abc import ABC, abstractmethod

class MCNP_Card(ABC):
    """
    Abstract class for semantic representations of MCNP input cards.
    """
    

    @abstractmethod
    def format_for_mcnp_input(self):
        """
        Creates a string representation of this card that can be
        written to file.

        :return: a list of strings for the lines that this card will occupy.
        :rtype: list
        """
        pass

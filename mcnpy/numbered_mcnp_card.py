from abc import abstractmethod
from mcnpy.mcnp_card import MCNP_Card


class Numbered_MCNP_Card(MCNP_Card):
    @property
    @abstractmethod
    def number(self):
        """
        The current number of the object that will be written out to a new input.

        :rtype: int
        """
        pass

    @property
    @abstractmethod
    def old_number(self):
        """
        The original number of the object provided in the input file

        :rtype: int
        """
        pass

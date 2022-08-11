from mcnpy.cells import Cells
from mcnpy.numbered_mcnp_card import Numbered_MCNP_Card


class Universe(Numbered_MCNP_Card):
    """
    Class to represent an MCNP universe
    """

    def __init__(self, number):
        self._number = number
        self._cells = Cells()

    @property
    def cells(self):
        """
        A list of the cell objects in this universe.

        :return: a `Cells` object
        """
        return self._cells

from mcnpy.cells import Cells
from mcnpy.numbered_mcnp_card import Numbered_MCNP_Card


class Universe(Numbered_MCNP_Card):
    """
    Class to represent an MCNP universe, but not handle the input
    directly.
    """

    def __init__(self, number):
        self._number = number

    @property
    def cells(self):
        """
        A list of the cell objects in this universe.

        :return: a `Cells` object
        """
        if self._problem:
            for cell in self._problem.cells:
                if cell.universe == self:
                    yield cell

    @property
    def number(self):
        return self._number

    @property
    def old_number(self):
        return self._number

    @property
    def class_prefix(self):
        return "u"

    def format_for_mcnp_input(self, mcnp_version):
        pass

    def allowed_keywords(self):
        return set()

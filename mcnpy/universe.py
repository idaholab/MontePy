from mcnpy.cells import Cells
from mcnpy.input_parser.mcnp_input import Card
from mcnpy.input_parser.block_type import BlockType
from mcnpy.numbered_mcnp_card import Numbered_MCNP_Card


class Universe(Numbered_MCNP_Card):
    """
    Class to represent an MCNP universe, but not handle the input
    directly.
    """

    def __init__(self, number):
        super().__init__(Card(["U"], BlockType.DATA))
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

    @number.setter
    def number(self, number):
        if not isinstance(number, int):
            raise TypeError("number must be int")
        if number <= 0:
            raise ValueError("Universe number must be ≥ 0")
        if self._problem:
            self._problem.universes.check_number(number)
        self._mutated = True
        self._number = number

    @property
    def old_number(self):
        return self._number

    @property
    def class_prefix(self):
        return "u"

    def format_for_mcnp_input(self, mcnp_version):
        pass

    @property
    def allowed_keywords(self):
        return set()

    def __str__(self):
        return f"Universe({self.number})"

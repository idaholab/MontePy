import mcnpy
from mcnpy.cells import Cells
from mcnpy.input_parser.mcnp_input import Card
from mcnpy.input_parser.block_type import BlockType
from mcnpy.numbered_mcnp_object import Numbered_MCNP_Object


class Universe(Numbered_MCNP_Object):
    """
    Class to represent an MCNP universe, but not handle the input
    directly.

    :param number: The number for the universe, must be ≥ 0
    :type number: int
    """

    def __init__(self, number):
        super().__init__(Card(["U"], BlockType.DATA))
        if not isinstance(number, int):
            raise TypeError("number must be int")
        if number < 0:
            raise ValueError("Universe number must be ≥ 0")
        self._number = number

    @property
    def cells(self):
        """
        A generator of the cell objects in this universe.

        :return: a generator returning every cell in this universe.
        :rtype: Generator
        """
        if self._problem:
            for cell in self._problem.cells:
                if cell.universe == self:
                    yield cell

    def claim(self, cells):
        """
        Take the given cells and move them into this universe, and out of their original universe.

        Can be given a single Cell, a list of cells, or a Cells object.

        :param cells: the cell(s) to be claimed
        :type cells: Cell, list, or Cells
        :raises TypeError: if bad parameter is given.
        """
        if not isinstance(cells, (mcnpy.Cell, list, Cells)):
            raise TypeError(f"Cells being claimed must be a Cell, list, or Cells")
        if isinstance(cells, list):
            cells = Cells(cells)
        if isinstance(cells, mcnpy.Cell):
            cells = Cells([cells])

        for cell in cells:
            cell.universe = self

    @property
    def number(self):
        """
        The number for this Universe.

        Universe 0 is protected, and a Universe cannot be set 0,
        if it is not already Universe 0.
        """
        return self._number

    @number.setter
    def number(self, number):
        if not isinstance(number, int):
            raise TypeError("number must be int")
        if number <= 0:
            raise ValueError("Universe number must be > 0")
        if self._problem:
            self._problem.universes.check_number(number)
        self._mutated = True
        self._number = number

    @property
    def old_number(self):
        """
        Original universe number from the input file.
        """
        return self._number

    def format_for_mcnp_input(self, mcnp_version):
        pass

    @property
    def allowed_keywords(self):
        return set()

    def __str__(self):
        return f"Universe({self.number})"

    def __repr__(self):
        return (
            f"Universe: Number: {self.number} "
            f"Problem: {'set' if self._problem else 'not set'}, "
            f"Cells: {[cell.number for cell in self.cells] if self._problem else ''}"
        )

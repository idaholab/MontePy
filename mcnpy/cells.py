import mcnpy
from mcnpy.collections import Collection


class Cells(Collection):
    """A collections of cells."""

    def __init__(self, cells=None):
        """
        :param cells: the list of cells to start with if needed
        :type cells: list
        """
        super().__init__(mcnpy.Cell, cells)

    @property
    def numbers(self):
        """
        A generator of the cell numbers being used
        """
        for cell in self._objects:
            yield cell.cell_number

    def append(self, cell):
        assert isinstance(cell, mcnpy.Cell)
        self._objects.append(cell)

    def __iadd__(self, other):
        assert type(other) in [Cells, list]
        for cell in other:
            assert isinstance(cell, mcnpy.Cell)
        self._objects += other._objects
        return self

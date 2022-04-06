import mcnpy
from mcnpy.numbered_object_collection import NumberedObjectCollection


class Cells(NumberedObjectCollection):
    """A collections of cells."""

    def __init__(self, cells=None):
        """
        :param cells: the list of cells to start with if needed
        :type cells: list
        """
        super().__init__(mcnpy.Cell, cells)

    def append(self, cell):
        assert isinstance(cell, mcnpy.Cell)
        self._objects.append(cell)

    def __iadd__(self, other):
        assert type(other) in [Cells, list]
        for cell in other:
            assert isinstance(cell, mcnpy.Cell)
        if isinstance(other, Cells):
            self._objects += other._objects
        else:
            self._objects += other
        return self

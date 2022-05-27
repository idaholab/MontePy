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

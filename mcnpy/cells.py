from mcnpy.cell import Cell


class Cells:
    """A collections of cells."""

    def __init__(self, cells=None):
        """
        :param cells: the list of cells to start with if needed
        :type cells: list
        """
        if cells:
            assert isinstance(cells, list)
            for cell in cells:
                assert isinstance(cell, Cell)
            self._cells = cells
        else:
            self._cells = []

    @property
    def numbers(self):
        """
        A generator of the cell numbers being used
        """
        for cell in self._cells:
            yield cell.cell_number

    def check_redundant_numbers(self):
        """
        Checks if there are any redundant cell numbers.
        :returns: true if there are collisions of cell_numbers
        :rtype: bool
        """
        return len(self._cells) != len(set(self.numbers))

    def __iter__(self):
        self._iter = self._cells.__iter__()
        return self._iter

    def __next__(self):
        return self._iter.__next__()

    def append(self, cell):
        assert isinstance(cell, Cell)
        self._cells.append(cell)

    def __getitem__(self, i):
        return self._cells[i]

    def __len__(self):
        return len(self._cells)

    def __iadd__(self, other):
        assert type(other) in [Cells, list]
        for cell in other:
            assert isinstance(cell, Cell)
        self._cells += other._cells
        return self

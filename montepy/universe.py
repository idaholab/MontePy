# Copyright 2024, Battelle Energy Alliance, LLC All Rights Reserved.
import montepy
from montepy.cells import Cells
from montepy.input_parser.mcnp_input import Input
from montepy.input_parser.block_type import BlockType
from montepy.input_parser import syntax_node
from montepy.numbered_mcnp_object import Numbered_MCNP_Object


class Universe(Numbered_MCNP_Object):
    """
    Class to represent an MCNP universe, but not handle the input
    directly.

    :param number: The number for the universe, must be ≥ 0
    :type number: int
    """

    def __init__(self, number):
        self._number = self._generate_default_node(int, -1)
        if not isinstance(number, int):
            raise TypeError("number must be int")
        if number < 0:
            raise ValueError(f"Universe number must be ≥ 0. {number} given.")
        self._number = self._generate_default_node(int, number)

        class Parser:
            def parse(self, token_gen, input):
                return syntax_node.SyntaxNode("fake universe", {})

        super().__init__(Input(["U"], BlockType.DATA), Parser())

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
        if not isinstance(cells, (montepy.Cell, list, Cells)):
            raise TypeError(f"Cells being claimed must be a Cell, list, or Cells")
        if isinstance(cells, list):
            cells = Cells(cells)
        if isinstance(cells, montepy.Cell):
            cells = Cells([cells])

        for cell in cells:
            cell.universe = self

    @property
    def old_number(self):
        """
        Original universe number from the input file.
        """
        return self._number

    def _update_values(self):
        pass

    def __str__(self):
        return f"Universe({self.number})"

    def __repr__(self):
        return (
            f"Universe: Number: {self.number} "
            f"Problem: {'set' if self._problem else 'not set'}, "
            f"Cells: {[cell.number for cell in self.cells] if self._problem else ''}"
        )

# Copyright 2024-2025, Battelle Energy Alliance, LLC All Rights Reserved.
from __future__ import annotations

from numbers import Integral
from typing import Generator
import numpy as np


import montepy
from montepy.cells import Cells
from montepy.input_parser.mcnp_input import Input
from montepy.input_parser.block_type import BlockType
from montepy.input_parser import syntax_node
from montepy.numbered_mcnp_object import Numbered_MCNP_Object


class Universe(Numbered_MCNP_Object):
    """Class to represent an MCNP universe, but not handle the input
    directly.

    Parameters
    ----------
    number : int
        The number for the universe, must be ≥ 0
    """

    def __init__(self, number: int):
        self._number = self._generate_default_node(int, -1)
        if not isinstance(number, Integral):
            raise TypeError("number must be int")
        if number < 0:
            raise ValueError(f"Universe number must be ≥ 0. {number} given.")
        self._number = self._generate_default_node(int, number)

        class Parser:
            def parse(self, token_gen, input):
                return syntax_node.SyntaxNode("fake universe", {})

        super().__init__(Input(["U"], BlockType.DATA), Parser(), number)

    @property
    def cells(self) -> Generator[montepy.Cell, None, None]:
        """A generator of the cell objects in this universe.

        Returns
        -------
        Generator
            a generator returning every cell in this universe.
        """
        if self._problem:
            for cell in self._problem.cells:
                if cell.universe == self:
                    yield cell

    @property
    def filled_cells(self) -> Generator[montepy.Cell, None, None]:
        """A generator of the cells that use this universe.

        Returns
        -------
        Generator[Cell]
            an iterator of the Cell objects which use this universe as their fill.
        """
        if not self._problem:
            yield from []
            return

        for cell in self._problem.cells:
            if cell.fill:
                if cell.fill.universes is not None:
                    if np.any(cell.fill.universes.flatten() == self):
                        yield cell
                elif cell.fill.universe == self:
                    yield cell

    def claim(self, cells):
        """Take the given cells and move them into this universe, and out of their original universe.

        Can be given a single Cell, a list of cells, or a Cells object.

        Parameters
        ----------
        cells : Cell, list, or Cells
            the cell(s) to be claimed

        Raises
        ------
        TypeError
            if bad parameter is given.
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
        """Original universe number from the input file."""
        return self._number

    def _update_values(self):
        pass

    def __str__(self):
        return f"Universe({self.number})"

    def __repr__(self):
        return f"<Universe: {self.number}>"
    
    
    def __eq__(self, other):
        if not isinstance(other, type(self)):
            return False
        return self.number == other.number

# Copyright 2024-2025, Battelle Energy Alliance, LLC All Rights Reserved.
from __future__ import annotations

import montepy.types as ty
from typing import Generator
import numpy as np


import montepy
from montepy.utilities import *
from montepy.cells import Cells
from montepy.input_parser.mcnp_input import Input
from montepy.input_parser.block_type import BlockType
from montepy.input_parser import syntax_node
from montepy.numbered_mcnp_object import Numbered_MCNP_Object
import montepy.types as ty


class Universe(Numbered_MCNP_Object):
    """Class to represent an MCNP universe, but not handle the input
    directly.

    Parameters
    ----------
    number : int
        The number for the universe, must be ≥ 0
    """

    @staticmethod
    def _parent_collections():
        return (("cells", "universe", False),)

    @args_checked
    def __init__(self, number: ty.NonNegativeInt, *, jit_parse: bool = False):
        super().__init__(Input(["U"], BlockType.DATA), number)
        self._number = self._generate_default_node(int, number)

    def full_parse(self):
        pass

    # dummy abstract methods
    @staticmethod
    def _parser():
        class Parser:
            @staticmethod
            def parse(token_gen, input):
                return syntax_node.SyntaxNode("fake universe", {})

        return Parser

    def _init_blank(self):
        self._number = self._generate_default_node(int, -1)

    def _parse_tree(self):
        pass

    def _generate_default_tree(self, **kwargs):
        pass

    @property
    def cells(self) -> Generator[montepy.Cell, None, None]:
        """A generator of the cell objects in this universe.

        Returns
        -------
        Generator[montepy.Cell, None, None]
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
        Generator[Cell, None, None]
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

    @args_checked
    def claim(self, cells: montepy.Cell | ty.Iterable[montepy.Cell]):
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
        if isinstance(cells, montepy.Cell):
            cells = Cells([cells])

        for cell in cells:
            cell.universe = self

    @args_checked
    def soft_claim(self, cells: montepy.Cell | ty.Iterable[montepy.Cell]):
        if isinstance(cells, montepy.Cell):
            cells = Cells([cells])

        for cell in cells:
            # only claim if user hasn't given it a more interesting universe
            # avoids recursion from creating JIT universes
            if cell._universe._universe is None or cell._universe._universe.number == 0:
                cell.universe = self

    def grab_cells_from_jit_parse(self):
        if not self._problem:
            return
        cells_to_claim = []
        for cell in self._problem.cells:
            if not hasattr(cell, "_not_parsed"):
                if cell._universe.old_number == self.number:
                    cells_to_claim.append(cell)
            else:
                uni_inp = cell._universe
                if (
                    hasattr(uni_inp, "_parked_data")
                    and uni_inp._parked_data.value == self.number
                ):
                    cells_to_claim.append(cell)
                elif cell.search(str(self.number)):
                    cell.full_parse()
                    # TODO does uni_inp get thrown out?
                    if uni_inp.old_number == self.number:
                        cells_to_claim.append(cell)
        self.soft_claim(cells_to_claim)

    @property
    def old_number(self):
        """Original universe number from the input file."""
        return self._number

    def _update_values(self):
        pass

    def __eq__(self, other):
        if not isinstance(other, type(self)):
            return False
        return self.number == other.number

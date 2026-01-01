# Copyright 2024, Battelle Energy Alliance, LLC All Rights Reserved.
import itertools

from montepy.utilities import *
from montepy.data_inputs.cell_modifier import CellModifierInput, InitInput
from montepy.data_inputs.lattice import LatticeType
from montepy.exceptions import *
from montepy.input_parser.mcnp_input import Jump
from montepy.input_parser import syntax_node
from montepy.mcnp_object import MCNP_Object
import montepy.types as ty
from montepy.utilities import *


class LatticeInput(CellModifierInput):
    """Object to handle the inputs from ``LAT``.

    Parameters
    ----------
    input : Input | str
        the Input object representing this data input
    in_cell_block : bool
        if this card came from the cell block of an input file.
    key : str
        the key from the key-value pair in a cell
    value : SyntaxNode
        the value syntax tree from the key-value pair in a cell
    """

    def _init_blank(self):
        self._lattice = self._generate_default_node(int, None)

    def _parse_cell_tree(self):
        val = self._tree["data"]
        if isinstance(val, syntax_node.ListNode):
            val = val[0]
        if val.type is not LatticeType:
            try:
                val.convert_to_int()
                val.convert_to_enum(LatticeType, int)
            except ValueError as e:
                raise ValueError("Cell Lattice must be 1 or 2") from e
        self._lattice = val

    def _parse_data_tree(self):
        self._lattice = []
        words = self.data
        for word in words:
            if word.type is not LatticeType:
                try:
                    word.convert_to_int()
                    word.convert_to_enum(LatticeType, int)
                except ValueError as e:
                    raise MalformedInputError(
                        input, f"Cell lattice must be 1 or 2. {word} given."
                    ) from e
            self._lattice.append(word)

    def _generate_default_cell_tree(self):
        list_node = syntax_node.ListNode("number sequence")
        data = self._generate_default_node(int, None)
        data.convert_to_enum(LatticeType, True, int)
        list_node.append(data)
        classifier = syntax_node.ClassifierNode()
        classifier.prefix = self._generate_default_node(
            str, self._class_prefix().upper(), None
        )
        self._tree = syntax_node.SyntaxNode(
            "lattice",
            {
                "classifier": classifier,
                "param_seperator": self._generate_default_node(str, "=", None),
                "data": list_node,
            },
        )

    @staticmethod
    def _class_prefix():
        return "lat"

    @staticmethod
    def _has_number():
        return False

    @staticmethod
    def _has_classifier():
        return 0

    @property
    @needs_full_ast
    def has_information(self):
        if self.in_cell_block:
            return self.lattice is not None

    @make_prop_val_node(
        "_lattice", (LatticeType, int, type(None)), LatticeType, deletable=True
    )
    def lattice(self) -> LatticeType:
        """The type of lattice being used.

        Returns
        -------
        LatticeType
        """
        pass

    @property
    @needs_full_ast
    def _tree_value(self):
        return self._lattice

    @needs_full_ast
    def push_to_cells(self):
        if self._problem and not self.in_cell_block:
            cells = self._problem.cells
            if self._lattice:
                self._check_redundant_definitions()
                for cell, lattice in itertools.zip_longest(
                    cells, self._lattice, fillvalue=None
                ):
                    if not isinstance(lattice, (Jump, type(None))):
                        cell._lattice._accept_from_data(lattice)

    def _accept_and_update(self, value):
        self.lattice = value

    def merge(self, other):
        raise MalformedInputError(
            other._input, "Cannot have two lattice inputs for the problem"
        )

    def _clear_data(self):
        del self._lattice

    def _update_cell_values(self):
        pass

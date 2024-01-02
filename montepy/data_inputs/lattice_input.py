# Copyright 2024, Battelle Energy Alliance, LLC All Rights Reserved.
import itertools
from montepy.data_inputs.cell_modifier import CellModifierInput
from montepy.data_inputs.lattice import Lattice
from montepy.errors import *
from montepy.input_parser.mcnp_input import Jump
from montepy.input_parser import syntax_node
from montepy.mcnp_object import MCNP_Object
from montepy.utilities import *


class LatticeInput(CellModifierInput):
    """
    Object to handle the inputs from ``LAT``.

    :param input: the Input object representing this data input
    :type input: Input
    :param in_cell_block: if this card came from the cell block of an input file.
    :type in_cell_block: bool
    :param key: the key from the key-value pair in a cell
    :type key: str
    :param value: the value syntax tree from the key-value pair in a cell
    :type value: SyntaxNode
    """

    def __init__(self, input=None, in_cell_block=False, key=None, value=None):
        super().__init__(input, in_cell_block, key, value)
        self._lattice = self._generate_default_node(int, None)
        self._lattice._convert_to_enum(Lattice, True, int)
        if self.in_cell_block:
            if key:
                try:
                    val = value["data"][0]
                    val._convert_to_int()
                    val._convert_to_enum(Lattice, int)
                except ValueError as e:
                    raise ValueError("Cell Lattice must be 1 or 2")
                self._lattice = val
        elif input:
            self._lattice = []
            words = self.data
            for word in words:
                try:
                    word._convert_to_int()
                    word._convert_to_enum(Lattice, int)
                    self._lattice.append(word)
                except ValueError:
                    raise MalformedInputError(
                        input, f"Cell lattice must be 1 or 2. {word} given."
                    )

    def _generate_default_cell_tree(self):
        list_node = syntax_node.ListNode("number sequence")
        data = self._generate_default_node(int, None)
        data._convert_to_enum(Lattice, True, int)
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
    def has_information(self):
        if self.in_cell_block:
            return self.lattice is not None

    @make_prop_val_node("_lattice", (Lattice, int, type(None)), Lattice, deletable=True)
    def lattice(self):
        """
        The type of lattice being used.

        :rtype: Lattice
        """
        pass

    @property
    def _tree_value(self):
        return self._lattice

    def push_to_cells(self):
        if self._problem and not self.in_cell_block:
            cells = self._problem.cells
            if self._lattice:
                self._check_redundant_definitions()
                for cell, lattice in itertools.zip_longest(
                    cells, self._lattice, fillvalue=None
                ):
                    if not isinstance(lattice, (Jump, type(None))):
                        cell._lattice._lattice = lattice

    def merge(self, other):
        raise MalformedInputError(
            other._input, "Cannot have two lattice inputs for the problem"
        )

    def _clear_data(self):
        del self._lattice

    def __str__(self):
        return "Lattice: {self.lattice}"

    def __repr__(self):
        ret = (
            f"Lattice: in_cell: {self._in_cell_block}"
            f" set_in_block: {self.set_in_cell_block}, "
            f"Lattice_values : {self.lattice}"
        )
        return ret

    def _update_cell_values(self):
        pass

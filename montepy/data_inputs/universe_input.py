# Copyright 2024, Battelle Energy Alliance, LLC All Rights Reserved.
import itertools
from montepy.data_inputs.cell_modifier import CellModifierInput
from montepy.errors import *
from montepy.constants import DEFAULT_VERSION
from montepy.input_parser.mcnp_input import Jump
from montepy.input_parser import syntax_node
from montepy.mcnp_object import MCNP_Object
from montepy.universe import Universe
from montepy.utilities import *


class UniverseInput(CellModifierInput):
    """
    Object to actually handle the ``U`` input in cells
    and data blocks.

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
        self._universe = None
        self._old_numbers = []
        self._old_number = self._generate_default_node(int, Jump())
        self._not_truncated = False
        super().__init__(input, in_cell_block, key, value)
        if self.in_cell_block:
            if key:
                val = self._tree["data"][0]
                val.is_negatable_identifier = True
                self._not_truncated = val.is_negative
                self._old_number = val
        elif input:
            self._universes = []
            for node in self.data:
                try:
                    node.is_negatable_identifier = True
                    if node.value is not None:
                        self._old_numbers.append(node)
                    else:
                        self._old_numbers.append(node)
                except ValueError:
                    raise MalformedInputError(
                        input,
                        f"Cell universes must be an integer ≥ 0. {node} was given",
                    )

    def _generate_default_cell_tree(self):
        list_node = syntax_node.ListNode("number sequence")
        list_node.append(self._generate_default_node(int, Jump()))
        classifier = syntax_node.ClassifierNode()
        classifier.prefix = self._generate_default_node(
            str, self._class_prefix().upper(), None
        )
        self._tree = syntax_node.SyntaxNode(
            "universe",
            {
                "classifier": classifier,
                "param_seperator": self._generate_default_node(str, "=", None),
                "data": list_node,
            },
        )

    @staticmethod
    def _class_prefix():
        return "u"

    @staticmethod
    def _has_number():
        return False

    @staticmethod
    def _has_classifier():
        return 0

    @make_prop_val_node("_old_number")
    def old_number(self):
        pass

    @property
    def old_numbers(self):
        ret = []
        for value in self._old_numbers:
            if isinstance(value, syntax_node.ValueNode):
                ret.append(value.value)
            else:
                ret.append(value)
        return ret

    @property
    def has_information(self):
        if self.in_cell_block:
            return self.universe is not None and self.universe.number != 0

    @make_prop_pointer("_universe", Universe)
    def universe(self):
        if self.in_cell_block:
            return self._universe

    @property
    def not_truncated(self):
        """
        Indicates if this cell has been marked as not being truncated for optimization.

        See Note 1 from section 3.3.1.5.1 of the user manual (LA-UR-17-29981).

            Note 1. A problem will run faster by preceding the U card entry with a minus sign for any
            cell that is not truncated by the boundary of any higher-level cell. (The minus sign indicates
            that calculating distances to boundary in higher-level cells can be omitted.) Use this
            capability with EXTREME CAUTION; MCNP6 cannot detect errors in this feature because
            the logic that enables detection is omitted by the presence of the negative universe. Extremely
            wrong answers can be quietly calculated. Plot several views of the geometry or run with the
            VOID card to check for errors.

            -- LA-UR-17-29981.

        :rtype: bool
        :returns: True if this cell has been marked as not being truncated by the parent filled cell.
        """
        return self._not_truncated

    @not_truncated.setter
    def not_truncated(self, value):
        if not isinstance(value, bool):
            raise TypeError("truncated_by_parent must be a bool")
        self._not_truncated = value

    @property
    def _tree_value(self):
        val = self._old_number
        val.value = self.universe.number
        val.is_negative = self.not_truncated
        return val

    def _collect_new_values(self):
        ret = []
        for cell in self._problem.cells:
            # force value update here with _tree_value
            if cell._universe._tree_value.value == 0:
                # access ValueNode directly to avoid override with _tree_value
                cell._universe._old_number._value = None
            ret.append(cell._universe._old_number)
        return ret

    def merge(self, other):
        raise MalformedInputError(
            other._input, "Cannot have two universe inputs for the problem"
        )

    def push_to_cells(self):
        if not self._problem:
            return
        if not self.in_cell_block:
            cells = self._problem.cells
            if self._old_numbers:
                self._check_redundant_definitions()
                for cell, uni_number in itertools.zip_longest(
                    cells, self._old_numbers, fillvalue=None
                ):
                    if isinstance(uni_number, (Jump, type(None))):
                        continue
                    cell._universe._old_number = uni_number
                    if uni_number.is_negative:
                        cell._universe._not_truncated = True
            universes = self._problem.universes
            for cell in cells:
                uni_num = cell.old_universe_number
                if uni_num is None:
                    uni_num = 0
                if uni_num not in universes.numbers:
                    universe = Universe(uni_num)
                    universe.link_to_problem(self._problem)
                    universes.append(universe)
                else:
                    universe = universes[uni_num]
                cell._universe._universe = universe

    def _clear_data(self):
        del self._old_numbers

    def __str__(self):
        ret = "\n".join(self.format_for_mcnp_input(DEFAULT_VERSION))
        return ret

    def __repr__(self):
        ret = (
            f"UNIVERSE: in_cell: {self._in_cell_block}"
            f" set_in_block: {self.set_in_cell_block}, "
            f"Universe : {self._universe}, "
            f"Old Numbers: {self._old_numbers if hasattr(self, '_old_numbers') else ''}"
        )
        return ret

    def _update_cell_values(self):
        if self.universe is not None:
            self._tree["data"][0].is_negatable_identifier = True
            self._tree["data"][0].value = self.universe.number
            self._tree["data"][0].is_negative = self.not_truncated

import itertools
from mcnpy.data_inputs.cell_modifier import CellModifierInput
from mcnpy.errors import *
from mcnpy.input_parser.constants import DEFAULT_VERSION
from mcnpy.input_parser.mcnp_input import Jump
from mcnpy.input_parser.syntax_node import ValueNode
from mcnpy.mcnp_object import MCNP_Object
from mcnpy.universe import Universe
from mcnpy.utilities import *


class UniverseInput(CellModifierInput):
    """
    Object to actually handle the ``U`` card in cells
    and data blocks.

    :param input: the Input object representing this data card
    :type input: Input
    :param comments: The list of Comments that may proceed this or be entwined with it.
    :type comments: list
    :param in_cell_block: if this card came from the cell block of an input file.
    :type in_cell_block: bool
    :param key: the key from the key-value pair in a cell
    :type key: str
    :param value: the value from the key-value pair in a cell
    :type value: str
    """

    def __init__(
        self, input=None, comments=None, in_cell_block=False, key=None, value=None
    ):
        self._universe = None
        self._universes = None
        self._old_numbers = []
        self._old_number = self._generate_default_node(int, None)
        self._not_truncated = False
        super().__init__(input, comments, in_cell_block, key, value)
        if self.in_cell_block:
            self._old_number = self._generate_default_node(int, 0)
            if key:
                val = value["data"][0]
                val.is_negatable_identifier = True
                self._not_truncated = val.is_negative
                self._old_number = val
        elif input:
            self._universes = []
            for node in self.data:
                if not isinstance(node, Jump):
                    try:
                        node.is_negatable_identifier = True
                        self._old_numbers.append(node)
                    except ValueError:
                        raise MalformedInputError(
                            input,
                            f"Cell universes must be an integer ≥ 0. {node} was given",
                        )
                elif isinstance(node, Jump):
                    self._old_numbers.append(node)

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
            if isinstance(value, ValueNode):
                ret.append(value.value)
            else:
                ret.append(value)
        return ret

    @property
    def has_information(self):
        if self.in_cell_block:
            return self.universe.number != 0

    @property
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
        self._mutated = True
        self._not_truncated = value

    @universe.setter
    def universe(self, value):
        if not isinstance(value, Universe):
            raise TypeError("universe must be set to a Universe")
        self._mutated = True
        self._universe = value

    def merge(self, other):
        raise MalformedInputError(
            other, "Cannot have two universe inputs for the problem"
        )

    def push_to_cells(self):
        if not self._problem:
            return
        if not self.in_cell_block:
            cells = self._problem.cells
            if self._universes:
                self._check_redundant_definitions()
                for cell, uni_number in itertools.zip_longest(
                    cells, self._universes, fillvalue=None
                ):
                    if isinstance(uni_number, (Jump, type(None))):
                        continue
                    cell._universe.old_number = abs(uni_number.value)
                    if uni_number < 0:
                        cell._universe._not_truncated = True
            universes = self._problem.universes
            for cell in cells:
                uni_num = cell.old_universe_number.value
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
        del self._universes

    def __str__(self):
        ret = "\n".join(self.format_for_mcnp_input(DEFAULT_VERSION))
        return ret

    def __repr__(self):
        ret = (
            f"UNIVERSE: in_cell: {self._in_cell_block}"
            f" set_in_block: {self.set_in_cell_block}, "
            f"Universe : {self._universe}, "
            f"Universes: {self._universes}"
        )
        return ret

    @staticmethod
    def _get_print_number(number, not_truncating):
        """
        Prepares the universe number for printing.

        This handles the whole negative sign for not being truncated by the parent.

        :param number: the universe number.
        :type number: int
        :param not_truncating: True if this cell isn't truncated by the parent cell
        :type not_truncating: bool
        :returns: the number properly formatted or a Jump if the number is 0.
        :rtype: int or Jump
        """
        if number == 0:
            return Jump()
        if not_truncating:
            number = -number
        return number

    def _update_values(self):
        pass
        # TODO

    def format_for_mcnp_input(self, mcnp_version):
        self.validate()
        self._update_values()
        return self.wrap_string_for_mcnp(self._tree.format(), mcnp_version, True)

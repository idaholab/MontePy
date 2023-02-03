from abc import abstractmethod
import mcnpy
from mcnpy.data_inputs.data_input import DataInputAbstract
from mcnpy.input_parser import syntax_node
from mcnpy.input_parser.block_type import BlockType
from mcnpy.input_parser.mcnp_input import Input


class CellModifierInput(DataInputAbstract):
    """
    Abstract Parent class for Data Cards that modify cells / geometry.

    Examples: IMP, VOL, etc.

    :param input_card: the Card object representing this data card
    :type input_card: Card
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
        fast_parse = False
        if key and value:
            input = Input([key], BlockType.DATA)
            fast_parse = True
        super().__init__(input, comments, fast_parse)
        if not isinstance(in_cell_block, bool):
            raise TypeError("in_cell_block must be a bool")
        if key and not isinstance(key, str):
            raise TypeError("key must be a str")
        if value and not isinstance(value, syntax_node.SyntaxNode):
            raise TypeError("value must be from a SyntaxNode")
        if key and in_cell_block:
            self._set_in_cell_block = True
            self._tree = value
            self._data = value["data"]
        else:
            self._set_in_cell_block = False
        self._in_cell_block = in_cell_block
        self._in_key = key
        self._in_value = value

    @property
    def in_cell_block(self):
        """
        True if this object represents an input from the cell block section of a file.

        :rtype: bool
        """
        return self._in_cell_block

    @property
    def set_in_cell_block(self):
        """
        True if this data were set in the cell block in the input
        """
        return self._set_in_cell_block

    @property
    def has_changed_print_style(self):
        """
        returns true if the printing style for this modifier has changed
        from cell block to data block, or vice versa.

        :returns: true if the printing style for this modifier has changed
        :rtype: bool
        """
        if self._problem:
            if not self.in_cell_block:
                for cell in self._problem.cells:
                    attr = mcnpy.Cell._INPUTS_TO_PROPERTY[type(self)][0]
                    set_in_cell_block = getattr(cell, attr).set_in_cell_block
                    break
            else:
                set_in_cell_block = self.set_in_cell_block
            print_in_cell_block = not self._problem.print_in_data_block[
                self._class_prefix()
            ]
            set_in_cell_block = print_in_cell_block
            if not self.in_cell_block:
                for cell in self._problem.cells:
                    attr = mcnpy.Cell._CARDS_TO_PROPERTY[type(self)][0]
                    modifier = getattr(cell, attr)
                    if modifier.has_information:
                        set_in_cell_block = modifier.set_in_cell_block
                    break
            else:
                if self.has_information:
                    set_in_cell_block = self.set_in_cell_block
            return print_in_cell_block ^ set_in_cell_block
        else:
            return False

    @abstractmethod
    def merge(self, other):
        """
        Merges the data from another card of same type into this one.

        :param other: The other object to merge into this object.
        :type other: CellModifierInput
        :raises MalformedInputError: if two objects cannot be merged.
        """
        pass

    def link_to_problem(self, problem):
        super().link_to_problem(problem)
        if self.set_in_cell_block:
            self._problem.print_in_data_block[self._class_prefix()] = False

    @abstractmethod
    def push_to_cells(self):
        """
        After being linked to the problem update all cells attributes with this data.

        This needs to also check that none of the cells had data provided in the cell block
        (check that ``set_in_cell_block`` isn't set).
        Use ``self._check_redundant_definitions`` to do this.

        :raises MalformedInputError: When data are given in the cell block and the data block.
        """
        pass

    @property
    @abstractmethod
    def has_information(self):
        """
        For a cell instance of :class:`mcnpy.data_cards.cell_modifier.CellModifierCard` returns True iff there is information here worth printing out.

        e.g., a manually set volume for a cell

        :returns: True if this instance has information worth printing.
        :rtype: bool
        """
        pass

    def _check_redundant_definitions(self):
        """
        Checks that data wasn't given in data block and the cell block.
        """
        attr, _ = mcnpy.Cell._INPUTS_TO_PROPERTY[type(self)]
        if not self._in_cell_block and self._problem:
            cells = self._problem.cells
            for cell in cells:
                if getattr(cell, attr).set_in_cell_block:
                    raise mcnpy.errors.MalformedInputError(
                        cell,
                        f"Cell: {cell.number} provided {self._class_prefix.upper()}"
                        "data when those data were in the data block",
                    )

    @abstractmethod
    def _clear_data(self):
        """
        After data being pushed to cells delete internal data to avoid inadvertent editing.
        """
        pass

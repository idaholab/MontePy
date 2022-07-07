from abc import abstractmethod
import mcnpy
from mcnpy.data_cards.data_card import DataCardAbstract
from mcnpy.input_parser.block_type import BlockType
from mcnpy.input_parser.mcnp_input import Card


class CellModifierCard(DataCardAbstract):
    """
    Abstract Parent class for Data Cards that modify cells/ geometry.

    Examples: IMP, VOL, etc.
    """

    def __init__(
        self, input_card=None, comments=None, in_cell_block=False, key=None, value=None
    ):
        """
        :param input_card: the Card object representing this data card
        :type input_card: Card
        :param comment: The Comment that may proceed this
        :type comment: Comment
        :param in_cell_block: if this card came from the cell block of an input file.
        :type in_cell_block: bool
        :param key: the key from the key-value pair in a cell
        :type key: str
        :param key: the value from the key-value pair in a cell
        :type key: str
        """
        if key and value:
            input_card = Card([f"{key} {value}"], BlockType.DATA)
        super().__init__(input_card, comments)
        if not isinstance(in_cell_block, bool):
            raise TypeError("in_cell_block must be a bool")
        if key and not isinstance(key, str):
            raise TypeError("key must be a str")
        if value and not isinstance(value, str):
            raise TypeError("value must be a str")
        if key and in_cell_block:
            self._set_in_cell_block = True
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
                    attr = mcnpy.Cell._CARDS_TO_PROPERTY[type(self)][0]
                    set_in_cell_block = getattr(cell, attr).set_in_cell_block
                    break
            else:
                set_in_cell_block = self.set_in_cell_block
            print_in_cell_block = not self._problem.print_in_data_block[
                self.class_prefix
            ]
            return print_in_cell_block ^ set_in_cell_block
        else:
            return False

    @abstractmethod
    def merge(self, card):
        """
        Merges the data from another card of same type into this one.
        """
        pass

    def link_to_problem(self, problem):
        super().link_to_problem(problem)
        if self.set_in_cell_block:
            self._problem.print_in_data_block[self.class_prefix] = False

    @abstractmethod
    def push_to_cells(self):
        """
        After being linked to the problem update all cells attributes with this data.

        This needs to also check that none of the cells had data provided in the cell block
        (check that ``set_in_cell_block`` isn't set).

        :raises MalformedInputError: When data are given in the cell block and the data block.
        """
        pass

    @abstractmethod
    def _clear_data(self):
        """
        After data being pushed to cells delete internal data to avoid inadvertent editing.
        """
        pass

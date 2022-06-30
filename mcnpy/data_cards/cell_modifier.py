from abc import abstractmethod
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
    @abstractmethod
    def _define_problem_level_method_map(self):
        """"""
        pass

    @property
    @abstractmethod
    def _define_cell_level_method_map(self):
        """"""
        pass

    def _remove_excess_methods(self):
        pass

import itertools
from mcnpy.data_cards.cell_modifier import CellModifierCard
from mcnpy.errors import *
from mcnpy.input_parser.constants import DEFAULT_VERSION
from mcnpy.input_parser.mcnp_input import Jump
from mcnpy.mcnp_card import MCNP_Card
from mcnpy.universe import Universe


class UniverseCard(CellModifierCard):
    """
    Object to actually handle the ``U`` card in cells
    and data blocks.
    """

    def __init__(
        self, input_card=None, comments=None, in_cell_block=False, key=None, value=None
    ):
        """
        :param input_card: the Card object representing this data card
        :type input_card: Card
        :param comments: The list of Comments that may proceed this or be entwined with it.
        :type comments: list
        :param in_cell_block: if this card came from the cell block of an input file.
        :type in_cell_block: bool
        :param key: the key from the key-value pair in a cell
        :type key: str
        :param key: the value from the key-value pair in a cell
        :type key: str
        """
        super().__init__(input_card, comments, in_cell_block, key, value)
        self._universe = None
        self._not_truncated = False
        if self.in_cell_block:
            self._old_number = None
            if key:
                try:
                    value = int(value)
                    if value < 0:
                        self._not_truncated = True
                    value = abs(value)
                    assert value >= 0
                except (ValueError) as e:
                    raise ValueError(
                        f"Cell universe must be an integer {value} was given"
                    )
                self._old_number = value
        elif input_card:
            self._universe = []
            words = self.words[1:]
            for word in words:
                if isinstance(word, str):
                    try:
                        value = int(word)
                        self._universe.append(value)
                    except (ValueError) as e:
                        raise MalformedInputError(
                            input_card,
                            f"Cell universes must be an integer ≥ 0. {word} was given",
                        )
                elif isinstance(word, Jump):
                    self._universe.append(word)
                else:
                    raise TypeError(
                        f"Word: {word} cannot be parsed as a volume as a str, or Jump"
                    )

    @property
    def class_prefix(self):
        return "u"

    @property
    def has_number(self):
        return False

    @property
    def has_classifier(self):
        return 0

    @property
    def old_number(self):
        if self.in_cell_block:
            return self._old_number

    @property
    def universe(self):
        if self.in_cell_block:
            return self._universe

    @property
    def not_truncated_by_parent(self):
        """
        """
        return self._not_truncated

    @not_truncated_by_parent.setter
    def not_truncated_by_parent(self, value):
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
        if self._problem:
            if not self.in_cell_block:
                cells = self._problem.cells
                if self._universe:
                    self._check_redundant_definitions()
                    for cell, uni_number in itertools.zip_longest(
                        cells, self._universe, fillvalue=None
                    ):
                        if not isinstance(uni_number, (Jump, type(None))):
                            cell._universe._old_number = abs(uni_number)
                            if uni_number < 0:
                                cell._universe._not_truncated = True
            universes = self._problem.universes
            for cell in cells:
                uni_num = cell.old_universe_number
                if uni_num is None:
                    uni_num = 0
                if uni_num not in universes.numbers:
                    universe = Universe(uni_num)
                    universes.append(universe)
                else:
                    universe = universes[uni_num]
                cell._universe._universe = universe

    def _clear_data(self):
        del self._universe

    def __str__(self):
        mutated = self.mutated
        self._mutated = True
        ret = "\n".join(self.format_for_mcnp_input(DEFAULT_VERSION))
        self._mutated = mutated
        return ret

    def __repr__(self):
        ret = (
            f"UNIVERSE: in_cell: {self._in_cell_block}"
            f" set_in_block: {self.set_in_cell_block}, "
            f"Universe : {self._universe}"
        )
        return ret

    @staticmethod
    def _get_print_number(number, not_truncating):
        if not_truncating:
            number = -number
        return number

    def format_for_mcnp_input(self, mcnp_version):
        ret = []
        if self.in_cell_block:
            if self.universe and self.universe.number != 0:
                ret.extend(
                    self.wrap_string_for_mcnp(
                        f"U={UniverseCard._get_print_number(self.universe.number, self.not_truncated_by_parent)}",
                        mcnp_version,
                        False,
                    )
                )
        else:
            mutated = self.mutated
            if not mutated:
                mutated = self.has_changed_print_style
                for cell in self._problem.cells:
                    if cell._universe.mutated:
                        mutated = True
                        break
            if mutated and self._problem.print_in_data_block["U"]:
                ret = MCNP_Card.format_for_mcnp_input(self, mcnp_version)
                ret_strs = ["VOL"]
                unis = []
                for cell in self._problem.cells:
                    unis.append(
                        UniverseCard._get_print_number(
                            cell.universe.number, cell.not_truncated_by_parent
                        )
                    )
                ret_strs.extend(self.compress_repeat_values(unis, 1e-1))
                ret.extend(self.wrap_for_mcnp(ret_strs, mcnp_version, True))
            else:
                ret = self._format_for_mcnp_unmutated(mcnp_version)
        return ret

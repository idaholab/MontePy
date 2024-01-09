# Copyright 2024, Battelle Energy Alliance, LLC All Rights Reserved.
import itertools
from montepy.data_cards.cell_modifier import CellModifierCard
from montepy.errors import *
from montepy.input_parser.constants import DEFAULT_VERSION
from montepy.input_parser.mcnp_input import Jump
from montepy.mcnp_card import MCNP_Card
from montepy.universe import Universe


class UniverseCard(CellModifierCard):
    """
    Object to actually handle the ``U`` card in cells
    and data blocks.

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
        :param value: the value from the key-value pair in a cell
        :type value: str
        """
        self._universe = None
        self._not_truncated = False
        super().__init__(input_card, comments, in_cell_block, key, value)
        if self.in_cell_block:
            self._old_number = None
            if key:
                try:
                    value = int(value)
                    if value < 0:
                        self._not_truncated = True
                    value = abs(value)
                except ValueError:
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
                    except ValueError:
                        raise MalformedInputError(
                            input_card,
                            f"Cell universes must be an integer ≥ 0. {word} was given",
                        )
                elif isinstance(word, Jump):
                    self._universe.append(word)
                else:
                    raise TypeError(
                        f"Word: {word} cannot be parsed as an universe as a str, or Jump"
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
            self._starting_num_cells = len(cells)
            if self._universe:
                self._check_redundant_definitions()
                for cell, uni_number in itertools.zip_longest(
                    cells, self._universe, fillvalue=None
                ):
                    if isinstance(uni_number, (Jump, type(None))):
                        continue
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
                    universe.link_to_problem(self._problem)
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

    def format_for_mcnp_input(self, mcnp_version):
        ret = []
        if self.in_cell_block:
            if self.universe and self.universe.number != 0:
                ret.extend(
                    self.wrap_string_for_mcnp(
                        f"U={UniverseCard._get_print_number(self.universe.number, self.not_truncated)}",
                        mcnp_version,
                        False,
                    )
                )
        else:
            mutated = self.mutated
            if not mutated:
                mutated = self.has_changed_print_style
                if self._starting_num_cells != len(self._problem.cells):
                    mutated = True
                for cell in self._problem.cells:
                    if cell._universe.mutated:
                        mutated = True
                        break
            if mutated and self._problem.print_in_data_block["U"]:
                has_info = False
                for cell in self._problem.cells:
                    if cell._volume.has_information:
                        has_info = True
                        break
                if has_info:
                    ret = MCNP_Card.format_for_mcnp_input(self, mcnp_version)
                    ret_strs = ["U"]
                    unis = []
                    for cell in self._problem.cells:
                        unis.append(
                            UniverseCard._get_print_number(
                                cell.universe.number, cell.not_truncated
                            )
                        )
                    ret_strs.extend(
                        self.compress_jump_values(
                            self.compress_repeat_values(unis, 1e-1)
                        )
                    )
                    ret.extend(self.wrap_words_for_mcnp(ret_strs, mcnp_version, True))
            elif self._problem.print_in_data_block["U"]:
                ret = self._format_for_mcnp_unmutated(mcnp_version)
        return ret

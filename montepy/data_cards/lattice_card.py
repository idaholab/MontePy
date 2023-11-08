import itertools
from montepy.data_cards.cell_modifier import CellModifierCard
from montepy.data_cards.lattice import Lattice
from montepy.errors import *
from montepy.input_parser.constants import DEFAULT_VERSION
from montepy.input_parser.mcnp_input import Jump
from montepy.mcnp_card import MCNP_Card


class LatticeCard(CellModifierCard):
    """
    Object to handle the inputs from ``LAT``.

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
        super().__init__(input_card, comments, in_cell_block, key, value)
        self._lattice = None
        if self.in_cell_block:
            if key:
                try:
                    value = int(value)
                    value = Lattice(value)
                except ValueError as e:
                    raise ValueError("Cell Lattice must be 1 or 2")
                self._lattice = value
        elif input_card:
            self._lattice = []
            words = self.words[1:]
            for word in words:
                if isinstance(word, str):
                    try:
                        value = int(word)
                        self._lattice.append(Lattice(value))
                    except ValueError:
                        raise MalformedInputError(
                            input_card, f"Cell lattice must be 1 or 2"
                        )
                elif isinstance(word, Jump):
                    self._lattice.append(word)
                else:
                    raise TypeError(
                        f"Word: {word} cannot be parsed as a lattice as a str, or Jump"
                    )

    @property
    def class_prefix(self):
        return "lat"

    @property
    def has_number(self):
        return False

    @property
    def has_classifier(self):
        return 0

    @property
    def has_information(self):
        if self.in_cell_block:
            return self.lattice is not None

    @property
    def lattice(self):
        """
        The type of lattice being used.

        :rtype: Lattice
        """
        return self._lattice

    @lattice.setter
    def lattice(self, value):
        if not isinstance(value, (Lattice, int, type(None))):
            raise TypeError(
                "lattice must be set to a Lattice, or an integer, {value} given"
            )
        if isinstance(value, int):
            try:
                value = Lattice(value)
            except ValueError:
                raise ValueError("Value: {value} is not a valid Lattice number")
        self._mutated = True
        self._lattice = value

    @lattice.deleter
    def lattice(self):
        self._mutated = True
        self._lattice = None

    def push_to_cells(self):
        if self._problem and not self.in_cell_block:
            self._starting_num_cells = len(self._problem.cells)
            cells = self._problem.cells
            if self._lattice:
                self._check_redundant_definitions()
                for cell, lattice in itertools.zip_longest(
                    cells, self._lattice, fillvalue=None
                ):
                    if not isinstance(lattice, (Jump, type(None))):
                        cell.lattice = lattice

    def merge(self, other):
        raise MalformedInputError(
            other, "Cannot have two lattice inputs for the problem"
        )

    def _clear_data(self):
        del self._lattice

    def __str__(self):
        return "Lattice: {self.lattice}"

    def __repr__(self):
        ret = (
            f"Lattice: in_cell: {self._in_cell_block}"
            f" set_in_block: {self.set_in_cell_block}, "
            f"Lattice_values : {self._lattice}"
        )
        return ret

    def format_for_mcnp_input(self, mcnp_version):
        ret = []
        if self.in_cell_block:
            if self.lattice:
                ret.extend(
                    self.wrap_string_for_mcnp(
                        f"LAT={self.lattice.value}",
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
                    if cell._lattice.mutated:
                        mutated = True
                        break
            if mutated and self._problem.print_in_data_block["LAT"]:
                has_info = False
                for cell in self._problem.cells:
                    if cell._lattice.has_information:
                        has_info = True
                        break
                if has_info:
                    ret = MCNP_Card.format_for_mcnp_input(self, mcnp_version)
                    ret_strs = ["LAT"]
                    lattices = []
                    for cell in self._problem.cells:
                        if cell.lattice:
                            lattices.append(cell.lattice.value)
                        else:
                            lattices.append(Jump())
                    ret_strs.extend(
                        self.compress_jump_values(
                            self.compress_repeat_values(lattices, 1e-1)
                        )
                    )
                    ret.extend(self.wrap_words_for_mcnp(ret_strs, mcnp_version, True))
            elif self._problem.print_in_data_block["LAT"]:
                ret = self._format_for_mcnp_unmutated(mcnp_version)
        return ret

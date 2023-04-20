from mcnpy.data_cards.cell_modifier import CellModifierCard
from mcnpy.data_cards.transform import Transform
from mcnpy.errors import *
from mcnpy.input_parser.block_type import BlockType
from mcnpy.input_parser.mcnp_input import Card, Jump
from mcnpy.mcnp_card import MCNP_Card
from mcnpy.universe import Universe
import numpy as np


class Fill(CellModifierCard):
    """
    Object to handle the ``FILL`` card in cell and data blocks.

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

    DIMENSIONS = {"i": 0, "j": 1, "k": 2}
    """
    Maps the dimension to its axis number
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

        self._old_number = None
        self._old_numbers = None
        self._universe = None
        self._universes = None
        self._transform = None
        self._hidden_transform = None
        self._old_transform_number = None
        self._multi_universe = False
        super().__init__(input_card, comments, in_cell_block, key, value)
        if self.in_cell_block:
            if key:
                self._parse_cell_input(key, value)
        elif input_card:
            self._old_number = []
            words = self.words[1:]
            for word in words:
                if isinstance(word, str):
                    try:
                        value = int(word)
                        assert value >= 0
                        self._old_number.append(value)
                    except (ValueError, AssertionError) as e:
                        raise MalformedInputError(
                            input_card,
                            f"Cell fill must be set to a valid universe, {word} was given",
                        )
                elif isinstance(word, Jump):
                    self._old_number.append(word)
                else:
                    raise TypeError(
                        f"Word: {word} cannot be parsed as a lattice as a str, or Jump"
                    )

    def _parse_cell_input(self, key, value):
        """
        Parses the information provided in the cell input.

        :param key: The key given in the cell
        :type key: str
        :param value: the value given in the cell
        :type value: str
        """

        def get_universe(value):
            if ":" in value:
                self._parse_matrix(value)
            else:
                words = value.split()
                try:
                    val = int(words[0])
                    assert val > 0
                    self._old_number = val
                except (ValueError, AssertionError) as e:
                    raise ValueError(
                        f"The fill universe must be a valid integer, {words[0]} was given"
                    )
                # ensure only one universe is given
                if len(words) >= 2 and "(" not in words[1]:
                    raise ValueError(
                        f"Fill cannot have two universes in this format. {value} given"
                    )

        if "(" in value:
            get_universe(value)
            parens_contents = value[value.index("(") + 1 : value.rindex(")")]
            words = parens_contents.split()
            if len(words) == 1:
                try:
                    transform = int(words[0])
                    assert transform > 0
                    self._hidden_transform = False
                    self._old_transform_number = transform
                except (ValueError, AssertionError) as e:
                    raise ValueError(
                        "Transform number must be a positive integer. {words[0]} was given."
                    )
            elif len(words) > 1:
                if "*" in key:
                    in_key = "*TR1"
                else:
                    in_key = "TR1"
                input_card = Card([in_key + " " + parens_contents], BlockType.DATA)
                self._transform = Transform(input_card, pass_through=True)
                self._hidden_transform = True

        else:
            get_universe(value)

    def _parse_matrix(self, value):
        """
        Parses a matrix fill of universes.

        :param value: the value in the cell
        :type value: str
        """
        self._multi_universe = True
        words = iter(value.split())
        self._min_index = np.zeros((3,), dtype=np.dtype(int))
        self._max_index = np.zeros((3,), dtype=np.dtype(int))
        for axis, limits in zip(Fill.DIMENSIONS.values(), words):
            values = limits.split(":")
            for val, limit_holder in zip(values, (self._min_index, self._max_index)):
                try:
                    val = int(val)
                    limit_holder[axis] = val
                except ValueError as e:
                    raise ValueError(
                        f"The lattice limits must be an integer. {val} was given"
                    )
        for min_val, max_val in zip(self.min_index, self.max_index):
            if min_val > max_val:
                raise ValueError(
                    "The minimum value must be smaller than the max value."
                    f"Min: {min_val}, Max: {max_val}, Input: {value}"
                )
        self._old_numbers = np.zeros(self._sizes, dtype=np.dtype(int))
        for i in self._axis_range(0):
            for j in self._axis_range(1):
                for k in self._axis_range(2):
                    val = next(words)
                    try:
                        val = int(val)
                        assert val >= 0
                        self._old_numbers[i][j][k] = val
                    except (ValueError, AssertionError) as e:
                        raise ValueError(
                            f"Values provided must be valid universes. {val} given."
                        )

    @property
    def class_prefix(self):
        return "fill"

    @property
    def has_number(self):
        return False

    @property
    def has_classifier(self):
        return 0

    @property
    def universe(self):
        """
        The universe that this cell will be filled with.

        Only returns a value when :func:`multiple_universes` is False, otherwise none.

        :returns: the universe that the cell will be filled with, or None
        :rtype: Universe
        """
        if not self.multiple_universes:
            return self._universe

    @universe.setter
    def universe(self, value):
        if not isinstance(value, (Universe, type(None))):
            raise TypeError(f"Universe must be set to a Universe. {value} given.")
        if self.multiple_universes:
            raise ValueError(
                "A single universe can only be set when multiple_universes is False."
            )
        self._mutated = True
        self._universe = value

    @universe.deleter
    def universe(self):
        self._mutated = True
        self._universe = None

    @property
    def universes(self):
        """
        The universes that this cell will be filled with in a lattice.

        Only returns a value when :func:`multiple_universes` is true, otherwise none.

        :returns: the universes that the cell will be filled with as a 3-D array.
        :rtype: np.ndarray
        """
        if self.multiple_universes:
            return self._universes

    @universes.setter
    def universes(self, value):
        if not isinstance(value, (np.ndarray, type(None))):
            raise TypeError(f"Universes must be set to an array. {value} given.")
        if not self.multiple_universes:
            raise ValueError(
                "Multiple universes can only be set when multiple_universes is True."
            )
        self._mutated = True
        self._universes = value

    @universes.deleter
    def universes(self):
        self._mutated = True
        self._universes = None

    @property
    def min_index(self):
        """
        The minimum indices of the matrix in each dimension.

        For the order of the indices see: ``DIMENSIONS``.

        :returns: the minimum indices of the matrix for complex fills
        :rtype: :class:`numpy.ndarry`
        """
        return self._min_index

    @property
    def max_index(self):
        """
        The maximum indices of the matrix in each dimension.

        For the order of the indices see: ``DIMENSIONS``.

        :returns: the maximum indices of the matrix for complex fills
        :rtype: :class:`numpy.ndarry`
        """
        return self._max_index

    @property
    def multiple_universes(self):
        """
        Whether or not this cell is filled with multiple universes in a matrix.

        :return: True if this cell contains multiple universes
        :rtype: bool
        """
        return self._multi_universe

    @multiple_universes.setter
    def multiple_universes(self, value):
        if not isinstance(value, bool):
            raise TypeError("Multiple_univeses must be set to a bool")
        self._multi_universe = value
        self._mutated = True

    @property
    def old_universe_number(self):
        """
        The number of the universe that this is filled by taken from the input.

        :returns: the old universe number
        :type: int
        """
        return self._old_number

    @property
    def old_universe_numbers(self):
        """
        The numbers of the universes that this is filled by taken from the input.

        :returns: the old universe numbers
        :type: :class:`numpy.ndarray`
        """
        return self._old_numbers

    @property
    def hidden_transform(self):
        """
        Whether or not the transform used is hidden.

        This is true when an unnumbered transform is used
        e.g., ``FILL=1 (1.0 2.0 3.0)``.

        :returns: True iff the transform used is hidden
        :rtype: bool
        """
        return self._hidden_transform

    @property
    def has_information(self):
        if self.in_cell_block:
            return self.universe is not None

    @property
    def transform(self):
        """
        The transform for this fill (if any).

        :returns: the transform for the filling universe for this cell.
        :rtype: Transform
        """
        return self._transform

    @transform.setter
    def transform(self, value):
        if not isinstance(value, (Transform, type(None))):
            raise TypeError("Transform must be set to a Transform.")
        self._mutated = True
        self._transform = value
        if value is not None:
            self._hidden_transform = value.hidden_transform
        else:
            self._hidden_transform = False

    @transform.deleter
    def transform(self):
        self._mutated = True
        self._transform = None

    @property
    def old_transform_number(self):
        """
        The number of the transform specified in the input.

        :returns: the original number for the transform from the input.
        :rtype: int
        """
        return self._old_transform_number

    def merge(self, other):
        raise MalformedInputError(
            other, "Cannot have two lattice inputs for the problem"
        )

    def push_to_cells(self):
        def get_universe(number):
            return self._problem.universes[number]

        if self.in_cell_block:
            if self.old_transform_number:
                self._transform = self._problem.transforms[self.old_transform_number]
            if (
                self.old_universe_number is not None
                or self.old_universe_numbers is not None
            ):
                if isinstance(self.old_universe_numbers, np.ndarray):
                    self._universes = np.empty_like(
                        self.old_universe_numbers, dtype="O"
                    )
                    for i in self._axis_range(0):
                        for j in self._axis_range(1):
                            for k in self._axis_range(2):
                                self._universes[i][j][k] = get_universe(
                                    self.old_universe_numbers[i][j][k].item()
                                )
                else:
                    self._universe = get_universe(self.old_universe_number)
        else:
            if not self.set_in_cell_block and self.old_universe_number:
                self._starting_num_cells = len(self._problem.cells)
                for cell, old_number in zip(
                    self._problem.cells, self.old_universe_number
                ):
                    if not isinstance(old_number, Jump):
                        cell._fill._old_number = old_number
            for cell in self._problem.cells:
                cell._fill.push_to_cells()

    def _clear_data(self):
        self._old_number = None
        self._universe = None

    def _prepare_transform_string(self, mcnp_version):
        """
        Gets the fill transform string ready.

        E.g., (5) or ( 0 0 10)...

        :returns: a tuple of (bool: if true is in degrees and needs *FILL, list of strings)
                the strings are already properly formatted for MCNP
        :rtype: tuple
        """
        if self.hidden_transform:
            in_deg, lines = self.transform._generate_inputs(mcnp_version, True, True)
            lines[0] = "(" + lines[0]
            lines[-1] = lines[-1] + ")"
            return in_deg, lines
        else:
            return (False, [f"({self.transform.number})"])

    def _generate_complex_fill_string(self, mcnp_version):
        """
        Generates the matrix fill string.

        handles: the index ranging, the universe lists, and formatting for MCNP.

        :returns: a list of properly formatted strings.
        :rtype: list
        """
        ret = []
        buff_str = ""
        for axis in self.DIMENSIONS.values():
            buff_str += f" {self.min_index[axis]}:{self.max_index[axis]}"
        ret.extend(self.wrap_string_for_mcnp(buff_str, mcnp_version, True))
        buff_str = ""
        for i in self._axis_range(0):
            for j in self._axis_range(1):
                for k in self._axis_range(2):
                    buff_str += f" {self.universes[i][j][k].number}"
                ret.extend(self.wrap_string_for_mcnp(buff_str, mcnp_version, False))
                buff_str = ""
        return ret

    def _axis_range(self, axis):
        """
        Returns an iterator for iterating over the given axis.

        :param axis: the number of the axis to iterate over
        :type axis: int
        :returns: range
        """
        return range(self._axis_size(axis))

    def _axis_size(self, axis):
        """
        Get the length of the given axis.

        :param axis: the axis to probe into.
        :type axis: int
        :returns: the length of the given axis of the universe matrix.
        :rtype: int
        """
        return int(self.max_index[axis] - self.min_index[axis]) + 1

    @property
    def _sizes(self):
        """
        The axis sizes of the matrix.

        :returns: a tuple of the matrix shape.
        :rtype: tuple
        """
        return (self._axis_size(0), self._axis_size(1), self._axis_size(2))

    def __str__(self):
        return f"Fill: Universe: {self.universe}, transform: {self.transform}"

    def __repr__(self):
        return (
            f"Fill: set_in_cell: {self.set_in_cell_block}, in_cell: {self.in_cell_block} "
            f"old_number: {self.old_universe_number}, old_transform: {self._old_transform_number} "
            f"old_numbers: {self.old_universe_numbers} "
            f"Universe: {self.universe}, universes: {self.universes}, transform: {self.transform} "
            f"Multi_universe: {self._multi_universe} hidden_transform: {self.hidden_transform} "
            f"Min/Max: {str(self.min_index) + ' ' +str(self.max_index) if self._multi_universe == True  else 'None'}"
        )

    def format_for_mcnp_input(self, mcnp_version):
        ret = []
        if self.in_cell_block:
            key = "FILL"
            in_deg = False
            transform_lines = [""]
            if self.universe is not None or self.universes is not None:
                if self.transform:
                    in_deg, transform_lines = self._prepare_transform_string(
                        mcnp_version
                    )
                if in_deg:
                    key = "*" + key
                lines_iter = iter(transform_lines)
                if not self.multiple_universes:
                    value = f"{self.universe.number} {next(lines_iter)}"
                else:
                    complex_lines = self._generate_complex_fill_string(mcnp_version)
                    value = complex_lines[0]

                ret.extend(
                    self.wrap_string_for_mcnp(f"{key}={value}", mcnp_version, False)
                )
                if self.multiple_universes:
                    for line in complex_lines[1:]:
                        ret.extend(self.wrap_string_for_mcnp(line, mcnp_version, False))
                for line in lines_iter:
                    ret.extend(self.wrap_string_for_mcnp(line, mcnp_version, False))
        else:
            mutated = self.has_changed_print_style
            if self._starting_num_cells != len(self._problem.cells):
                mutated = True
            for cell in self._problem.cells:
                if cell.fill.mutated:
                    mutated = True
                    break
            if mutated and self._problem.print_in_data_block["FILL"]:
                has_info = False
                for cell in self._problem.cells:
                    if cell.fill.has_information:
                        has_info = True
                        break
                if has_info:
                    ret = MCNP_Card.format_for_mcnp_input(self, mcnp_version)
                    words = ["FILL"]
                    universes = []
                    for cell in self._problem.cells:
                        fill = cell.fill
                        if fill.transform or fill.multiple_universes:
                            raise ValueError(
                                f"Fill can not be in the data block if"
                                " fill transforms and other complex inputs are used."
                                f" Cell {cell.number} used these"
                            )
                        if fill.universe:
                            universes.append(fill.universe.number)
                        else:
                            universes.append(Jump())
                    words.extend(
                        self.compress_jump_values(
                            self.compress_repeat_values(universes, 1e-1)
                        )
                    )
                    ret += self.wrap_words_for_mcnp(words, mcnp_version, True)
            # if not mutated
            elif self._problem.print_in_data_block["FILL"]:
                ret = self._format_for_mcnp_unmutated(mcnp_version)
        return ret

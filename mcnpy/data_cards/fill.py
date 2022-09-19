from mcnpy.data_cards.cell_modifier import CellModifierCard
from mcnpy.data_cards.transform import Transform
from mcnpy.errors import *
from mcnpy.input_parser.block_type import BlockType
from mcnpy.input_parser.constants import DEFAULT_VERSION
from mcnpy.input_parser.mcnp_input import Card, Jump
from mcnpy.mcnp_card import MCNP_Card
from mcnpy.universe import Universe
import numpy as np


class Fill(CellModifierCard):
    """
    Object to handle the ``FILL`` card in cell and data blocks.
    """

    DIMENSIONS = {"x": 0, "y": 1, "z": 2}

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
        self._old_number = None
        self._universe = None
        self._transform = None
        self._hidden_transform = None
        self._old_transform_number = None
        self._multi_universe = False
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
        def get_universe(value):
            if ":" in value:
                self._parse_matrix(value)
            else:
                words = value.split()
                try:
                    value = int(words[0])
                    assert value > 0
                    self._old_number = value
                except (ValueError, AssertionError) as e:
                    raise ValueError(
                        f"The fill universe must be a valid integer, {words[0]} was given"
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
        """
        self._multi_universe = True
        words = iter(value.split())
        next(words)
        self._min_index = np.zeros((3, 1))
        self._max_index = np.zeros((3, 1))
        for axis, limits in zip(Fill.DIMENSIONS.values(), words):
            values = limits.split(":")
            for val, limit_holder in zip(values, (self._min_index, self._max_index)):
                try:
                    val = int(val)
                    limit_holder[axis] = val
                except (ValueError) as e:
                    raise ValueError(
                        f"The lattice limits must be an integer. {val} was given"
                    )
        sizes = []
        for axis in Fill.DIMENSIONS.values():
            sizes.append(int(self._max_index[axis] - self._min_index[axis] + 1))
        self._old_number = np.zeros(sizes)
        for i in range(sizes[0]):
            for j in range(sizes[1]):
                for k in range(sizes[2]):
                    val = next(words)
                    try:
                        val = int(val)
                        assert val >= 0
                        self._old_number[i][j][k] = val
                    except (ValueError, AssertionError) as e:
                        raise ValueError(
                            "Values provided must be valid universes. {val} given."
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
        return self._universe

    @universe.setter
    def universe(self, value):
        if not isinstance(value, Universe):
            raise TypeError("Universe must be set to a Universe. {value} given.")
        self._mutated = True
        self._universe = Universe

    @property
    def multiple_universes(self):
        return self._multi_universe

    @property
    def old_universe_number(self):
        return self._old_number

    @property
    def hidden_transform(self):
        return self._hidden_transform

    @property
    def transform(self):
        return self._transform

    @property
    def old_transform_number(self):
        return self._old_transform_number

    def merge(self, other):
        raise MalformedInputError(
            other, "Cannot have two lattice inputs for the problem"
        )

    def push_to_cells(self):
        def get_universe(number):
            return self._problem.transforms[number]

        if self.in_cell_block:
            if self.old_transform_number:
                self._transform = get_universe(self.old_transform_number)
            if self.multiple_universes:
                print(get_universe(self.old_universe_number))
            elif self.old_universe_number:
                self._universe = self._problem.universes[self.old_universe_number]
        else:
            if not self.set_in_cell_block:
                for cell, old_number in zip(
                    self._problem.cells, self.old_universe_number
                ):
                    cell._fill._old_number = old_number
            for cell in self._problem.cells:
                cell._fill.push_to_cells()

    def _clear_data(self):
        pass

    def format_for_mcnp_input(self, mcnp_version):
        ret = []

        return ret

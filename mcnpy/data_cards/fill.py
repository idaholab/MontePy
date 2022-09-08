from mcnpy.data_cards.cell_modifier import CellModifierCard
from mcnpy.errors import *
from mcnpy.input_parser.constants import DEFAULT_VERSION
from mcnpy.input_parser.mcnp_input import Jump
from mcnpy.mcnp_card import MCNP_Card


class Fill(CellModifierCard):
    """
    Object to handle the ``FILL`` card in cell and data blocks.
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

        # TODO support *FILL
        super().__init__(input_card, comments, in_cell_block, key, value)
        self._old_number = None
        self._universe = None
        self._transform = None
        if self.in_cell_block:
            if key:
                self._parse_cell_input(value)
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

    def _parse_cell_input(self, value):
        def get_universe(value):
            words = value.split()
            try:
                value = int(words[0])
                assert value > 0
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
                except (ValueError, AssertionError) as e:
                    raise ValueError(
                        "Transform number must be a positive integer. {words[0]} was given."
                    )
        elif ":" in value:
            pass
        else:
            get_universe(value)

    @property
    def class_prefix(self):
        return "fill"

    @property
    def has_number(self):
        return False

    @property
    def has_classifier(self):
        return 0

    def merge(self, other):
        raise MalformedInputError(
            other, "Cannot have two lattice inputs for the problem"
        )

    def push_to_cells(self):
        pass

    def _clear_data(self):
        pass

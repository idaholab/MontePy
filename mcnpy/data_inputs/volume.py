from mcnpy.data_inputs.cell_modifier import CellModifierInput
from mcnpy.errors import *
from mcnpy.input_parser.constants import DEFAULT_VERSION
from mcnpy.input_parser.mcnp_input import Jump
from mcnpy.mcnp_object import MCNP_Object
from mcnpy.utilities import *


class Volume(CellModifierInput):
    """
    Class for the data input that modifies cell volumes; ``VOL``.

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
        self._volume = None
        self._calc_by_mcnp = True
        super().__init__(input, comments, in_cell_block, key, value)
        if self.in_cell_block:
            if key:
                try:
                    value = fortran_float(value)
                    assert value >= 0.0
                except (ValueError, AssertionError) as e:
                    raise ValueError(
                        f"Cell volume must be a number ≥ 0.0. {value} was given"
                    )
                self._volume = value
                self._calc_by_mcnp = False
        elif input:
            self._volume = []
            words = self.words[1:]
            if self.words[1].lower() == "no":
                self._calc_by_mcnp = False
                words = self.words[2:]
            for word in words:
                if isinstance(word, str):
                    try:
                        value = fortran_float(word)
                        assert value >= 0
                        self._volume.append(value)
                    except (ValueError, AssertionError) as e:
                        raise MalformedInputError(
                            input, f"Cell volumes by a number ≥ 0.0: {word} given"
                        )
                elif isinstance(word, Jump):
                    self._volume.append(word)
                else:
                    raise TypeError(
                        f"Word: {word} cannot be parsed as a volume as a str, or Jump"
                    )

    @staticmethod
    def _class_prefix():
        return "vol"

    @staticmethod
    def _has_number():
        return False

    @staticmethod
    def _has_classifier():
        return 0

    @property
    def volume(self):
        """
        The actual cell volume.

        Only available at the cell level.

        :returns: the cell volume iff this is for a single cell
        :rtype: float
        """
        if self.in_cell_block:
            return self._volume

    @volume.setter
    def volume(self, value):
        if not isinstance(value, float):
            raise TypeError("Volume must be set to a float")
        if value < 0.0:
            raise ValueError("Volume must be set to a number ≥ 0")
        self._volume = value
        self._mutated = True

    @volume.deleter
    def volume(self):
        self._volume = None
        self._mutated = True

    @property
    def is_mcnp_calculated(self):
        """
        Indicates whether or not the cell volume will attempt to be calculated by MCNP.

        This can be disabled by either manually setting the volume or disabling
        this calculation globally.
        This does not guarantee that MCNP will able to do so.
        Complex geometries may make this impossible.

        :returns: True iff MCNP will try to calculate the volume for this cell.
        :rtype: bool
        """
        if self._problem and self.in_cell_block:
            # TODO need nice way to interact with "NO" as user
            if not self._problem.cells._volume.is_mcnp_calculated:
                return False
        return self._calc_by_mcnp

    @is_mcnp_calculated.setter
    def is_mcnp_calculated(self, value):
        if not self.in_cell_block:
            self._calc_by_mcnp = value
            self._mutated = True

    @property
    def has_information(self):
        if self.in_cell_block:
            return self.set

    @property
    def set(self) -> bool:
        """
        If this volume is set.

        :returns: true if the volume is manually set.
        :rtype: bool
        """
        return self._volume is not None

    def merge(self, other):
        raise MalformedInputError(
            other, "Cannot have two volume inputs for the problem"
        )

    def push_to_cells(self):
        if not self.in_cell_block and self._problem and self._volume:
            self._check_redundant_definitions()
            cells = self._problem.cells
            for i, cell in enumerate(cells):
                if i >= len(self._volume):
                    return
                vol = self._volume[i]
                if not isinstance(vol, Jump):
                    cell.volume = vol

    def _clear_data(self):
        del self._volume

    def __str__(self):
        mutated = self.mutated
        self._mutated = True
        ret = "\n".join(self.format_for_mcnp_input(DEFAULT_VERSION))
        self._mutated = mutated
        return ret

    def __repr__(self):
        ret = (
            f"VOLUME: in_cell: {self._in_cell_block}, calc_by_mcnp: {self.is_mcnp_calculated},"
            f" set_in_block: {self.set_in_cell_block}, "
            f"Volume : {self._volume}"
        )
        return ret

    def format_for_mcnp_input(self, mcnp_version):
        ret = []
        if self.in_cell_block:
            if self._volume:
                ret.extend(
                    self.wrap_string_for_mcnp(f"VOL={self.volume}", mcnp_version, False)
                )
        else:
            mutated = self.mutated
            if not mutated:
                mutated = self.has_changed_print_style
                for cell in self._problem.cells:
                    if cell._volume.mutated:
                        mutated = True
                        break
            if mutated and self._problem.print_in_data_block["VOL"]:
                ret = MCNP_Object.format_for_mcnp_input(self, mcnp_version)
                ret_strs = ["VOL"]
                if not self.is_mcnp_calculated:
                    ret_strs.append("NO")
                volumes = []
                for cell in self._problem.cells:
                    if cell.volume:
                        volumes.append(f"{cell.volume}")
                    else:
                        volumes.append(Jump())
                ret_strs.extend(self.compress_jump_values(volumes))
                ret.extend(self.wrap_words_for_mcnp(ret_strs, mcnp_version, True))

            else:
                ret = self._format_for_mcnp_unmutated(mcnp_version)
        return ret

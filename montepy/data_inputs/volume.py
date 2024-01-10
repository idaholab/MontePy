# Copyright 2024, Battelle Energy Alliance, LLC All Rights Reserved.
from montepy.data_inputs.cell_modifier import CellModifierInput
from montepy.errors import *
from montepy.constants import DEFAULT_VERSION
from montepy.input_parser.mcnp_input import Jump
from montepy.input_parser import syntax_node
from montepy.mcnp_object import MCNP_Object
from montepy.utilities import *


def _ensure_positive(self, value):
    if value < 0:
        raise ValueError(f"Volume must be positive. {value} given.")


class Volume(CellModifierInput):
    """
    Class for the data input that modifies cell volumes; ``VOL``.

    :param input: the Input object representing this data input
    :type input: Input
    :param in_cell_block: if this card came from the cell block of an input file.
    :type in_cell_block: bool
    :param key: the key from the key-value pair in a cell
    :type key: str
    :param value: the value syntax tree from the key-value pair in a cell
    :type value: SyntaxNode
    """

    def __init__(self, input=None, in_cell_block=False, key=None, value=None):
        self._volume = self._generate_default_node(float, None)
        self._calc_by_mcnp = True
        super().__init__(input, in_cell_block, key, value)
        if self.in_cell_block:
            if key:
                value = self._tree["data"][0]
                if value.type != float or value.value < 0:
                    raise ValueError(
                        f"Cell volume must be a number ≥ 0.0. {value} was given"
                    )
                self._volume = value
                self._calc_by_mcnp = False
        elif input:
            self._volume = []
            tree = self._tree
            if "parameters" in tree:
                raise MalformedInputError(
                    input, f"Volume card can't accept any key-value parameters"
                )
            if (
                "keyword" in tree
                and tree["keyword"].value
                and tree["keyword"].value.lower() == "no"
            ):
                self._calc_by_mcnp = False
            for node in tree["data"]:
                if node.value is not None:
                    try:
                        assert node.type == float
                        assert node.value >= 0
                        self._volume.append(node)
                    except AssertionError:
                        raise MalformedInputError(
                            input, f"Cell volumes by a number ≥ 0.0: {node} given"
                        )
                else:
                    self._volume.append(node)

    def _generate_default_cell_tree(self):
        list_node = syntax_node.ListNode("number sequence")
        list_node.append(self._generate_default_node(float, None))
        classifier = syntax_node.ClassifierNode()
        classifier.prefix = self._generate_default_node(
            str, self._class_prefix().upper(), None
        )
        self._tree = syntax_node.SyntaxNode(
            "volume",
            {
                "classifier": classifier,
                "param_seperator": self._generate_default_node(str, "=", None),
                "data": list_node,
            },
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

    @make_prop_val_node(
        "_volume",
        (float, int, type(None)),
        float,
        validator=_ensure_positive,
        deletable=True,
    )
    def volume(self):
        """
        The actual cell volume.

        Only available at the cell level.

        :returns: the cell volume iff this is for a single cell
        :rtype: float
        """
        pass

    @property
    def _tree_value(self):
        if self.in_cell_block:
            return self._volume

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
            if not self._problem.cells._volume.is_mcnp_calculated:
                return False
        return self._calc_by_mcnp

    @is_mcnp_calculated.setter
    def is_mcnp_calculated(self, value):
        if not self.in_cell_block:
            self._calc_by_mcnp = value

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
        return self.volume is not None

    def merge(self, other):
        raise MalformedInputError(
            other._input, "Cannot have two volume inputs for the problem"
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
                    cell._volume._volume = vol

    def _clear_data(self):
        del self._volume

    def __str__(self):
        ret = "\n".join(self.format_for_mcnp_input(DEFAULT_VERSION))
        return ret

    def __repr__(self):
        ret = (
            f"VOLUME: in_cell: {self._in_cell_block}, calc_by_mcnp: {self.is_mcnp_calculated},"
            f" set_in_block: {self.set_in_cell_block}, "
            f"Volume : {self._volume}"
        )
        return ret

    def _update_values(self):
        if self.in_cell_block:
            self._update_cell_values()
        else:
            keyword = self._tree["keyword"]
            if not self.is_mcnp_calculated and (
                keyword.value is None or keyword.value.lower() != "no"
            ):
                keyword.value = "NO"
                if keyword.padding is None or len(keyword.padding) == 0:
                    keyword.padding = syntax_node.PaddingNode(" ")
            elif self.is_mcnp_calculated:
                keyword.value = None
            new_vals = self._collect_new_values()
            self.data.update_with_new_values(new_vals)

    def _update_cell_values(self):
        if self._tree["data"][0] is not self._volume:
            self._tree["data"].nodes.pop()
            self._tree["data"].append(self._volume)

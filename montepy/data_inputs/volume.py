# Copyright 2024, Battelle Energy Alliance, LLC All Rights Reserved.

from montepy.utilities import *
from montepy.data_inputs.cell_modifier import CellModifierInput
from montepy.exceptions import *
from montepy.constants import DEFAULT_VERSION
from montepy.input_parser.mcnp_input import Jump
from montepy.input_parser import syntax_node
from montepy.mcnp_object import MCNP_Object, InitInput
import montepy.types as ty
from montepy.utilities import *


def _ensure_positive(self, value):
    if value < 0:
        raise ValueError(f"Volume must be positive. {value} given.")


class Volume(CellModifierInput):
    """Class for the data input that modifies cell volumes; ``VOL``.

    Parameters
    ----------
    input : Input
        the Input object representing this data input
    in_cell_block : bool
        if this card came from the cell block of an input file.
    key : str
        the key from the key-value pair in a cell
    value : SyntaxNode
        the value syntax tree from the key-value pair in a cell
    """

    def _init_blank(self):
        self._volume = self._generate_default_node(float, None)
        self._calc_by_mcnp = True

    def _parse_cell_tree(self):
        if self._in_key:
            value = self._tree["data"][0]
            if value.type != float or value.value < 0:
                raise ValueError(
                    f"Cell volume must be a number ≥ 0.0. {value} was given"
                )
            self._volume = value
            self._calc_by_mcnp = False

    def _parse_data_tree(self):
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
    def volume(self) -> float:
        """The actual cell volume.

        Only available at the cell level.

        Returns
        -------
        float
            the cell volume iff this is for a single cell
        """
        pass

    @property
    def _tree_value(self):
        if self.in_cell_block:
            return self._volume

    @property
    @needs_full_ast
    def is_mcnp_calculated(self) -> bool:
        """Indicates whether or not the cell volume will attempt to be calculated by MCNP.

        This can be disabled by either manually setting the volume or disabling
        this calculation globally.
        This does not guarantee that MCNP will able to do so.
        Complex geometries may make this impossible.

        Returns
        -------
        bool
            True iff MCNP will try to calculate the volume for this
            cell.
        """
        if self._problem and self.in_cell_block:
            if not self._problem.cells._volume.is_mcnp_calculated:
                return False
        return self._calc_by_mcnp

    @is_mcnp_calculated.setter
    @needs_full_cst
    def is_mcnp_calculated(self, value):
        if not self.in_cell_block:
            self._calc_by_mcnp = value

    @property
    def has_information(self) -> bool:
        if self.in_cell_block:
            return self.set

    @property
    def set(self) -> bool:
        """If this volume is set.

        Returns
        -------
        bool
            true if the volume is manually set.
        """
        return (self.volume is not None) or (
            hasattr(self, "_parked_value") and self._parked_value.value is not None
        )

    def merge(self, other):
        raise MalformedInputError(
            other._input, "Cannot have two volume inputs for the problem"
        )

    @needs_full_ast
    def push_to_cells(self):
        if not self.in_cell_block and self._problem and self._volume:
            self._check_redundant_definitions()
            cells = self._problem.cells
            for cell, vol in zip(cells, self._volume):
                if not isinstance(vol, Jump):
                    cell._volume._accept_from_data(vol)

    def _accept_and_update(self, value):
        self._volume = value

    def _clear_data(self):
        del self._volume

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

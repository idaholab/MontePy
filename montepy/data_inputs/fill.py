# Copyright 2024 - 2025, Battelle Energy Alliance, LLC All Rights Reserved.
import itertools as it
from numbers import Integral, Real
import numpy as np

from montepy.data_inputs.cell_modifier import CellModifierInput, InitInput
from montepy.data_inputs.transform import Transform
from montepy.exceptions import *
from montepy.input_parser.block_type import BlockType
from montepy.input_parser.mcnp_input import Input, Jump
from montepy.input_parser import syntax_node
from montepy.mcnp_object import MCNP_Object
from montepy.universe import Universe
from montepy.utilities import *


def _verify_3d_index(self, indices):
    for index in indices:
        if not isinstance(index, Integral):
            raise TypeError(f"Index values for fill must be an int. {index} given.")
    if len(indices) != 3:
        raise ValueError(f"3 values must be given for fill. {indices} given")


class Fill(CellModifierInput):
    """Object to handle the ``FILL`` input in cell and data blocks.

    Parameters
    ----------
    input : Union[Input, str]
        the Input object representing this data input
    in_cell_block : bool
        if this card came from the cell block of an input file.
    key : str
        the key from the key-value pair in a cell
    value : SyntaxNode
        the value syntax tree from the key-value pair in a cell
    """

    DIMENSIONS = {"i": 0, "j": 1, "k": 2}
    """Maps the dimension to its axis number"""

    def __init__(
        self,
        input: InitInput = None,
        in_cell_block: bool = False,
        key: str = None,
        value: syntax_node.SyntaxNode = None,
    ):
        self._old_number = self._generate_default_node(int, None)
        self._old_numbers = None
        self._universe = None
        self._universes = None
        self._transform = None
        self._hidden_transform = None
        self._old_transform_number = None
        self._multi_universe = False
        self._min_index = None
        self._max_index = None
        super().__init__(input, in_cell_block, key, value)
        if self.in_cell_block:
            if key:
                self._parse_cell_input(key, value)
        elif input:
            self._old_numbers = []
            values = self.data
            for value in values:
                try:
                    value._convert_to_int()
                    if value.value is not None:
                        assert value.value >= 0
                        self._old_numbers.append(value)
                    else:
                        self._old_numbers.append(value)
                except (ValueError, AssertionError) as e:
                    raise MalformedInputError(
                        input,
                        f"Cell fill must be set to a valid universe, {value} was given",
                    )

    def _generate_default_cell_tree(self):
        list_node = syntax_node.ListNode("number sequence")
        list_node.append(self._generate_default_node(float, None))
        classifier = syntax_node.ClassifierNode()
        classifier.prefix = self._generate_default_node(
            str, self._class_prefix().upper(), None, never_pad=True
        )
        self._tree = syntax_node.SyntaxNode(
            "fill",
            {
                "classifier": classifier,
                "param_seperator": self._generate_default_node(str, "=", None),
                "data": list_node,
            },
        )

    def _parse_cell_input(self, key, value):
        """Parses the information provided in the cell input.

        Parameters
        ----------
        key : str
            The key given in the cell
        value : str
            the value given in the cell
        """

        def get_universe(value):
            if ":" in value["data"].nodes:
                self._parse_matrix(value)
            else:
                data = value["data"]
                try:
                    val = data[0]
                    val._convert_to_int()
                    assert val.value >= 0
                    self._old_number = val
                except (TypeError, AssertionError) as e:
                    raise ValueError(
                        f"The fill universe must be a valid integer ≥ 0, {data} was given"
                    )
                # ensure only one universe is given
                if (
                    len(data) >= 2
                    and isinstance(data[1], syntax_node.ValueNode)
                    and "(" != data[1].value
                ):
                    raise ValueError(
                        f"Fill cannot have two universes in this format. {data.format()} given"
                    )

        data = value["data"]
        if not isinstance(data, syntax_node.ListNode):
            data = data.nodes
        if "(" in data:
            get_universe(value)
            trans_data = value["data"][
                list(value["data"]).index("(") + 1 : list(value["data"]).index(")") - 1
            ]
            if len(trans_data) == 1:
                try:
                    transform = trans_data[0]
                    transform._convert_to_int()
                    assert transform.value > 0
                    self._hidden_transform = False
                    self._old_transform_number = transform
                except AssertionError as e:
                    raise ValueError(
                        "Transform number must be a positive integer. {words[0]} was given."
                    )
            elif len(trans_data) > 1:
                modifier = value["classifier"].modifier
                if modifier and "*" in modifier.value:
                    in_key = "*TR1"
                else:
                    in_key = "TR1"
                input_card = Input([in_key + " " + trans_data.format()], BlockType.DATA)
                self._transform = Transform(input_card, pass_through=True)
                self._hidden_transform = True

        else:
            get_universe(value)

    def _parse_matrix(self, value):
        """Parses a matrix fill of universes.

        Parameters
        ----------
        value : str
            the value in the cell
        """
        self._multi_universe = True
        words = value["data"]
        self._min_index = np.zeros((3,), dtype=np.dtype(int))
        self._max_index = np.zeros((3,), dtype=np.dtype(int))
        limits_iter = (
            it.islice(words, 0, None, 3),
            it.islice(words, 1, None, 3),
            it.islice(words, 2, None, 3),
        )
        for axis, min_val, seperator, max_val in zip(
            Fill.DIMENSIONS.values(), *limits_iter
        ):
            for val, limit_holder in zip(
                (min_val, max_val), (self._min_index, self._max_index)
            ):
                try:
                    val._convert_to_int()
                    limit_holder[axis] = val.value
                except ValueError as e:
                    raise ValueError(
                        f"The lattice limits must be an integer. {val.value} was given"
                    )
        for min_val, max_val in zip(self.min_index, self.max_index):
            if min_val > max_val:
                raise ValueError(
                    "The minimum value must be smaller than the max value."
                    f"Min: {min_val}, Max: {max_val}, Input: {value.format()}"
                )
        self._old_numbers = np.zeros(self._sizes, dtype=np.dtype(int))
        words = iter(words[9:])
        for k in self._axis_range(2):
            for j in self._axis_range(1):
                for i in self._axis_range(0):
                    val = next(words)
                    try:
                        val._convert_to_int()
                        assert val.value >= 0
                        self._old_numbers[i][j][k] = val.value
                    except (ValueError, AssertionError) as e:
                        raise ValueError(
                            f"Values provided must be valid universes. {val.value} given."
                        )

    @staticmethod
    def _class_prefix():
        return "fill"

    @staticmethod
    def _has_number():
        return False

    @staticmethod
    def _has_classifier():
        return 0

    @property
    def universe(self):
        """The universe that this cell will be filled with.

        Only returns a value when :func:`multiple_universes` is False, otherwise none.

        Returns
        -------
        Universe
            the universe that the cell will be filled with, or None
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
        self._universe = value

    @universe.deleter
    def universe(self):
        self._universe = None

    @property
    def universes(self):
        """The universes that this cell will be filled with in a lattice.

        Only returns a value when :func:`multiple_universes` is true, otherwise none.

        Returns
        -------
        np.ndarray
            the universes that the cell will be filled with as a 3-D
            array.
        """
        if self.multiple_universes:
            return self._universes

    @universes.setter
    def universes(self, value):
        if not isinstance(value, (np.ndarray, type(None))):
            raise TypeError(f"Universes must be set to an array. {value} given.")
        if value.ndim != 3:
            raise ValueError(
                f"3D array must be given for fill.universes. Array of shape: {value.shape} given."
            )

        def is_universes(array):
            type_checker = lambda x: isinstance(x, (Universe, type(None)))
            return map(type_checker, array.flat)

        if value.dtype != np.object_ or not all(is_universes(value)):
            raise TypeError(
                f"All values in array must be a Universe (or None). {value} given."
            )
        self.multiple_universes = True
        if self.min_index is None:
            self.min_index = np.array([0] * 3)
        self.max_index = self.min_index + np.array(value.shape) - 1
        self._universes = value

    @universes.deleter
    def universes(self):
        self._universes = None

    @make_prop_pointer(
        "_min_index",
        (list, np.ndarray),
        validator=_verify_3d_index,
        deletable=True,
    )
    def min_index(self):
        """The minimum indices of the matrix in each dimension.

        For the order of the indices see: ``DIMENSIONS``.

        Returns
        -------
        :class:`numpy.ndarry`
            the minimum indices of the matrix for complex fills
        """
        pass

    @make_prop_pointer(
        "_max_index",
        (list, np.ndarray),
        validator=_verify_3d_index,
        deletable=True,
    )
    def max_index(self):
        """The maximum indices of the matrix in each dimension.

        For the order of the indices see: ``DIMENSIONS``.

        Returns
        -------
        :class:`numpy.ndarry`
            the maximum indices of the matrix for complex fills
        """
        pass

    @property
    def multiple_universes(self):
        """Whether or not this cell is filled with multiple universes in a matrix.

        Returns
        -------
        bool
            True if this cell contains multiple universes
        """
        return self._multi_universe

    @multiple_universes.setter
    def multiple_universes(self, value):
        if not isinstance(value, bool):
            raise TypeError("Multiple_univeses must be set to a bool")
        self._multi_universe = value

    @make_prop_val_node("_old_number")
    def old_universe_number(self):
        """The number of the universe that this is filled by taken from the input.

        Returns
        -------
        int
            the old universe number
        """
        pass

    @property
    def old_universe_numbers(self):
        """The numbers of the universes that this is filled by taken from the input.

        Returns
        -------
        :class:`numpy.ndarray`
            the old universe numbers
        """
        if isinstance(self._old_numbers, list):
            return [
                num.value if isinstance(num, syntax_node.ValueNode) else num
                for num in self._old_numbers
            ]
        return self._old_numbers

    @property
    def hidden_transform(self):
        """Whether or not the transform used is hidden.

        This is true when an unnumbered transform is used
        e.g., ``FILL=1 (1.0 2.0 3.0)``.

        Returns
        -------
        bool
            True iff the transform used is hidden
        """
        return self._hidden_transform

    @property
    def has_information(self):
        if self.in_cell_block:
            return self.universe is not None or self.universes is not None

    @property
    def _tree_value(self):
        if self.transform or self.multiple_universes:
            raise ValueError(
                f"Fill can not be in the data block if"
                " fill transforms and other complex inputs are used."
            )
        val = self._old_number
        val.value = self.universe.number if self.universe else None
        return val

    @property
    def transform(self):
        """The transform for this fill (if any).

        Returns
        -------
        Transform
            the transform for the filling universe for this cell.
        """
        return self._transform

    @transform.setter
    def transform(self, value):
        if not isinstance(value, (Transform, type(None))):
            raise TypeError("Transform must be set to a Transform.")
        self._transform = value
        if value is not None:
            self._hidden_transform = value.hidden_transform
        else:
            self._hidden_transform = False

    @transform.deleter
    def transform(self):
        self._transform = None

    @make_prop_val_node("_old_transform_number")
    def old_transform_number(self):
        """The number of the transform specified in the input.

        Returns
        -------
        int
            the original number for the transform from the input.
        """
        pass

    def merge(self, other):
        raise MalformedInputError(
            other._input, "Cannot have two lattice inputs for the problem"
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
            if not self.set_in_cell_block and self.old_universe_numbers:
                for cell, old_number in zip(self._problem.cells, self._old_numbers):
                    if not isinstance(old_number, Jump):
                        cell._fill._old_number = old_number
            for cell in self._problem.cells:
                cell._fill.push_to_cells()

    def _clear_data(self):
        self._old_number = None
        self._universe = None

    def _axis_range(self, axis):
        """Returns an iterator for iterating over the given axis.

        Parameters
        ----------
        axis : int
            the number of the axis to iterate over

        Returns
        -------
        unknown
            range
        """
        return range(self._axis_size(axis))

    def _axis_size(self, axis):
        """Get the length of the given axis.

        Parameters
        ----------
        axis : int
            the axis to probe into.

        Returns
        -------
        int
            the length of the given axis of the universe matrix.
        """
        return int(self.max_index[axis] - self.min_index[axis]) + 1

    @property
    def _sizes(self):
        """The axis sizes of the matrix.

        Returns
        -------
        tuple
            a tuple of the matrix shape.
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

    def _update_cell_values(self):
        new_vals = list(self._tree["data"])
        if self.transform and self.transform.is_in_degrees:
            self._tree["classifier"].modifier = "*"
        else:
            self._tree["classifier"].modifier = None
        new_vals = self._update_cell_universes(new_vals)
        self._update_cell_transform_values(new_vals)

    def _update_cell_transform_values(self, new_vals):
        if self.transform is None:
            try:
                values = [val.value for val in self._tree["data"]]
                start = values.index("(")
                end = values.index(")")
                del new_vals[start : end + 1]
            except ValueError:
                pass
        # Update transforms
        else:
            start = -1
            end = -1
            try:
                values = [val.value for val in self._tree["data"]]
                start = values.index("(")
                end = values.index(")")
            except ValueError:
                pass
            if self.transform.hidden_transform:
                self.transform._update_values()
                payload = list(self.transform._tree["data"])
            else:
                # if started with named transform
                if start > 0 and end > 0 and ((end - start) - 1 == 1):
                    payload = [self._tree["data"][start + 1]]
                else:
                    payload = [syntax_node.ValueNode("1", int)]
                payload[0].value = self.transform.number
            if start > 0 and end > 0:
                new_vals = new_vals[: start + 1] + payload + new_vals[end:]
        self._tree["data"].update_with_new_values(new_vals)

    def _update_cell_universes(self, new_vals):
        def _value_node_generator():
            while True:
                value = syntax_node.ValueNode("1", int)
                padding = syntax_node.PaddingNode(" ")
                value.padding = padding
                yield value

        if self.multiple_universes:
            payload = []
            get_number = np.vectorize(lambda u: u.number)
            payload = get_number(self.universes).T.ravel()
        else:
            payload = [
                (
                    self.universe.number
                    if self.universe is not None
                    else self.old_universe_number
                )
            ]
        try:
            start_transform = new_vals.index("(")
        except ValueError:
            start_transform = None

        reverse_list = new_vals.copy()
        reverse_list.reverse()
        try:
            start_matrix = len(new_vals) - reverse_list.index(":") + 1
        except ValueError:
            start_matrix = 0
        value_nodes = it.chain(
            new_vals[start_matrix:start_transform], _value_node_generator()
        )
        buffer = []
        for universe, value in zip(payload, value_nodes):
            value.value = universe
            buffer.append(value)
        buffer = self._update_multi_index_limits(new_vals[:start_matrix]) + buffer
        if start_transform:
            buffer += new_vals[start_transform:]
        return buffer

    def _update_multi_index_limits(self, new_vals):
        if not self.multiple_universes and ":" not in new_vals:
            return new_vals
        if ":" not in new_vals:
            for min_idx, max_idx in zip(self.min_index, self.max_index):
                new_vals.extend(
                    [
                        self._generate_default_node(int, str(min_idx), padding=None),
                        syntax_node.PaddingNode(":"),
                        self._generate_default_node(int, str(max_idx), padding=" "),
                    ]
                )
            return new_vals
        vals_iter = iter(new_vals)
        for min_idx, max_idx in zip(self.min_index, self.max_index):
            min_val = next(vals_iter)
            min_val.value = min_idx
            next(vals_iter)
            max_val = next(vals_iter)
            max_val.value = max_idx
        return new_vals

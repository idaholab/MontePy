# Copyright 2024 - 2025, Battelle Energy Alliance, LLC All Rights Reserved.
from __future__ import annotations
import itertools as it
import numpy as np

import montepy
from montepy.utilities import *
from montepy.data_inputs.cell_modifier import (
    CellModifierInput,
    InitInput,
    cell_mod_prop,
)
from montepy.data_inputs.transform import Transform
from montepy.exceptions import *
from montepy.input_parser.block_type import BlockType
from montepy.input_parser.mcnp_input import Input, Jump
from montepy.input_parser import syntax_node
from montepy.mcnp_object import MCNP_Object
import montepy.types as ty
from montepy.universe import Universe
from montepy.utilities import *


def _verify_3d_index(self, indices):
    for index in indices:
        if not isinstance(index, ty.Integral):
            raise TypeError(f"Index values for fill must be an int. {index} given.")
    if len(indices) != 3:
        raise ValueError(f"3 values must be given for fill. {indices} given")


class Fill(CellModifierInput):
    """Object to handle the ``FILL`` input in cell and data blocks.

    Parameters
    ----------
    input : Input | str
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

    def _init_blank(self):
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

    def _parse_cell_tree(self):
        if self._in_key:
            self._parse_cell_input(self._in_key, self._in_value)

    def _parse_data_tree(self):
        self._old_numbers = []
        values = self.data
        for value in values:
            try:
                value.convert_to_int()
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
        classifier = syntax_node.ClassifierNode()
        classifier.prefix = self._generate_default_node(
            str, self._class_prefix().upper(), None, never_pad=True
        )
        self._tree = syntax_node.SyntaxNode(
            "fill",
            {
                "classifier": classifier,
                "param_seperator": self._generate_default_node(str, "=", None),
                "data": self._generate_cell_data_tree(),
            },
        )

    @staticmethod
    def _generate_cell_data_tree() -> syntax_node.SyntaxNode:
        """
        Generates a default syntax tree for the data of a cell fill (indices, universes, transform).
        """
        return syntax_node.SyntaxNode(
            "cell fill",
            {
                "indices": syntax_node.ListNode("fill indices"),
                "universes": syntax_node.ListNode("fill universes"),
                "transform": syntax_node.ListNode("fill transform"),
            },
        )

    def _precondition_tree(self, data: syntax_node.ListNode) -> syntax_node.SyntaxNode:
        """
        Converts a listNode payload (if only one universe is given) to the proper syntax tree.
        """
        new_data = self._generate_cell_data_tree()
        new_data.nodes["universes"] = data
        self._tree.nodes["data"] = new_data
        return new_data

    def _parse_cell_input(self, key: str, value: str):
        """Parses the information provided in the cell input.

        Parameters
        ----------
        key : str
            The key given in the cell
        value : str
            the value given in the cell
        """
        data = value["data"]
        if not isinstance(data, syntax_node.SyntaxNode):
            data = self._precondition_tree(data)
        if len(data["indices"]) > 0:
            self._parse_matrix(value)
        else:
            uni_data = data["universes"]
            try:
                val = uni_data[0]
                val.convert_to_int()
                assert val.value >= 0
                self._old_number = val
            except (TypeError, AssertionError) as e:
                raise ValueError(
                    f"The fill universe must be a valid integer ≥ 0, {data} was given"
                )
            # ensure only one universe is given
            if len(uni_data) >= 2:
                raise ValueError(
                    f"Fill cannot have two universes in this format. {data.format()} given"
                )
        if len(data["transform"]) > 0:
            trans_data = data["transform"][1:-1]
            if len(trans_data) == 1:
                try:
                    transform = trans_data[0]
                    transform.convert_to_int()
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
                input = Input([in_key + " " + trans_data.format()], BlockType.DATA)
                self._transform = Transform(input, pass_through=True)
                self._hidden_transform = True

    def _parse_matrix(self, value: syntax_node.SyntaxNode):
        """Parses a matrix fill of universes.

        Parameters
        ----------
        value : SyntaxNode
            the value in the cell
        """
        self._multi_universe = True
        words = value["data"]["indices"]
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
                    val.convert_to_int()
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
        words = iter(value["data"]["universes"])
        new_nodes = []
        for k in self._axis_range(2):
            for j in self._axis_range(1):
                for i in self._axis_range(0):
                    try:
                        try:
                            val = next(words)
                        # if ended early
                        except StopIteration:
                            words = it.cycle([None])
                            val = None
                        if val is None:
                            val = self._generate_default_node(int, None)
                            new_nodes.append(val)
                        else:
                            val.convert_to_int()
                            assert val.value >= 0
                        self._old_numbers[i][j][k] = val.value if val.value else 0
                    except (ValueError, AssertionError) as e:
                        raise ValueError(
                            f"Values provided must be valid universes. {val.value} given."
                        )

        # inset new nodes
        for new_node in new_nodes:
            value["data"]["universes"].append(new_node)

    @staticmethod
    def _class_prefix():
        return "fill"

    @staticmethod
    def _has_number():
        return False

    @staticmethod
    def _has_classifier():
        return 0

    @cell_mod_prop("_fill")
    @prop_pointer_from_problem("_universe", "old_universe_number", "universes")
    @needs_full_ast
    def universe(self) -> Universe:
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
    @needs_full_cst
    @args_checked
    def universe(self, value: Universe = None):
        if self.multiple_universes:
            raise ValueError(
                "A single universe can only be set when multiple_universes is False."
            )
        self._universe = value
        if value is not None:
            self._universes = None
            self.multiple_universes = False

    @universe.deleter
    @needs_full_cst
    def universe(self):
        self._universe = None

    @property
    @needs_full_ast
    def universes(self) -> np.ndarray[Universe]:
        """The universes that this cell will be filled with in a lattice.

        Only returns a value when :func:`multiple_universes` is true, otherwise none.

        Arrays with fewer than 3 dimensions are automatically expanded to 3D by adding dimensions at the end (e.g., a 1D array of shape (N,) becomes (N, 1, 1) and a 0D array becomes (1, 1, 1)).


        Returns
        -------
        np.ndarray[Universe]
            the universes that the cell will be filled with as a 3-D
            array.


        See Also
        --------

        * :manual631sub:`5.5.5.3`
        * :manual63sub:`5.5.5.3`
        * :manual62:`87`


        .. versionchanged:: 1.2.0

            * Now supports setting the universes with a numpy array of up to 3-dimensional universe IDs.
            * Automatic expansion of lower-dimensional arrays to 3D



        Examples
        --------
        Setting the universes with a numpy array of universe IDs:

        >>> import montepy
        >>> import numpy as np
        >>> problem = montepy.MCNP_Problem("")
        >>> cell = montepy.Cell()
        >>> cell.number = 1
        >>> problem.cells.append(cell)
        >>> u1 = montepy.Universe(number=1)
        >>> u2 = montepy.Universe(number=2)
        >>> problem.universes.append(u1)
        >>> problem.universes.append(u2)
        >>> cell.fill.universes = np.array([[[1, 2, 0]]])
        >>> cell.fill.universes[0, 0, 0]
        Universe: Number: 1 Problem: set, Cells: []
        >>> cell.fill.universes[0, 0, 1]
        Universe: Number: 2 Problem: set, Cells: []
        >>> print(cell.fill.universes[0, 0, 2])
        None

        Arrays with fewer than 3 dimensions are expanded to 3D:

        >>> cell.fill.universes = np.array([1, 2])  # 1D array
        >>> cell.fill.universes.shape
        (2, 1, 1)
        >>> cell.fill.universes = np.array([[1, 2]])  # 2D array
        >>> cell.fill.universes.shape
        (1, 2, 1)
        >>> cell.fill.universes = np.array(1)  # 0D array
        >>> cell.fill.universes.shape
        (1, 1, 1)




        Parameters
        ----------
        value : np.ndarray or None
            A 3D numpy array of :class:`~montepy.universe.Universe` objects,
            a 3D numpy array of integer universe IDs, or None to clear the
            universes. Arrays with 0, 1, or 2 dimensions are automatically
            expanded to 3D by adding dimensions at the end.
        """
        if self.multiple_universes:
            if self._universes is None:
                if not self._problem:
                    raise IllegalState(
                        f"Can't find Universes for a fill detached from a problem"
                    )
                self._universes = np.empty_like(self._old_numbers, dtype="O")
                for coord, old_num in np.ndenumerate(self._old_numbers):
                    self._universes[coord] = self._problem.universes[old_num]
            return self._universes
        return None

    @universes.setter
    @needs_full_cst
    @args_checked
    def universes(self, value: np.ndarray[Universe | ty.NonNegativeInt] = None):
        if value is None:
            self.multiple_universes = False
            self.universe = None
            self._universes = None
            return

        if value.ndim <= 2:
            for _ in range(3 - value.ndim):
                value = np.expand_dims(value, axis=value.ndim)

        elif value.ndim > 3:
            raise ValueError(
                f"3D array must be given for fill.universes. Array of shape: {value.shape} given."
            )

        # Setting by universe IDs
        if np.issubdtype(value.dtype, np.integer):
            if self._problem is None:
                raise IllegalState(
                    "Universe IDs can only be set if the Fill is part of a Problem."
                )

            universes_array = np.empty(value.shape, dtype=object)
            for idx_tuple, uid in np.ndenumerate(value):
                if uid == 0:
                    universes_array[idx_tuple] = None
                else:
                    try:
                        universes_array[idx_tuple] = self._problem.universes[uid]
                    except KeyError as e:
                        raise KeyError(
                            f"Universe ID {uid} at index {idx_tuple} is not defined in the problem."
                        ) from e
            value = universes_array

        def is_universes(array):
            type_checker = lambda x: isinstance(x, (Universe, type(None)))
            return map(type_checker, array.flat)

        self.multiple_universes = True
        self._universe = None
        if self.min_index is None:
            self.min_index = np.array([0] * 3)
        self.max_index = self.min_index + np.array(value.shape) - 1
        self._universes = value

    @universes.deleter
    @needs_full_cst
    def universes(self):
        self._universes = None
        self.multiple_universes = False

    @make_prop_pointer(
        "_min_index",
        (list, np.ndarray),
        validator=_verify_3d_index,
        deletable=True,
    )
    @needs_full_ast
    def min_index(self) -> np.ndarray[ty.Integral]:
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
    @needs_full_ast
    def max_index(self) -> np.ndarray[ty.Integral]:
        """The maximum indices of the matrix in each dimension.

        For the order of the indices see: ``DIMENSIONS``.

        Returns
        -------
        :class:`numpy.ndarry`
            the maximum indices of the matrix for complex fills
        """
        pass

    @property
    @needs_full_ast
    def multiple_universes(self) -> bool:
        """Whether or not this cell is filled with multiple universes in a matrix.

        Returns
        -------
        bool
            True if this cell contains multiple universes
        """
        return self._multi_universe

    @multiple_universes.setter
    @needs_full_cst
    @args_checked
    def multiple_universes(self, value: bool):
        self._multi_universe = value
        if not value:
            self._universes = None

    @make_prop_val_node("_old_number")
    @needs_full_ast
    def old_universe_number(self) -> int:
        """The number of the universe that this is filled by taken from the input.

        Returns
        -------
        int
            the old universe number
        """
        pass

    @property
    @needs_full_ast
    def old_universe_numbers(self) -> np.ndarray[int]:
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
    @needs_full_ast
    def hidden_transform(self) -> bool:
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
    def has_information(self) -> bool:
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

    @prop_pointer_from_problem("_transform", "old_transform_number", "transforms")
    @needs_full_ast
    def transform(self) -> montepy.Transform:
        """The transform for this fill (if any).

        Returns
        -------
        Transform
            the transform for the filling universe for this cell.
        """
        return self._transform

    @transform.setter
    @needs_full_cst
    @args_checked
    def transform(self, value: Transform = None):
        self._transform = value
        if value is not None:
            self._hidden_transform = value.hidden_transform
        else:
            self._hidden_transform = False
            self._old_transform_number.value = None

    @transform.deleter
    @needs_full_cst
    def transform(self):
        self._transform = None

    @make_prop_val_node("_old_transform_number")
    @needs_full_ast
    def old_transform_number(self):
        """The number of the transform specified in the input.

        Returns
        -------
        int
            the original number for the transform from the input.
        """
        pass

    @args_checked
    def merge(self, other: Fill):
        raise MalformedInputError(
            other._input, "Cannot have two lattice inputs for the problem"
        )

    @needs_full_ast
    def push_to_cells(self):
        if not self.set_in_cell_block and self.old_universe_numbers:
            for cell, old_number in zip(self._problem.cells, self._old_numbers):
                if not isinstance(old_number, Jump):
                    cell._fill._accept_from_data(old_number)

    def _accept_and_update(self, value):
        self._old_number = value

    def _clear_data(self):
        self._old_number = None
        self._universe = None

    def _axis_range(self, axis) -> range:
        """Returns an iterator for iterating over the given axis.

        Parameters
        ----------
        axis : int
            the number of the axis to iterate over

        Returns
        -------
        range
        """
        return range(self._axis_size(axis))

    def _axis_size(self, axis: ty.Integral) -> int:
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
    def _sizes(self) -> tuple[int, int, int]:
        """The axis sizes of the matrix.

        Returns
        -------
        tuple
            a tuple of the matrix shape.
        """
        return (self._axis_size(0), self._axis_size(1), self._axis_size(2))

    def _update_cell_values(self):
        if self._transform and self.transform.is_in_degrees:
            self._tree["classifier"].modifier = "*"
        else:
            self._tree["classifier"].modifier = None
        self._update_cell_transform_values()
        self._update_cell_universes()
        self._update_multi_index_limits()

    def _update_cell_transform_values(self):
        """
        Updates cell fill tree with the new transform data.
        """
        old_vals = self._tree["data"]["transform"]
        if self._transform is None and self.old_transform_number is None:
            old_vals.nodes.clear()
            new_vals = []
        # Update transforms
        else:
            if self.hidden_transform:
                self.transform._update_values()
                payload = list(self.transform._tree["data"])
            else:
                # if started with named transform
                payload = [self._tree["data"]["transform"][1]]
                payload[0].value = self.transform.number
            new_vals = [old_vals[0]] + payload + [old_vals[-1]]
        self._tree["data"]["transform"].update_with_new_values(new_vals)

    def _update_cell_universes(self):
        """
        Updates cell fill tree with the universe(s) data.
        """
        tree = self._tree["data"]["universes"]

        def _value_node_generator():
            while True:
                value = syntax_node.ValueNode(None, int)
                padding = syntax_node.PaddingNode(" ")
                value.padding = padding
                yield value

        if self.multiple_universes:
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
        value_nodes = it.chain(tree, _value_node_generator())
        buffer = []
        for universe, value in zip(payload, value_nodes):
            value.value = universe
            buffer.append(value)
        # drop blank values from original
        for back_idx, node in enumerate(reversed(list(buffer))):
            # if we should keep something on the right side
            if node.value or node.token is not None:
                break
        buffer = buffer[: len(buffer) - back_idx]
        tree.update_with_new_values(buffer)

    def _update_multi_index_limits(self):
        """
        Updates cell fill tree with the indices limit for a multi-universe fill.
        """
        base_tree = self._tree["data"]["indices"]
        # clear out old indices if not being used
        if not self.multiple_universes:
            base_tree.nodes.clear()
            return
        # Need (3 dimensions) x (3 nodes [#, :, #]) for all indices
        if len(base_tree) != 9:
            base_tree.nodes.clear()
            # create blank tree
            for _ in range(3):
                base_tree.append(syntax_node.ValueNode(None, int, never_pad=True))
                base_tree.append(syntax_node.PaddingNode(":"))
                base_tree.append(syntax_node.ValueNode(None, int))
        # iterate through starting index of each dimension (3 nodes per dimension)
        for dimension, base_idx in enumerate(range(0, 8, 3)):
            base_tree[base_idx].value = self.min_index[dimension]
            base_tree[base_idx + 2].value = self.max_index[dimension]

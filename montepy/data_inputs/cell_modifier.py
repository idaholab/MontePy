# Copyright 2024 - 2025, Battelle Energy Alliance, LLC All Rights Reserved.
from __future__ import annotations

import montepy
from montepy.utilities import *
from montepy.data_inputs.data_input import DataInputAbstract, InitInput
from montepy.input_parser import syntax_node
from montepy.input_parser.block_type import BlockType
from montepy.input_parser.mcnp_input import Input, Jump
import montepy.types as ty

from abc import abstractmethod
import typing
import warnings


def cell_mod_prop(
    cells_param,
):
    """
    Decorator for tying a cell modifier property to the parent cells object to pull from data block.
    """

    def decorator(func):
        # must decorate a property
        assert isinstance(func, property)
        base_prop = func

        def getter(self):
            if self._problem:
                data_version = getattr(self._problem.cells, cells_param)
                if data_version._input is not None and not data_version.fully_parsed:
                    data_version.full_parse()
                    data_version.push_to_cells()
            return base_prop.fget(self)

        return property(getter, base_prop.fset, base_prop.fdel)

    return decorator


class CellModifierInput(DataInputAbstract):
    """Abstract Parent class for Data Inputs that modify cells / geometry.

    Examples: IMP, VOL, etc.

    .. versionchanged:: 1.6.0b1

        Added ``jit_parse`` parameter

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
    problem: MCNP_Problem
        the base problem to be linked to.
    jit_parse : bool
        Parse the object just-in-time, when the information is actually needed, if True.
    """

    @args_checked
    def __init__(
        self,
        input: InitInput = None,
        in_cell_block: bool = False,
        key: str = None,
        value: syntax_node.SyntaxNode = None,
        *,
        problem: montepy.MCNP_Problem = None,
        jit_parse: bool = True,
        **kwargs,
    ):
        self._problem_ref = None
        self._parameters = syntax_node.ParametersNode()
        self._input = None
        self._init_blank()
        fast_parse = False
        if key and value:
            input = Input([key], BlockType.DATA)
            fast_parse = True
        self._in_cell_block = in_cell_block
        self._in_key = key
        self._in_value = value
        if key and in_cell_block:
            self._set_in_cell_block = True
            self._tree = value
            self._data = value["data"]
        else:
            self._set_in_cell_block = False
        if problem:
            self.link_to_problem(problem)
        if input is None and value is None:
            self._generate_default_tree(**kwargs)
            self._parse_tree()
        # handle cell parsing
        elif value is not None:
            self._parse_classifier(input, self._parse_input, jit_parse=jit_parse)
            self._tree = value
            self._parse_tree()
        else:
            super().__init__(input, jit_parse=jit_parse)
        if jit_parse:
            self._not_parsed = True

    def _jit_light_init(self, input):
        super()._jit_light_init(input)
        if "start_pad" not in self._tree:
            from montepy.input_parser.syntax_node import PaddingNode, SyntaxNode

            self._tree = SyntaxNode(
                self._tree.name,
                {"start_pad": PaddingNode(), **self._tree.nodes},
            )
            self._start_pad = self._tree["start_pad"]
        return self

    def _parse_tree(self):
        super()._parse_tree()
        if self.in_cell_block:
            self._parse_cell_tree()
        else:
            self._parse_data_tree()
            self.push_to_cells()

    @abstractmethod
    def _parse_cell_tree(self):
        pass

    @abstractmethod
    def _parse_data_tree(self):
        pass

    _KEYS_TO_PRESERVE = {"_parked_value"}

    def full_parse(self):
        if hasattr(self, "_not_parsed") and self._not_parsed:
            del self._not_parsed
            problem = self._problem
            old_data = {
                k: getattr(self, k, None)
                for k in self._KEYS_TO_PRESERVE
                if getattr(self, k, None)
            }
            # Preserve leading comments stored in the JIT tree's start_pad so they
            # survive the __init__ reinit below.
            jit_start_pad_nodes = None
            if hasattr(self, "_tree") and "start_pad" in self._tree:
                nodes = list(self._tree["start_pad"].nodes)
                if nodes:
                    jit_start_pad_nodes = nodes
            if self.in_cell_block:
                self.__init__(
                    in_cell_block=True,
                    key=self._in_key,
                    value=self._in_value,
                    jit_parse=False,
                )
            else:
                self.__init__(self._input, jit_parse=False)
            [setattr(self, k, v) for k, v in old_data.items()]
            if jit_start_pad_nodes and "start_pad" in self._tree:
                self._tree["start_pad"]._nodes = jit_start_pad_nodes + list(
                    self._tree["start_pad"].nodes
                )
            if hasattr(self, "_parked_value"):
                try:
                    self._accept_and_update(self._parked_value)
                except (ValueError, TypeError) as e:
                    raise type(e)(
                        f"Invalid value given for data block input for {type(self).__name__}. "
                        f"Original error: {e}"
                    ) from e
            if problem:
                self.link_to_problem(problem)
                if not self.in_cell_block and self._input is not None:
                    self.push_to_cells()

    def _generate_default_tree(self):
        if self.in_cell_block:
            self._generate_default_cell_tree()
        else:
            self._generate_default_data_tree()

    @abstractmethod
    def _generate_default_cell_tree(self):
        pass

    def _generate_default_data_tree(self):
        list_node = syntax_node.ListNode("number sequence")
        list_node.append(self._generate_default_node(float, None))
        classifier = syntax_node.ClassifierNode()
        classifier.prefix = self._generate_default_node(
            str, self._class_prefix().upper(), None
        )
        classifier.padding = syntax_node.PaddingNode(" ")
        self._tree = syntax_node.SyntaxNode(
            self._class_prefix(),
            {
                "start_pad": syntax_node.PaddingNode(),
                "classifier": classifier,
                "keyword": syntax_node.ValueNode(None, str, None),
                "data": list_node,
            },
        )

    @property
    def in_cell_block(self) -> bool:
        """True if this object represents an input from the cell block section of a file.

        Returns
        -------
        bool
        """
        return self._in_cell_block

    @property
    def set_in_cell_block(self) -> bool:
        """True if this data were set in the cell block in the input"""
        return self._set_in_cell_block

    @abstractmethod
    def merge(self, other: typing.Self):
        """Merges the data from another card of same type into this one.

        Parameters
        ----------
        other : CellModifierInput
            The other object to merge into this object.

        Raises
        ------
        MalformedInputError
            if two objects cannot be merged.
        """
        pass

    def link_to_problem(self, problem, *, deepcopy: bool = False):
        super().link_to_problem(problem)
        if (
            not deepcopy
            and problem
            and not hasattr(self, "_not_parsed")
            and self.set_in_cell_block
        ):
            self._problem.print_in_data_block[self._class_prefix()] = False

    def _accept_from_data(self, value):
        if hasattr(self, "_not_parsed"):
            self._parked_value = value
        else:
            self._accept_and_update(value)

    @abstractmethod
    def _accept_and_update(self, value):
        pass

    @abstractmethod
    def push_to_cells(self):
        """After being linked to the problem update all cells attributes with this data.

        This needs to also check that none of the cells had data provided in the cell block
        (check that ``set_in_cell_block`` isn't set).
        Use ``self._check_redundant_definitions`` to do this.

        Raises
        ------
        MalformedInputError
            When data are given in the cell block and the data block.
        """
        pass

    @property
    @abstractmethod
    def has_information(self) -> bool:
        """For a cell instance of :class:`montepy.data_inputs.cell_modifier.CellModifierInput` returns True iff there is information here worth printing out.

        e.g., a manually set volume for a cell

        Returns
        -------
        bool
            True if this instance has information worth printing.
        """
        pass

    def _check_redundant_definitions(self):
        """Checks that data wasn't given in data block and the cell block."""
        import re

        attr, _ = montepy.Cell._INPUTS_TO_PROPERTY[type(self)]
        if not self._in_cell_block and self._problem:
            cells = self._problem.cells
            prefix = type(self)._class_prefix()
            jit_pattern = re.compile(rf"\b{re.escape(prefix)}\b", re.IGNORECASE)
            for cell in cells:
                if hasattr(cell, "_not_parsed"):
                    if cell.search(jit_pattern):
                        cell.full_parse()
                        if not getattr(cell, attr).set_in_cell_block:
                            continue
                    else:
                        continue
                if getattr(cell, attr).set_in_cell_block:
                    raise montepy.exceptions.MalformedInputError(
                        cell._input,
                        f"Cell: {cell.number} provided {self._class_prefix().upper()}"
                        " data when those data were in the data block",
                    )

    @abstractmethod
    def _clear_data(self):
        """After data has been pushed to cells, delete internal data to avoid inadvertent editing.

        This is only called on data-block instances of this object.
        """
        pass

    @property
    def _is_worth_printing(self) -> bool:
        """Determines if this object has information that is worth printing in the input file.

        Uses the :func:`has_information` property for all applicable cell(s)

        Returns
        -------
        bool
            True if this object should be included in the output
        """
        if self.in_cell_block:
            # if has to be all or nothing printed
            if (
                hasattr(self, "_ALL_OR_NOTHING")
                and self._problem
                and self._problem.print_in_data_block._get_all_or_none(
                    self._class_prefix()
                )
            ):
                return True
            return self.has_information
        attr, _ = montepy.Cell._INPUTS_TO_PROPERTY[type(self)]
        if len(self.data) > 1 or (
            len(self.data) == 1
            and self.data[0] is not None
            and self.data[0].value is not None
        ):
            return True
        if self._problem:
            for cell in self._problem.cells:
                if getattr(cell, attr).has_information:
                    return True
        return False

    @property
    @abstractmethod
    def _tree_value(self) -> syntax_node.ValueNode:
        """The ValueNode that holds the information for this instance, that should be included in the data block.

        Returns
        -------
        ValueNode
            The ValueNode to update the data-block syntax tree with.
        """
        pass

    def _collect_new_values(self) -> list[syntax_node.ValueNode]:
        """Gets a list of the ValueNodes that hold the information for all cells.

        This will be a list in the same order as :attr:`montepy.MCNP_Problem.cells`.

        Returns
        -------
        list[ValueNode]
            a list of the ValueNodes to update the data block syntax
            tree with
        """
        ret = []
        attr, _ = montepy.Cell._INPUTS_TO_PROPERTY[type(self)]
        for cell in self._problem.cells:
            input = getattr(cell, attr)
            if hasattr(input, "_not_parsed"):
                input.full_parse()
            ret.append(input._tree_value)
        return ret

    @abstractmethod
    def _update_cell_values(self):
        """Updates values in the syntax tree when in the cell block."""
        pass

    def _update_values(self):
        if self.in_cell_block:
            self._update_cell_values()
        else:
            new_vals = self._collect_new_values()
            self.data.update_with_new_values(new_vals)

    def _format_tree(self) -> str:
        """Formats the syntax tree for printing in an input file.

        By default this runs ``self._tree.format()``.

        Returns
        -------
        str
            a string of the text to write out to the input file (not
            wrapped yet for MCNP).
        """
        return self._tree.format()

    @args_checked
    def format_for_mcnp_input(
        self,
        mcnp_version: ty.VersionType,
        has_following: bool = False,
        always_print: bool = False,
    ) -> list[str]:
        """Creates a string representation of this MCNP_Object that can be
        written to file.

        Parameters
        ----------
        mcnp_version : ty.VersionType
            The tuple for the MCNP version that must be exported to.
        has_following: bool
            If true this is followed by another input, and a new line will be inserted if this ends in a comment.
        always_print: bool
            If true this will always produce a result irrespective of ``print_in_data_block``.

        Returns
        -------
        list
            a list of strings for the lines that this input will occupy.
        """
        if hasattr(self, "_not_parsed") and self._input is not None:
            # Only take the JIT fast-path when this modifier would actually be
            # printed here (in_cell_block XOR print_in_data_block).  Otherwise
            # fall through to full_parse so that push_to_cells runs and cell-
            # block values are available.
            if self._problem:
                _pidb = self._problem.print_in_data_block[self._class_prefix().upper()]
                if always_print or self.in_cell_block != _pidb:
                    return self._original_lines()
                # Not printing here; full_parse so push_to_cells fires below.
            else:
                return self._original_lines()
        self.validate()
        self._tree.check_for_graveyard_comments(has_following)
        if not self._problem:
            print_in_data_block = not self.in_cell_block
        else:
            print_in_data_block = self._problem.print_in_data_block[
                self._class_prefix().upper()
            ]

        """
        Boolean logic
        A = self.in_Cell_block
        B = print_in_data_block
        C = is_worth_printing

        Logic:
            1. A!BC + !ABC
            2. C *(A!B + !AB)
            3. C * (A xor B)
            4. C * (A != B)
        """
        # print in either block
        if always_print or (
            self.in_cell_block != print_in_data_block and self._is_worth_printing
        ):
            self._update_values()
            return self.wrap_string_for_mcnp(
                self._format_tree(),
                mcnp_version,
                True,
                suppress_blank_end=not self.in_cell_block,
            )
        return []

    def _original_lines(self):
        if self.in_cell_block:
            return self._tree.format().split("\n")
        if hasattr(self, "_not_parsed") and "start_pad" in self._tree:
            pad_str = self._tree["start_pad"].format()
            if pad_str.strip():
                pad_lines = [l for l in pad_str.split("\n") if l.strip()]
                return pad_lines + self._input.input_lines
        return self._input.input_lines

    @args_checked
    def mcnp_str(self, mcnp_version: ty.VersionType = None) -> str:
        """Returns a string of this input as it would appear in an MCNP input file.

        ..versionadded:: 1.0.0

        Parameters
        ----------
        mcnp_version: ty.VersionType
            The tuple for the MCNP version that must be exported to.

        Returns
        -------
        str
            The string that would have been printed in a file

        TODO: cellmodifier
        """
        if mcnp_version is None:
            if self._problem is not None:
                mcnp_version = self._problem.mcnp_version
            else:
                mcnp_version = montepy.MCNP_VERSION
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            return "\n".join(
                self.format_for_mcnp_input(mcnp_version, always_print=True)
            )

    def _repr_args(self):
        ret = []
        if self.in_cell_block:
            ret.append(f"in_cell_block={self._in_cell_block}")
            ret.append(f"key={self._in_key}")
            ret.append(f"value={self._in_value}")
        return ret

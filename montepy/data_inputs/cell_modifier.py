# Copyright 2024 - 2025, Battelle Energy Alliance, LLC All Rights Reserved.
from abc import abstractmethod
import montepy
from montepy.data_inputs.data_input import DataInputAbstract, InitInput
from montepy.input_parser import syntax_node
from montepy.input_parser.block_type import BlockType
from montepy.input_parser.mcnp_input import Input, Jump
import warnings


class CellModifierInput(DataInputAbstract):
    """Abstract Parent class for Data Inputs that modify cells / geometry.

    Examples: IMP, VOL, etc.

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

    def __init__(
        self,
        input: InitInput = None,
        in_cell_block: bool = False,
        key: str = None,
        value: syntax_node.SyntaxNode = None,
    ):
        fast_parse = False
        if key and value:
            input = Input([key], BlockType.DATA)
            fast_parse = True
        super().__init__(input, fast_parse)
        if not isinstance(in_cell_block, bool):
            raise TypeError("in_cell_block must be a bool")
        if key and not isinstance(key, str):
            raise TypeError("key must be a str")
        if value and not isinstance(value, syntax_node.SyntaxNode):
            raise TypeError("value must be from a SyntaxNode")
        if not in_cell_block and not input:
            self._generate_default_data_tree()
        self._in_cell_block = in_cell_block
        self._in_key = key
        self._in_value = value
        if key and in_cell_block:
            self._set_in_cell_block = True
            self._tree = value
            self._data = value["data"]
        else:
            self._set_in_cell_block = False
            if in_cell_block and key is None and value is None:
                self._generate_default_cell_tree()

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
    def in_cell_block(self):
        """True if this object represents an input from the cell block section of a file.

        Returns
        -------
        bool
        """
        return self._in_cell_block

    @property
    def set_in_cell_block(self):
        """True if this data were set in the cell block in the input"""
        return self._set_in_cell_block

    @abstractmethod
    def merge(self, other):
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

    def link_to_problem(self, problem):
        super().link_to_problem(problem)
        if problem and not hasattr(self, "_not_parsed") and self.set_in_cell_block:
            self._problem.print_in_data_block[self._class_prefix()] = False

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
    def has_information(self):
        """For a cell instance of :class:`montepy.data_cards.cell_modifier.CellModifierCard` returns True iff there is information here worth printing out.

        e.g., a manually set volume for a cell

        Returns
        -------
        bool
            True if this instance has information worth printing.
        """
        pass

    def _check_redundant_definitions(self):
        """Checks that data wasn't given in data block and the cell block."""
        attr, _ = montepy.Cell._INPUTS_TO_PROPERTY[type(self)]
        if not self._in_cell_block and self._problem:
            cells = self._problem.cells
            for cell in cells:
                if getattr(cell, attr).set_in_cell_block:
                    raise montepy.errors.MalformedInputError(
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
    def _is_worth_printing(self):
        """Determines if this object has information that is worth printing in the input file.

        Uses the :func:`has_information` property for all applicable cell(s)

        Returns
        -------
        bool
            True if this object should be included in the output
        """
        if self.in_cell_block:
            return self.has_information
        attr, _ = montepy.Cell._INPUTS_TO_PROPERTY[type(self)]
        for cell in self._problem.cells:
            if getattr(cell, attr).has_information:
                return True
        return False

    @property
    @abstractmethod
    def _tree_value(self):
        """The ValueNode that holds the information for this instance, that should be included in the data block.

        Returns
        -------
        ValueNode
            The ValueNode to update the data-block syntax tree with.
        """
        pass

    def _collect_new_values(self):
        """Gets a list of the ValueNodes that hold the information for all cells.

        This will be a list in the same order as :func:`montepy.mcnp_problem.MCNP_Problem.cells`.

        Returns
        -------
        list
            a list of the ValueNodes to update the data block syntax
            tree with
        """
        ret = []
        attr, _ = montepy.Cell._INPUTS_TO_PROPERTY[type(self)]
        for cell in self._problem.cells:
            input = getattr(cell, attr)
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

    def _format_tree(self):
        """Formats the syntax tree for printing in an input file.

        By default this runs ``self._tree.format()``.

        Returns
        -------
        str
            a string of the text to write out to the input file (not
            wrapped yet for MCNP).
        """
        return self._tree.format()

    def format_for_mcnp_input(
        self,
        mcnp_version: tuple[int],
        has_following: bool = False,
        always_print: bool = False,
    ):
        """Creates a string representation of this MCNP_Object that can be
        written to file.

        Parameters
        ----------
        mcnp_version : tuple
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

    def mcnp_str(self, mcnp_version: tuple[int] = None):
        """Returns a string of this input as it would appear in an MCNP input file.

        ..versionadded:: 1.0.0

        Parameters
        ----------
        mcnp_version: tuple[int]
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

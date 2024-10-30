# Copyright 2024, Battelle Energy Alliance, LLC All Rights Reserved.
from abc import abstractmethod
import montepy
from montepy.data_inputs.data_input import DataInputAbstract
from montepy.input_parser import syntax_node
from montepy.input_parser.block_type import BlockType
from montepy.input_parser.mcnp_input import Input, Jump
import warnings


class CellModifierInput(DataInputAbstract):
    """
    Abstract Parent class for Data Inputs that modify cells / geometry.

    Examples: IMP, VOL, etc.

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
        """
        True if this object represents an input from the cell block section of a file.

        :rtype: bool
        """
        return self._in_cell_block

    @property
    def set_in_cell_block(self):
        """
        True if this data were set in the cell block in the input
        """
        return self._set_in_cell_block

    @abstractmethod
    def merge(self, other):
        """
        Merges the data from another card of same type into this one.

        :param other: The other object to merge into this object.
        :type other: CellModifierInput
        :raises MalformedInputError: if two objects cannot be merged.
        """
        pass

    def link_to_problem(self, problem):
        super().link_to_problem(problem)
        if problem and self.set_in_cell_block:
            self._problem.print_in_data_block[self._class_prefix()] = False

    @abstractmethod
    def push_to_cells(self):
        """
        After being linked to the problem update all cells attributes with this data.

        This needs to also check that none of the cells had data provided in the cell block
        (check that ``set_in_cell_block`` isn't set).
        Use ``self._check_redundant_definitions`` to do this.

        :raises MalformedInputError: When data are given in the cell block and the data block.
        """
        pass

    @property
    @abstractmethod
    def has_information(self):
        """
        For a cell instance of :class:`montepy.data_cards.cell_modifier.CellModifierCard` returns True iff there is information here worth printing out.

        e.g., a manually set volume for a cell

        :returns: True if this instance has information worth printing.
        :rtype: bool
        """
        pass

    def _check_redundant_definitions(self):
        """
        Checks that data wasn't given in data block and the cell block.
        """
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
        """
        After data has been pushed to cells, delete internal data to avoid inadvertent editing.

        This is only called on data-block instances of this object.
        """
        pass

    @property
    def _is_worth_printing(self):
        """
        Determines if this object has information that is worth printing in the input file.

        Uses the :func:`has_information` property for all applicable cell(s)

        :returns: True if this object should be included in the output
        :rtype: bool
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
        """
        The ValueNode that holds the information for this instance, that should be included in the data block.

        .. versionadded:: 0.2.0

        :returns: The ValueNode to update the data-block syntax tree with.
        :rtype: ValueNode
        """
        pass

    def _collect_new_values(self):
        """
        Gets a list of the ValueNodes that hold the information for all cells.

        This will be a list in the same order as :func:`montepy.mcnp_problem.MCNP_Problem.cells`.

        .. versionadded:: 0.2.0

        :returns: a list of the ValueNodes to update the data block syntax tree with
        :rtype: list
        """
        ret = []
        attr, _ = montepy.Cell._INPUTS_TO_PROPERTY[type(self)]
        for cell in self._problem.cells:
            input = getattr(cell, attr)
            ret.append(input._tree_value)
        return ret

    @abstractmethod
    def _update_cell_values(self):
        """
        Updates values in the syntax tree when in the cell block.

        .. versionadded:: 0.2.0
        """
        pass

    def _update_values(self):
        if self.in_cell_block:
            self._update_cell_values()
        else:
            new_vals = self._collect_new_values()
            self.data.update_with_new_values(new_vals)

    def _format_tree(self):
        """
        Formats the syntax tree for printing in an input file.

        By default this runs ``self._tree.format()``.

        :returns: a string of the text to write out to the input file (not wrapped yet for MCNP).
        :rtype: str
        """
        return self._tree.format()

    def format_for_mcnp_input(self, mcnp_version, has_following=False):
        """
        Creates a string representation of this MCNP_Object that can be
        written to file.

        :param mcnp_version: The tuple for the MCNP version that must be exported to.
        :type mcnp_version: tuple
        :return: a list of strings for the lines that this input will occupy.
        :rtype: list
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
        A= self.in_Cell_block
        B = print_in_data_block
        C = is_worth_pring

        Logic:
            1. A!BC + !ABC
            2. C *(A!B + !AB)
            3. C * (A xor B)
            4. C * (A != B)
        """
        # print in either block
        if (self.in_cell_block != print_in_data_block) and self._is_worth_printing:
            self._update_values()
            return self.wrap_string_for_mcnp(
                self._format_tree(),
                mcnp_version,
                True,
                suppress_blank_end=not self.in_cell_block,
            )
        return []

    @property
    def has_changed_print_style(self):  # pragma: no cover
        """
        returns true if the printing style for this modifier has changed
        from cell block to data block, or vice versa.

        .. deprecated:: 0.2.0
            This property is no longer needed and overly complex.

        :returns: true if the printing style for this modifier has changed
        :rtype: bool
        :raises DeprecationWarning: raised always.
        """
        warnings.warn(
            "has_changed_print_style will be removed soon.",
            DeprecationWarning,
            stacklevel=2,
        )
        if self._problem:
            print_in_cell_block = not self._problem.print_in_data_block[
                self.class_prefix
            ]
            set_in_cell_block = print_in_cell_block
            if not self.in_cell_block:
                for cell in self._problem.cells:
                    attr = montepy.Cell._CARDS_TO_PROPERTY[type(self)][0]
                    modifier = getattr(cell, attr)
                    if modifier.has_information:
                        set_in_cell_block = modifier.set_in_cell_block
                    break
            else:
                if self.has_information:
                    set_in_cell_block = self.set_in_cell_block
            return print_in_cell_block ^ set_in_cell_block
        else:
            return False

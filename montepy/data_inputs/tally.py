# Copyright 2024, Battelle Energy Alliance, LLC All Rights Reserved.
import copy

import montepy
from montepy.cells import Cells
from montepy.data_inputs.data_input import DataInputAbstract
from montepy.data_inputs.tally_type import TallyType
from montepy.input_parser.tally_parser import TallyParser
from montepy.input_parser import syntax_node
from montepy.numbered_mcnp_object import Numbered_MCNP_Object
from montepy.utilities import *

_TALLY_TYPE_MODULUS = 10


def _number_validator(self, number):
    if number <= 0:
        raise ValueError("number must be > 0")
    if number % _TALL_TYPE_MODULUS != self._type.value:
        raise ValueError(f"Tally Type cannot be changed.")
    if self._problem:
        self._problem.tallies.check_number(number)


class Tally(DataInputAbstract, Numbered_MCNP_Object):
    """ """

    # todo type enforcement
    _parser = TallyParser()

    __slots__ = {"_groups", "_type", "_number", "_old_number", "_include_total"}

    def __init__(self, input=None):
        self._cells = Cells()
        self._old_number = None
        self._number = self._generate_default_node(int, -1)
        super().__init__(input)
        if input:
            num = self._input_number
            self._old_number = copy.deepcopy(num)
            self._number = num
            try:
                tally_type = TallyType(self.number % _TALLY_TYPE_MODULUS)
            except ValueError as e:
                raise MalformedInputEror(input, f"Tally Type provided not allowed: {e}")
            groups, has_total = TallyGroup.parse_tally_specification(
                self._tree["tally"]
            )
            self._groups = groups
            self._include_total = has_total

    @staticmethod
    def _class_prefix():
        return "f"

    @staticmethod
    def _has_number():
        return True

    @staticmethod
    def _has_classifier():
        return 2

    @make_prop_val_node("_old_number")
    def old_number(self):
        """
        The material number that was used in the read file

        :rtype: int
        """
        pass

    @make_prop_val_node("_number", int, validator=_number_validator)
    def number(self):
        """
        The number to use to identify the material by

        :rtype: int
        """
        pass


class TallyGroup:
    __slots__ = {"_cells", "_old_numbers"}

    def __init__(self, cells=None, nodes=None):
        self._cells = montepy.cells.Cells()
        self._old_numbers = []

    @staticmethod
    def parse_tally_specification(tally_spec):
        # TODO type enforcement
        ret = []
        in_parens = False
        buff = None
        has_total = False
        for node in tally_spec:
            # TODO handle total
            if in_parens:
                if node.value == ")":
                    in_parens = False
                    buff._append_node(node)
                    ret.append(buff)
                    buff = None
                else:
                    buff._append_node(node)
            else:
                if node.value == "(":
                    in_parens = True
                    buff = TallyGroup()
                    buff._append_node(node)
                else:
                    ret.append(TallyGroup(nodes=[node]))
        return (ret, has_total)

    def _append_node(self, node):
        if not isinstance(node, syntax_node.ValueNode):
            raise ValueError(f"Can only append ValueNode. {node} given")
        self._old_numbers.append(node)

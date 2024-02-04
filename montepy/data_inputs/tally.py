# Copyright 2024, Battelle Energy Alliance, LLC All Rights Reserved.
import copy

import montepy
from montepy.cells import Cells
from montepy.data_inputs.data_input import DataInputAbstract
from montepy.data_inputs.tally_group import CellTallyGroup, SurfaceTallyGroup
from montepy.data_inputs.tally_type import TallyType
from montepy.errors import *
from montepy.input_parser.tally_parser import TallyParser
from montepy.input_parser import syntax_node
from montepy.numbered_mcnp_object import Numbered_MCNP_Object
from montepy.surface_collection import Surfaces
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
    _group_type = None

    __slots__ = {"_groups", "_type", "_number", "_old_number", "_include_total"}

    def __init__(self, input=None, other_tally=None):
        self._old_number = None
        self._number = self._generate_default_node(int, -1)
        super().__init__(input)
        if other_tally is not None:
            self._from_other_tally(other_tally)
            self._parse_tally_groups()
        if input:
            num = self._input_number
            self._old_number = copy.deepcopy(num)
            self._number = num
            try:
                tally_type = TallyType(self.number % _TALLY_TYPE_MODULUS)
                self._type = tally_type
            except ValueError as e:
                raise MalformedInputEror(input, f"Tally Type provided not allowed: {e}")

    def _parse_tally_groups(self):
        groups, has_total = self._group_type.parse_tally_specification(
            self._tree["tally"], self
        )
        self._groups = groups
        self._include_total = has_total

    def _from_other_tally(self, other, deepcopy=False):
        if other._type != self._allowed_type:
            # todo
            assert False
        for attr in {"_tree", "_old_number", "_number", "_groups", "_include_total"}:
            setattr(self, attr, getattr(other, attr, None))

    @classmethod
    def parse_tally_input(cls, input):
        base_tally = cls(input)
        new_class = TALLY_TYPE_CLASS_MAP[base_tally._type]
        ret = new_class(other_tally=base_tally)
        return ret

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

    def update_pointers(self, data_inputs):
        if self._problem is not None:
            for group in self.groups:
                group.update_pointers(self.problem, *self._obj_type)

    def _append_obj(self, obj):
        if not isinstance(obj, self._group_type._obj_type):
            raise TypeError(
                f"Can only append {self._group_type._obj_name} to Tally. {obj} given"
            )
        new_group = self._group_type([obj])
        self._groups.append(new_groups)

    def append_group(self, objs):
        if not isinstance(obj, (self._group_type, list)):
            raise TypeError(
                f"Can only append {self._group_type._obj_name} to Tally. {obj} given"
            )
        if isinstance(objs, list):
            objs = self._group_type(objs)
        self._groups.append(objs)

    @make_prop_pointer("_groups", list)
    def groups(self):
        """ """
        pass

    def clone(self, new_type=None, new_number=None):
        cls = type(self)
        parent = cls.__base__
        if not issubclass(new_type, parent):
            raise ValueError(
                f"Cannot convert a tally of type: {type(self)} to {new_type}"
            )
        # todo


class SurfaceTally(Tally):
    _group_type = SurfaceTallyGroup

    def append_surface(self, surf):
        self._append_obj(surf)

    def surfaces(self):
        for group in groups:
            for surface in surfaces:
                yield surface


class CellTally(Tally):
    _group_type = CellTallyGroup

    def append_cell(self, cell):
        self._append_obj(cell)

    def cells(self):
        for group in groups:
            for cell in cells:
                yield cell


class CellFluxTally(CellTally):
    _allowed_type = TallyType.CELL_FLUX


class EnergyDepTally(CellTally):
    _allowed_type = TallyType.ENERGY_DEPOSITION


class FissionDepTally(CellTally):
    _allowed_type = TallyType.FISSION_ENERGY_DEPOSITION


class CurrentTally(SurfaceTally):
    _allowed_type = TallyType.CURRENT


class SurfaceFluxTally(SurfaceTally):
    _allowed_type = TallyType.SURFACE_FLUX


TALLY_TYPE_CLASS_MAP = {
    TallyType.CURRENT: CurrentTally,
    TallyType.SURFACE_FLUX: SurfaceFluxTally,
    TallyType.CELL_FLUX: CellFluxTally,
    TallyType.ENERGY_DEPOSITION: EnergyDepTally,
    TallyType.FISSION_ENERGY_DEPOSITION: FissionDepTally,
    # TODO
    # TODO What is a detector
}

# Copyright 2024, Battelle Energy Alliance, LLC All Rights Reserved.

from montepy.cells import Cells
from montepy.errors import *
from montepy.input_parser import syntax_node
from montepy.surface_collection import Surfaces
from montepy.utilities import *


class TallyGroup:
    __slots__ = {"_objs", "_old_numbers", "_parent", "_tree"}

    _obj_type = None

    _obj_name = None

    def __init__(self, objs=None, nodes=None, parent=None):
        self._objs = None
        self._old_numbers = []
        self._obj_name = ""
        self._parent = parent
        self._tree = nodes

    @classmethod
    def parse_tally_specification(cls, tally_spec, parent):
        # TODO type enforcement
        ret = []
        in_parens = False
        buff = None
        has_total = False
        for node in tally_spec:
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
                    buff = cls(parent=parent)
                    buff._append_node(node)
                else:
                    if (
                        isinstance(node, syntax_node.ValueNode)
                        and node.type == str
                        and node.value.lower() == "t"
                    ):
                        has_total = True
                    else:
                        ret.append(cls(nodes=[node], parent=parent))
        return (ret, has_total)

    def _append_node(self, node):
        if not isinstance(node, (syntax_node.ValueNode, syntax_node.PaddingNode)):
            raise ValueError(f"Can only append ValueNode. {node} given")
        self._old_numbers.append(node)

    def append(self, cell):
        self._objs.append(cell)

    def update_pointers(self, problem):
        self._objs = ObjContainer()
        obj_source = getattr(problem, f"{self._obj_name}s")
        for number in self._older_numbers:
            try:
                self._objs.append(obj_source[number])
            except KeyError:
                raise BrokenObjectLinkError(
                    "Tally", self._parent.number, self._obj_name, number
                )


class CellTallyGroup(TallyGroup):
    _obj_type = Cells
    _obj_name = "Cell"

    @make_prop_pointer("_objs", (Cells, list), Cells)
    def cells(self):
        """ """
        pass


class SurfaceTallyGroup(TallyGroup):
    _obj_type = Surfaces
    _obj_name = "Surface"

    @make_prop_pointer("_objs", (Surfaces, list), Surfaces)
    def surfaces(self):
        """ """
        pass

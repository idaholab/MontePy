# Copyright 2024, Battelle Energy Alliance, LLC All Rights Reserved.
from unittest import TestCase
import pytest

import montepy
from montepy.geometry_operators import Operator
from montepy.input_parser import syntax_node
from montepy.surfaces.half_space import HalfSpace, UnitHalfSpace


def test_halfspace_init():
    surface = montepy.surfaces.CylinderOnAxis()
    node = montepy.input_parser.syntax_node.GeometryTree("hi", {}, "*", " ", " ")
    half_space = HalfSpace(+surface, Operator.UNION, -surface, node)
    assert half_space.operator is Operator.UNION
    assert half_space.left == +surface
    assert half_space.right == -surface
    assert half_space.node is node
    with pytest.raises(TypeError):
        HalfSpace(surface, Operator.UNION)
    with pytest.raises(TypeError):
        HalfSpace(+surface, "hi")
    with pytest.raises(TypeError):
        HalfSpace(+surface, Operator.UNION, surface)
    with pytest.raises(TypeError):
        HalfSpace(+surface, Operator.UNION, -surface, "hi")
    with pytest.raises(ValueError):
        HalfSpace(+surface, Operator.UNION)
    with pytest.raises(ValueError):
        HalfSpace(+surface, Operator.INTERSECTION)


def test_get_leaves():
    surface = montepy.surfaces.CylinderOnAxis()
    cell = montepy.Cell()
    half_space = -surface & ~cell
    cells, surfaces = half_space._get_leaf_objects()
    assert cells == {cell}
    assert surfaces == {surface}


def test_half_len():
    surface = montepy.surfaces.CylinderOnAxis()
    cell = montepy.Cell()
    half_space = -surface & ~cell
    assert len(half_space) == 2


def test_half_eq():
    cell1 = montepy.Cell()
    cell2 = montepy.Cell()
    half1 = ~cell1 & ~cell2
    assert half1 == half1
    half2 = ~cell1 | ~cell2
    assert half1 != half2
    half2 = ~cell1 & ~cell1
    assert half1 != half2
    half2 = ~cell2 & ~cell2
    assert half1 != half2
    half2 = ~half1
    half2._operator = Operator.INTERSECTION
    assert half1 != half2
    with pytest.raises(TypeError):
        half1 == "hi"


def test_half_str():
    cell1 = montepy.Cell()
    cell1.number = 1
    cell2 = montepy.Cell()
    cell2.number = 2
    half_space = ~cell1 | ~cell2
    assert str(half_space) == "(#1:#2)"
    half_space = ~cell1 & ~cell2
    assert str(half_space) == "(#1*#2)"
    half_space = ~(~cell1 & ~cell2)
    assert str(half_space) == "#(#1*#2)"
    # test that no errors occur
    repr(half_space)


def test_unit_half_init():
    node = montepy.input_parser.syntax_node.ValueNode("123", float)
    half_space = UnitHalfSpace(123, True, False, node)
    assert half_space.divider == 123
    assert half_space.side
    assert not half_space._is_cell
    assert half_space.node is node
    with pytest.raises(TypeError):
        UnitHalfSpace("hi", True, False)
    with pytest.raises(TypeError):
        half_space = UnitHalfSpace(123, "hi", False)
    with pytest.raises(TypeError):
        half_space = UnitHalfSpace(123, True, "hi")
    with pytest.raises(TypeError):
        half_space = UnitHalfSpace(123, True, False, "hi")


def test_unit_eq():
    half1 = UnitHalfSpace(1, True, False)
    assert half1 == half1
    half2 = UnitHalfSpace(2, True, False)
    assert half1 != half2
    half2 = UnitHalfSpace(1, False, False)
    assert half1 != half2
    half2 = UnitHalfSpace(1, True, True)
    assert half1 != half2
    with pytest.raises(TypeError):
        half1 == "hi"


def test_unit_str():
    half_space = UnitHalfSpace(1, True, False)
    assert str(half_space) == "+1"
    half_space.side = False
    assert str(half_space) == "-1"
    half_space.is_cell = True
    assert str(half_space), "1"
    cell = montepy.Cell()
    cell.number = 1
    half_space.divider = cell
    assert str(half_space) == "1"


# test geometry integration
def test_surface_half_space():
    surface = montepy.surfaces.cylinder_on_axis.CylinderOnAxis()
    half_space = +surface
    assert isinstance(half_space, HalfSpace)
    assert isinstance(half_space, UnitHalfSpace)
    assert half_space.divider is surface
    assert half_space.side
    half_space = -surface
    assert isinstance(half_space, HalfSpace)
    assert isinstance(half_space, UnitHalfSpace)
    assert half_space.divider is surface
    assert not half_space.side
    with pytest.raises(TypeError):
        half_space = surface & surface
    with pytest.raises(TypeError):
        half_space = surface | surface
    with pytest.raises(TypeError):
        half_space = ~surface


def test_cell_half_space():
    cell = montepy.Cell()
    half_space = ~cell
    assert isinstance(half_space, HalfSpace)
    assert half_space.left.divider is cell
    assert half_space.left.side
    with pytest.raises(TypeError):
        half_space = cell & cell
    with pytest.raises(TypeError):
        half_space = cell | cell
    with pytest.raises(TypeError):
        half_space = +cell
    with pytest.raises(TypeError):
        half_space = -cell


def test_parens_node_export():
    surf1 = montepy.surfaces.cylinder_on_axis.CylinderOnAxis()
    surf2 = montepy.surfaces.cylinder_on_axis.CylinderOnAxis()
    surf3 = montepy.surfaces.cylinder_on_axis.CylinderOnAxis()
    surf1.number = 1
    surf2.number = 2
    surf3.number = 3
    for half_space, form_answer, str_answer in [
        (-surf1 & (+surf2 | -surf3), "-1 (2 : -3)", "(-1*(+2:-3))"),
        ((-surf1 | +surf2) & -surf3, "(-1 : 2) -3", "((-1:+2)*-3)"),
    ]:
        half_space._update_values()
        assert half_space.node.format() == form_answer
        assert str(half_space) == str_answer


def test_intersect_half_space():
    cell1 = ~montepy.Cell()
    cell2 = ~montepy.Cell()
    half_space = cell1 & cell2
    assert isinstance(half_space, HalfSpace)
    assert half_space.operator is Operator.INTERSECTION
    assert half_space.left is cell1
    assert half_space.right is cell2
    with pytest.raises(TypeError):
        cell1 & "hi"
    with pytest.raises(TypeError):
        "hi" & cell1
    with pytest.raises(TypeError):
        cell2 + cell1
    with pytest.raises(TypeError):
        cell2 - cell1


def test_union_half_space():
    cell1 = ~montepy.Cell()
    cell2 = ~montepy.Cell()
    half_space = cell1 | cell2
    assert isinstance(half_space, HalfSpace)
    assert half_space.operator is Operator.UNION
    assert half_space.left is cell1
    assert half_space.right is cell2
    with pytest.raises(TypeError):
        cell1 | "hi"
    with pytest.raises(TypeError):
        "hi" | cell1


def test_invert_half_space():
    cell1 = ~montepy.Cell()
    cell2 = ~montepy.Cell()
    half_space1 = cell1 | cell2
    half_space = ~half_space1
    assert isinstance(half_space, HalfSpace)
    assert half_space.operator is Operator.COMPLEMENT
    assert half_space.left is half_space1
    assert half_space.right is None


def test_iand_recursion():
    cell1 = montepy.Cell()
    cell2 = montepy.Cell()
    cell3 = montepy.Cell()
    half_space = ~cell1 & ~cell2
    cell1.number = 1
    cell2.number = 2
    cell3.number = 3
    cell3.geometry = half_space
    half_space &= ~cell1
    assert half_space.left == ~cell1
    assert not isinstance(half_space.right, UnitHalfSpace)
    assert half_space.right.left == ~cell2
    assert half_space.right.right == ~cell1
    assert half_space.operator == Operator.INTERSECTION
    assert len(half_space) == 3
    for i in range(1, 100):
        half_space &= ~cell1
        assert len(half_space) == i + 3
    with pytest.raises(TypeError):
        half_space &= "hi"
    # test with unit halfspaces
    surf = montepy.surfaces.CylinderParAxis()
    # test going from leaf to tree
    half_space = -surf
    half_space &= +surf
    assert len(half_space) == 2
    # test with actual tree
    half_space = -surf | +surf
    half_space &= +surf
    assert len(half_space) == 3


def test_ior_recursion():
    cell1 = ~montepy.Cell()
    cell2 = ~montepy.Cell()
    half_space = cell1 | cell2
    half_space |= cell1
    assert half_space.left is cell1
    assert not isinstance(half_space.right, UnitHalfSpace)
    assert half_space.right.left == cell2
    assert half_space.right.right == cell1
    assert half_space.operator == Operator.UNION
    assert len(half_space) == 3
    for i in range(1, 100):
        half_space |= cell1
        assert len(half_space), i + 3
    with pytest.raises(TypeError):
        half_space |= "hi"
    # test with unit halfspaces
    surf = montepy.surfaces.CylinderParAxis()
    half_space = -surf
    half_space |= +surf
    assert len(half_space) == 2
    half_space = -surf | +surf
    half_space |= +surf
    assert len(half_space) == 3


def test_parse_input_tree():
    # simplest intersection
    input = montepy.input_parser.mcnp_input.Input(
        ["1 0 1 -2"], montepy.input_parser.block_type.BlockType.CELL
    )
    parser = montepy.input_parser.cell_parser.CellParser()
    tree = parser.parse(input.tokenize())
    geometry = tree["geometry"]
    half_space = HalfSpace.parse_input_node(geometry)
    assert half_space.operator == Operator.INTERSECTION
    assert half_space.left.divider == 1
    assert half_space.left.side
    assert not half_space.left.is_cell
    assert half_space.right.divider == 2
    assert not half_space.right.side
    assert not half_space.right.is_cell
    # Test type checking
    with pytest.raises(TypeError):
        HalfSpace.parse_input_node("hi")
    # test assymetric
    input = montepy.input_parser.mcnp_input.Input(
        ["1 0 #2"], montepy.input_parser.block_type.BlockType.CELL
    )
    parser = montepy.input_parser.cell_parser.CellParser()
    tree = parser.parse(input.tokenize())
    geometry = tree["geometry"]
    half_space = HalfSpace.parse_input_node(geometry)
    assert half_space.operator == Operator.COMPLEMENT
    assert half_space.left.divider == 2
    assert half_space.left.side
    assert half_space.left.is_cell
    assert half_space.right is None
    # Test nested trees
    input = montepy.input_parser.mcnp_input.Input(
        ["1 0 1 -2 : 3"], montepy.input_parser.block_type.BlockType.CELL
    )
    parser = montepy.input_parser.cell_parser.CellParser()
    tree = parser.parse(input.tokenize())
    geometry = tree["geometry"]
    half_space = HalfSpace.parse_input_node(geometry)
    assert half_space.operator == Operator.UNION
    assert not isinstance(half_space.left, UnitHalfSpace)
    assert isinstance(half_space.right, UnitHalfSpace)
    assert half_space.left.operator == Operator.INTERSECTION
    assert half_space.right.divider == 3
    assert half_space.left.left.divider == 1
    assert half_space.left.right.divider == 2
    # test shift
    input = montepy.input_parser.mcnp_input.Input(
        ["1 0 #(1 2 3)"], montepy.input_parser.block_type.BlockType.CELL
    )
    parser = montepy.input_parser.cell_parser.CellParser()
    tree = parser.parse(input.tokenize())
    geometry = tree["geometry"]
    half_space = HalfSpace.parse_input_node(geometry)
    assert half_space.operator == Operator.COMPLEMENT
    assert half_space.right is None
    assert half_space.left.operator == Operator.GROUP
    nested = half_space.left.left
    assert nested.operator == Operator.INTERSECTION
    assert nested.right is not None
    assert nested.left.operator == Operator.INTERSECTION
    # test nested parens
    input = montepy.input_parser.mcnp_input.Input(
        ["1 0 (1 : 2:3) 4"], montepy.input_parser.block_type.BlockType.CELL
    )
    parser = montepy.input_parser.cell_parser.CellParser()
    tree = parser.parse(input.tokenize())
    geometry = tree["geometry"]
    half_space = HalfSpace.parse_input_node(geometry)
    assert len(half_space) == 4
    assert half_space.operator == Operator.INTERSECTION
    assert half_space.left.operator == Operator.GROUP
    assert half_space.left.left.operator == Operator.UNION


def test_update_new_parens():
    input = montepy.input_parser.mcnp_input.Input(
        ["1 0 1 2"], montepy.input_parser.block_type.BlockType.CELL
    )
    parser = montepy.input_parser.cell_parser.CellParser()
    tree = parser.parse(input.tokenize())
    geometry = tree["geometry"]
    half_space = HalfSpace.parse_input_node(geometry)
    surf3 = montepy.surfaces.cylinder_on_axis.CylinderOnAxis()
    surf3.number = 3
    half2 = half_space.right
    half_space.right = half2 | +surf3
    half_space._update_values()
    assert half_space.node.format() == "1 (2 : 3)"


def test_update_tree_with_comment():
    input = montepy.input_parser.mcnp_input.Input(
        ["1 0 -1 $hi there", "      2"],
        montepy.input_parser.block_type.BlockType.CELL,
    )
    cell = montepy.Cell(input)
    geometry = cell.geometry
    geometry._update_values()


def test_parse_input_value_node():
    node = montepy.input_parser.syntax_node.ValueNode("-1", float)
    half_space = UnitHalfSpace.parse_input_node(node)
    assert not half_space.is_cell
    assert not half_space.side
    assert half_space.divider == 1
    half_space = UnitHalfSpace.parse_input_node(node, True)
    assert half_space.is_cell
    assert half_space.side
    assert half_space.divider == 1
    node = montepy.input_parser.syntax_node.ValueNode("+1", float)
    half_space = UnitHalfSpace.parse_input_node(node, False)
    assert not half_space.is_cell
    assert half_space.side
    assert half_space.divider == 1
    with pytest.raises(TypeError):
        UnitHalfSpace.parse_input_node("hi", False)
    with pytest.raises(TypeError):
        UnitHalfSpace.parse_input_node(node, "hi")


def test_unit_divider_setter():
    cell = montepy.Cell()
    cell.number = 1
    parent = montepy.Cell()
    parent.number = 2
    node = montepy.input_parser.syntax_node.ValueNode("1", float)
    half_space = UnitHalfSpace.parse_input_node(node, True)
    cells = montepy.cells.Cells()
    cells.append(cell)
    half_space.update_pointers(cells, [], parent)
    assert half_space.divider is cell
    cell2 = montepy.Cell()
    # #madLads
    cell2.number = 4
    half_space.divider = cell2
    assert half_space.divider is cell2
    assert cell2 in parent.complements
    # test with surface
    surf = montepy.surfaces.CylinderParAxis()
    surf.number = 5
    with pytest.raises(TypeError):
        half_space.divider = surf
    half_space.is_cell = False
    half_space.divider = surf
    assert half_space.divider is surf
    assert surf in parent.surfaces
    with pytest.raises(TypeError):
        half_space.divider = "hi"


def test_unit_create_default_node():
    surf = montepy.surfaces.CylinderParAxis()
    surf.number = 1
    half_space = UnitHalfSpace(surf, True, False)
    half_space._ensure_has_nodes()
    node = half_space.node
    assert isinstance(node, syntax_node.ValueNode)
    assert node.value == 1
    assert node.format() == "1"
    # test with negative side
    half_space = UnitHalfSpace(surf, False, False)
    half_space._ensure_has_nodes()
    node = half_space.node
    assert node.format() == "-1"
    # test with int and not an object
    half_space = UnitHalfSpace(1, True, False)
    half_space._ensure_has_nodes()
    node = half_space.node
    assert isinstance(node, syntax_node.ValueNode)
    assert node.value == 1


def test_tree_create_default_node():
    surf = montepy.surfaces.CylinderParAxis()
    surf.number = 1
    half_space = -surf | +surf
    half_space._ensure_has_nodes()
    node = half_space.node
    assert isinstance(node, syntax_node.GeometryTree)
    assert node.operator == Operator.UNION
    assert node.format() == "-1 : 1"
    # Test intersection
    half_space = -surf & +surf
    half_space._ensure_has_nodes()
    node = half_space.node
    assert node.operator == Operator.INTERSECTION
    # Test complement
    half_space = ~(-surf | +surf)
    half_space._ensure_has_nodes()
    node = half_space.node
    assert node.operator == Operator.COMPLEMENT
    assert node.format() == " #(-1 : 1)"
    # test cell complement
    cell = montepy.Cell()
    cell.number = 1
    half_space = ~cell
    half_space._ensure_has_nodes()
    node = half_space.node
    assert node.operator == Operator.COMPLEMENT
    assert node.format() == " #1"


def test_update_operators_in_node():
    surf = montepy.surfaces.CylinderParAxis()
    surf.number = 1
    half_space = -surf | +surf
    half_space._ensure_has_nodes()
    half_space.operator = Operator.INTERSECTION
    half_space._update_values()
    assert half_space.node.format() == "-1   1"
    del half_space.right
    half_space.operator = Operator.COMPLEMENT
    cell = montepy.Cell()
    cell.number = 1
    half_space.left = UnitHalfSpace(cell, True, True)
    half_space._update_values()
    assert half_space.node.format() == "  #1"
    # test with blank tree
    half_space = -surf & +surf
    half_space._update_values()
    assert half_space.node.format() == "-1 1"
    # test move to union
    # test centering
    half_space.node.nodes["operator"].append("  ")
    half_space.operator = Operator.UNION
    half_space._update_values()
    assert half_space.node.format() == "-1 : 1"

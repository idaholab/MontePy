# Copyright 2024, Battelle Energy Alliance, LLC All Rights Reserved.
import pytest
import montepy
from montepy.geometry_operators import Operator
from montepy.input_parser import syntax_node
from montepy.surfaces.half_space import HalfSpace, UnitHalfSpace
from tests.test_cell_problem import verify_export as verify_cell_export


def test_halfspace_init():
    surface = montepy.CylinderOnAxis()
    surface.number = 1
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
    surface = montepy.CylinderOnAxis()
    surface.number = 1
    cell = montepy.Cell()
    cell.number = 1
    half_space = -surface & ~cell
    cells, surfaces = half_space._get_leaf_objects()
    assert cells == montepy.cells.Cells([cell])
    assert surfaces == montepy.surface_collection.Surfaces([surface])


def test_half_len():
    surface = montepy.CylinderOnAxis()
    cell = montepy.Cell()
    surface.number = 1
    cell.number = 1
    half_space = -surface & ~cell
    assert len(half_space) == 2


def test_half_eq():
    cell1 = montepy.Cell()
    cell2 = montepy.Cell()
    cell1.number = 1
    cell2.number = 2
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
    surface = montepy.CylinderOnAxis()
    surface.number = 1
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
    cell.number = 1
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
    surf1 = montepy.CylinderOnAxis()
    surf2 = montepy.CylinderOnAxis()
    surf3 = montepy.CylinderOnAxis()
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
    cell1 = montepy.Cell()
    cell2 = montepy.Cell()
    cell1.number = 1
    cell2.number = 2
    cell1 = ~cell1
    cell2 = ~cell2
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
    cell1 = montepy.Cell()
    cell2 = montepy.Cell()
    cell1.number = 1
    cell2.number = 2
    cell1 = ~cell1
    cell2 = ~cell2
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
    cell1 = montepy.Cell()
    cell2 = montepy.Cell()
    cell1.number = 1
    cell2.number = 2
    cell1 = ~cell1
    cell2 = ~cell2
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
    cell1.number = 1
    cell2.number = 2
    cell3.number = 3
    half_space = ~cell1 & ~cell2
    cell3.geometry = half_space
    half_space &= ~cell1
    # lazy tree enforcement
    assert str(half_space) == "((#1*#2)*#1)"
    assert half_space.right == ~cell1
    assert not isinstance(half_space.right, UnitHalfSpace)
    assert half_space.left.left == ~cell1
    assert half_space.left.right == ~cell2
    assert half_space.operator == Operator.INTERSECTION
    assert len(half_space) == 3
    for i in range(1, 100):
        half_space &= ~cell1
        assert len(half_space) == i + 3
    with pytest.raises(TypeError):
        half_space &= "hi"
    # test with unit halfspaces
    surf = montepy.CylinderParAxis()
    surf.number = 5
    # test going from leaf to tree
    half_space = -surf
    half_space &= +surf
    assert len(half_space) == 2
    assert str(half_space) == "(-5*+5)"
    # test with actual tree
    half_space = -surf | +surf
    half_space &= +surf
    assert len(half_space) == 3
    assert half_space.operator == Operator.INTERSECTION
    assert str(half_space) == "((-5:+5)*+5)"


def test_ior_recursion():
    cell1 = montepy.Cell()
    cell2 = montepy.Cell()
    cell1.number = 1
    cell2.number = 2
    cell1 = ~cell1
    cell2 = ~cell2
    half_space = cell1 | cell2
    half_space |= cell1
    assert str(half_space) == "((#1:#2):#1)"
    assert half_space.right is cell1
    assert not isinstance(half_space.left, UnitHalfSpace)
    assert half_space.left.right == cell2
    assert half_space.left.left == cell1
    assert half_space.operator == Operator.UNION
    assert len(half_space) == 3
    for i in range(1, 100):
        half_space |= cell1
        assert len(half_space), i + 3
    with pytest.raises(TypeError):
        half_space |= "hi"
    # test with unit halfspaces
    surf = montepy.CylinderParAxis()
    surf.number = 5
    half_space = -surf
    half_space |= +surf
    assert len(half_space) == 2
    assert str(half_space) == "(-5:+5)"
    half_space = -surf | +surf
    half_space |= +surf
    assert len(half_space) == 3
    assert str(half_space) == "((-5:+5):+5)"
    # test with complex tree
    half_space = -surf & +surf
    half_space |= +surf
    assert len(half_space) == 3
    assert half_space.operator == Operator.UNION
    assert str(half_space) == "((-5*+5):+5)"


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
    surf3 = montepy.CylinderOnAxis()
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
    surf = montepy.CylinderParAxis()
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
    surf = montepy.CylinderParAxis()
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
    surf = montepy.CylinderParAxis()
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
    surf = montepy.CylinderParAxis()
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


# ── replace() tests ───────────────────────────────────────────────────────────


@pytest.fixture
def make_linked_geometry():
    """Fixture factory: build a parent cell whose geometry is already linked.

    Returns a callable that accepts surfaces/cells and produces
    (parent_cell, half_space) where every UnitHalfSpace leaf has
    _cell set so the old-divider cleanup path in replace() is exercised.
    """

    def _factory(*surfs):
        parent = montepy.Cell()
        parent.number = 99
        # Populate parent.surfaces up front so all surfaces are present before replace()
        for surf in surfs:
            parent.surfaces.append(surf)
        half_space = None
        for surf in surfs:
            leaf = +surf
            # Wire _cell directly since dividers are already resolved objects, not ints
            leaf._cell = parent
            half_space = leaf if half_space is None else half_space & leaf
        return parent, half_space

    return _factory


def test_replace_surface_basic():
    """replace() swaps old surface for new one throughout the tree."""
    surf1 = montepy.CylinderOnAxis(number=1)
    surf2 = montepy.CylinderOnAxis(number=2)
    surf3 = montepy.CylinderOnAxis(number=3)
    half_space = +surf1 & -surf2
    half_space.replace(surf1, surf3)
    # surf3 should now appear in place of surf1
    leaves = list(half_space)
    dividers = [leaf.divider for leaf in leaves]
    assert surf3 in dividers
    assert surf1 not in dividers
    assert surf2 in dividers


def test_replace_surface_updates_cell_surfaces(make_linked_geometry):
    """After replace(), old surface is removed from cell.surfaces and new one is present."""
    surf1 = montepy.CylinderOnAxis()
    surf2 = montepy.CylinderOnAxis()
    surf3 = montepy.CylinderOnAxis()
    surf1.number = 1
    surf2.number = 2
    surf3.number = 3
    parent, half_space = make_linked_geometry(surf1, surf2)
    half_space.replace(surf1, surf3)
    assert surf3 in parent.surfaces
    assert surf1 not in parent.surfaces
    assert surf2 in parent.surfaces  # untouched


def test_replace_on_leaf():
    """replace() called directly on a UnitHalfSpace (leaf) works correctly."""
    surf1 = montepy.CylinderOnAxis()
    surf2 = montepy.CylinderOnAxis()
    surf1.number = 1
    surf2.number = 2
    leaf = +surf1
    leaf.replace(surf1, surf2)
    assert leaf.divider is surf2


def test_replace_not_found_raises():
    """replace() raises ValueError when old_divider is absent from the tree."""
    surf1 = montepy.CylinderOnAxis()
    surf2 = montepy.CylinderOnAxis()
    surf3 = montepy.CylinderOnAxis()
    surf1.number = 1
    surf2.number = 2
    surf3.number = 3
    half_space = +surf1 & -surf2
    with pytest.raises(ValueError):
        half_space.replace(surf3, surf1)


def test_replace_wrong_kind_raises():
    """replace() raises TypeError when mixing Surface and Cell arguments."""
    surf = montepy.CylinderOnAxis()
    surf.number = 1
    cell = montepy.Cell()
    cell.number = 2
    half_space = +surf
    with pytest.raises(TypeError):
        half_space.replace(surf, cell)


def test_replace_invalid_type_raises():
    """replace() raises TypeError when either argument is not a Surface or Cell."""
    surf = montepy.CylinderOnAxis()
    surf.number = 1
    half_space = +surf
    with pytest.raises(TypeError):
        half_space.replace("not a surface", surf)
    with pytest.raises(TypeError):
        half_space.replace(surf, 42)


def test_replace_subclass_surface():
    """replace() accepts any Surface subclass for either argument (no false type errors)."""
    surf1 = montepy.CylinderOnAxis()  # subclass of Surface
    surf2 = montepy.AxisPlane()  # different subclass of Surface
    surf1.number = 1
    surf2.number = 2
    half_space = +surf1 & -surf1
    # Should not raise — both are Surfaces regardless of subclass
    half_space.replace(surf1, surf2)
    for leaf in half_space:
        assert leaf.divider is surf2


def test_replace_cell_complement(make_linked_geometry):
    """replace() works on Cell complement dividers and updates cell.complements."""
    cell1 = montepy.Cell()
    cell2 = montepy.Cell()
    cell3 = montepy.Cell()
    cell1.number = 1
    cell2.number = 2
    cell3.number = 3

    parent = montepy.Cell()
    parent.number = 99
    parent.complements.append(cell1)
    parent.complements.append(cell2)

    # ~cell produces HalfSpace(UnitHalfSpace(cell, True, True), COMPLEMENT, None)
    hs1 = ~cell1
    hs2 = ~cell2
    for leaf in hs1:
        leaf._cell = parent
    for leaf in hs2:
        leaf._cell = parent
    half_space = hs1 & hs2

    half_space.replace(cell1, cell3)

    dividers = [leaf.divider for leaf in half_space]
    assert cell3 in dividers
    assert cell1 not in dividers
    assert cell2 in dividers  # untouched
    assert cell3 in parent.complements
    assert cell1 not in parent.complements


def test_replace_same_object_raises():
    """replace() raises ValueError when old_divider and new_divider are the same object."""
    surf = montepy.CylinderOnAxis()
    surf.number = 1
    half_space = +surf
    with pytest.raises(ValueError):
        half_space.replace(surf, surf)


def test_replace_same_number_different_object(make_linked_geometry):
    """replace() with a new surface sharing the same number as old must not corrupt cell.surfaces."""
    surf1 = montepy.CylinderOnAxis()
    surf2 = montepy.CylinderOnAxis()
    surf3 = montepy.CylinderOnAxis()
    surf1.number = 1
    surf2.number = 2
    # surf3 intentionally gets the same number as surf1
    surf3.number = 1
    parent, half_space = make_linked_geometry(surf1, surf2)
    # Should not raise NumberConflictError or leave the collection in a broken state
    half_space.replace(surf1, surf3)
    # Numbered_object_collection.__contains__ is number-based, so use identity checks
    # to distinguish surf1 and surf3 which share the same number.
    surfaces = list(parent.surfaces)
    assert any(s is surf3 for s in surfaces)
    assert not any(s is surf1 for s in surfaces)
    assert any(s is surf2 for s in surfaces)  # untouched


def test_replace_same_number_different_object_verify_export():
    """Replacing with a same-number surface still exports and re-parses cleanly."""
    surf1 = montepy.CylinderOnAxis(number=1)
    surf2 = montepy.CylinderOnAxis(number=2)
    surf3 = montepy.CylinderOnAxis(number=1)
    parent = montepy.Cell(number=99)
    parent.geometry = +surf1 & -surf2
    parent.importance.neutron = 1.0
    for leaf in parent.geometry:
        leaf._cell = parent

    parent.geometry.replace(surf1, surf3)

    surfaces = list(parent.surfaces)
    assert any(s is surf3 for s in surfaces)
    assert not any(s is surf1 for s in surfaces)
    verify_cell_export(parent)


def test_replace_unlinked_raises():
    """replace() raises IllegalState when the geometry tree has not been linked."""
    from montepy.exceptions import IllegalState

    surf1 = montepy.CylinderOnAxis()
    surf2 = montepy.CylinderOnAxis()
    surf1.number = 1
    surf2.number = 2
    # Build a tree with integer dividers (as if freshly parsed, not update_pointers'd)
    leaf = UnitHalfSpace(1, True, False)  # integer divider
    with pytest.raises(IllegalState):
        leaf.replace(surf1, surf2)


def test_ensure_has_parens_right_union():
    """_ensure_has_parens wraps the RIGHT side in GROUP when it's a union under intersection."""
    surf1 = montepy.CylinderOnAxis()
    surf2 = montepy.CylinderOnAxis()
    surf3 = montepy.CylinderOnAxis()
    surf1.number = 1
    surf2.number = 2
    surf3.number = 3
    # left is a leaf, right is a union → right must be wrapped in GROUP
    half_space = +surf1 & (+surf2 | -surf3)
    half_space._ensure_has_nodes()
    assert half_space.right.operator == Operator.GROUP
    assert half_space.node.format() == "1 (2 : -3)"


def test_replace_not_found_restores_nothing(make_linked_geometry):
    """replace() raises ValueError and does NOT restore old_divider when it was
    present in cell.surfaces but absent from the geometry tree."""
    surf1 = montepy.CylinderOnAxis()
    surf2 = montepy.CylinderOnAxis()
    surf3 = montepy.CylinderOnAxis()
    surf1.number = 1
    surf2.number = 2
    surf3.number = 3
    # geometry only contains surf1; surf2 is in cell.surfaces but not the tree
    parent, half_space = make_linked_geometry(surf1)
    # manually add surf2 to cell.surfaces so removed_from_container=True path is hit
    parent.surfaces.append(surf2)
    with pytest.raises(ValueError):
        half_space.replace(surf2, surf3)
    # surf2 must NOT be restored — Micah's directive
    assert surf2 not in parent.surfaces


# ── __iter__ tests ────────────────────────────────────────────────────────────


def test_halfspace_iter_leaves_in_order():
    """HalfSpace.__iter__ yields all UnitHalfSpace leaves depth-first left-to-right."""
    surf1 = montepy.CylinderOnAxis()
    surf2 = montepy.CylinderOnAxis()
    surf3 = montepy.CylinderOnAxis()
    surf1.number = 1
    surf2.number = 2
    surf3.number = 3
    half_space = (+surf1 & -surf2) | +surf3
    leaves = list(half_space)
    assert len(leaves) == 3
    assert all(isinstance(leaf, UnitHalfSpace) for leaf in leaves)
    assert leaves[0].divider is surf1
    assert leaves[1].divider is surf2
    assert leaves[2].divider is surf3


def test_halfspace_iter_count_matches_len():
    """len(half_space) equals the number of leaves yielded by iteration."""
    surf1 = montepy.CylinderOnAxis()
    surf2 = montepy.CylinderOnAxis()
    surf3 = montepy.CylinderOnAxis()
    surf1.number = 1
    surf2.number = 2
    surf3.number = 3
    half_space = +surf1 & -surf2 & +surf3
    assert len(half_space) == 3


def test_unit_halfspace_iter():
    """UnitHalfSpace.__iter__ yields exactly itself."""
    surf = montepy.CylinderOnAxis()
    surf.number = 1
    leaf = +surf
    leaves = list(leaf)
    assert len(leaves) == 1
    assert leaves[0] is leaf


def _all_geometry_nodes(geometry):
    if isinstance(geometry, UnitHalfSpace):
        return [geometry]
    nodes = [geometry] + _all_geometry_nodes(geometry.left)
    if geometry.right is not None:
        nodes += _all_geometry_nodes(geometry.right)
    return nodes


def _plane(number):
    return montepy.AxisPlane(f"{number} PZ {float(number)}")


def _surface_numbers(collection):
    return sorted(surface.number for surface in collection)


def test_geometry_linked_to_parsed_cell():
    cell = montepy.Cell("1 0 -1 (2 : 3) #4 imp:n=1")
    assert all(node._cell is cell for node in _all_geometry_nodes(cell.geometry))


def test_geometry_setter_links_whole_tree():
    cell = montepy.Cell(number=1)
    cell.geometry = -_plane(1) & (+_plane(2) | -_plane(3))
    assert all(node._cell is cell for node in _all_geometry_nodes(cell.geometry))


def test_geometry_replace_after_setter_updates_cell():
    cell = montepy.Cell(number=1)
    old, keep, new = _plane(1), _plane(2), _plane(3)
    cell.geometry = -old & +keep
    cell.geometry.replace(old, new)
    assert _surface_numbers(cell.surfaces) == [2, 3]


def test_geometry_replace_after_setter_reaches_problem():
    cell = montepy.Cell(number=1)
    old, keep, new = _plane(1), _plane(2), _plane(3)
    cell.geometry = -old & +keep
    cell.geometry.replace(old, new)
    problem = montepy.MCNP_Problem("foo")
    problem.cells.append(cell)
    assert _surface_numbers(problem.surfaces) == [2, 3]


def test_geometry_clone_links_to_new_cell():
    problem = montepy.read_input("tests/inputs/test.imcnp")
    new_cell = problem.cells[1].clone()
    assert all(
        node._cell is new_cell for node in _all_geometry_nodes(new_cell.geometry)
    )
    old = list(new_cell.surfaces)[0]
    new = _plane(9999)
    new_cell.geometry.replace(old, new)
    assert new in new_cell.surfaces


def test_geometry_reassign_drops_old_dividers():
    other = montepy.Cell(number=2)
    other.geometry = -_plane(9)
    cell = montepy.Cell(number=1)
    old, keep, new = _plane(1), _plane(2), _plane(3)
    cell.geometry = (-old & +keep) & ~other
    assert list(cell.complements) == [other]
    old_geometry = cell.geometry
    cell.geometry = +keep & -new
    assert _surface_numbers(cell.surfaces) == [2, 3]
    assert len(cell.complements) == 0
    assert all(node._cell is None for node in _all_geometry_nodes(old_geometry))


def test_geometry_reassign_same_number():
    cell = montepy.Cell(number=1)
    cell.geometry = -_plane(1)
    new = _plane(1)
    cell.geometry = -new
    assert list(cell.surfaces)[0] is new


def test_geometry_reassign_keeps_shared_tree():
    cell = montepy.Cell(number=1)
    cell.geometry = -_plane(1)
    new = _plane(2)
    cell.geometry &= +new
    assert _surface_numbers(cell.surfaces) == [1, 2]
    assert all(node._cell is cell for node in _all_geometry_nodes(cell.geometry))


def test_geometry_failed_reassign_changes_nothing():
    cell = montepy.Cell(number=1)
    surface = _plane(1)
    cell.geometry = -surface
    old_geometry = cell.geometry
    with pytest.raises(montepy.exceptions.IllegalState):
        cell.geometry = montepy.Cell("2 0 -5 imp:n=1").geometry
    assert cell.geometry is old_geometry
    assert old_geometry._cell is cell
    assert list(cell.surfaces) == [surface]


def _problem_with_cell():
    problem = montepy.MCNP_Problem("foo")
    old, keep = _plane(1), _plane(2)
    cell = montepy.Cell(number=1)
    cell.geometry = -old & +keep
    problem.cells.append(cell)
    return problem, cell, old, keep


def test_geometry_replace_in_problem_adds_surface():
    problem, cell, old, keep = _problem_with_cell()
    new = _plane(3)
    cell.geometry.replace(old, new)
    assert new in problem.surfaces
    assert _surface_numbers(cell.surfaces) == [2, 3]


def test_geometry_replace_in_problem_can_be_read_back(tmp_path):
    problem = montepy.read_input("tests/inputs/test.imcnp")
    cell = montepy.Cell("9000 0 -1 imp:n=1")
    old, keep, new = _plane(9001), _plane(9002), _plane(9003)
    cell.geometry = -old & +keep
    problem.cells.append(cell)
    cell.geometry.replace(old, new)
    destination = tmp_path / "out.imcnp"
    problem.write_problem(destination)
    new_problem = montepy.read_input(destination)
    assert 9003 in new_problem.surfaces.numbers
    assert _surface_numbers(new_problem.cells[9000].surfaces) == [9002, 9003]


def test_geometry_reassign_in_problem_adds_surface():
    problem, cell, old, keep = _problem_with_cell()
    new = _plane(3)
    cell.geometry = +keep & -new
    assert new in problem.surfaces
    assert old in problem.surfaces
    assert _surface_numbers(cell.surfaces) == [2, 3]


def test_geometry_iand_in_problem_adds_surface():
    problem, cell, old, keep = _problem_with_cell()
    new = _plane(3)
    cell.geometry &= -new
    assert new in problem.surfaces


def test_geometry_set_sides():
    cell = montepy.Cell(number=1)
    left, right, new_left, new_right = _plane(1), _plane(2), _plane(3), _plane(4)
    cell.geometry = -left & +right
    old_left = cell.geometry.left
    cell.geometry.left = -new_left
    assert _surface_numbers(cell.surfaces) == [2, 3]
    assert old_left._cell is None
    old_right = cell.geometry.right
    cell.geometry.right = +new_right | -left
    assert _surface_numbers(cell.surfaces) == [1, 3, 4]
    assert old_right._cell is None
    assert all(node._cell is cell for node in _all_geometry_nodes(cell.geometry))


def test_geometry_set_side_in_problem_adds_surface():
    problem, cell, old, keep = _problem_with_cell()
    new = _plane(3)
    cell.geometry.left = -new
    assert new in problem.surfaces


def test_geometry_delete_right_updates_cell():
    cell = montepy.Cell(number=1)
    left, right = _plane(1), _plane(2)
    cell.geometry = ~(-left & +right)
    inner = cell.geometry.left
    inner.operator = Operator.COMPLEMENT
    del inner.right
    assert inner.right is None
    assert _surface_numbers(cell.surfaces) == [1]


def test_geometry_set_side_parsed_cell_is_not_resolved():
    cell = montepy.Cell("1 0 -1 2 imp:n=1")
    new = _plane(3)
    cell.geometry.left = -new
    assert cell.geometry.left._cell is cell
    assert len(cell.surfaces) == 0


@pytest.mark.parametrize("value", ["hi", None])
def test_geometry_set_left_bad_type(value):
    half_space = -_plane(1) & +_plane(2)
    with pytest.raises(TypeError):
        half_space.left = value


def test_geometry_set_right_bad_type():
    half_space = -_plane(1) & +_plane(2)
    with pytest.raises(TypeError):
        half_space.right = "hi"

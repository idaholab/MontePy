from hypothesis import given, assume, settings
import hypothesis.strategies as st

import montepy

import pytest

geom_pair = st.tuples(st.integers(min_value=1), st.booleans())


@settings(max_examples=50, deadline=500)
@given(
    st.integers(min_value=1),
    st.lists(geom_pair, min_size=1, max_size=10, unique_by=lambda x: x[0]),
)
def test_build_arbitrary_cell_geometry(first_surf, new_surfaces):
    assume(
        len({first_surf, *[num for num, _ in new_surfaces]}) == len(new_surfaces) + 1
    )
    input = montepy.input_parser.mcnp_input.Input(
        [f"1 0 {first_surf} imp:n=1"], montepy.input_parser.block_type.BlockType.CELL
    )
    cell = montepy.Cell(input)
    surf = montepy.surfaces.surface.Surface()
    surf.number = first_surf
    cell.update_pointers([], [], montepy.surface_collection.Surfaces([surf]))
    for surf_num, operator in new_surfaces:
        surf = montepy.surfaces.surface.Surface()
        surf.number = surf_num
        if operator:
            cell.geometry &= +surf
        else:
            cell.geometry |= -surf
    assert len(cell.geometry) == len(new_surfaces) + 1


def test_cell_geometry_set_warns():
    input = montepy.input_parser.mcnp_input.Input(
        [f"1 0 -1 imp:n=1"], montepy.input_parser.block_type.BlockType.CELL
    )
    cell = montepy.Cell(input)
    with pytest.raises(montepy.errors.IllegalState):
        surf = montepy.surfaces.surface.Surface()
        surf.number = 5
        cell.geometry &= +surf


def test_geom_invalid():
    surf = montepy.AxisPlane()
    with pytest.raises(montepy.errors.IllegalState):
        -surf
    with pytest.raises(montepy.errors.IllegalState):
        +surf
    with pytest.raises(montepy.errors.IllegalState):
        ~montepy.Cell()

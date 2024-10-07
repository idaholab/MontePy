from hypothesis import given
import hypothesis.strategies as st

import montepy

import pytest

geom_pair = st.tuples(st.integers(min_value=1), st.booleans())


@given(
    st.integers(min_value=1), st.lists(geom_pair, min_size=1, unique_by=lambda x: x[0])
)
def test_build_arbitrary_cell_geometry(first_surf, new_surfaces):
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

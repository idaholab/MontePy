import io
from pathlib import Path
import pytest
from tests.test_cell_problem import verify_export as cell_verify

import montepy
from montepy import Cell
from montepy import Universe


@pytest.fixture
def basic_parsed_cell():
    return Cell("1 0 -2 imp:n=1")


@pytest.fixture
def basic_cell():
    cell = montepy.Cell(number=1)
    sphere = montepy.Surface("1 SO 10.0")
    cell.geometry = -sphere
    cell.importance.neutron = 1.0
    return cell


@pytest.fixture
def cells(basic_parsed_cell, basic_cell):
    return (basic_parsed_cell, basic_cell)


@pytest.fixture(scope="module")
def simple_problem():
    return montepy.read_input(Path("tests") / "inputs" / "test.imcnp")


@pytest.fixture
def cp_simple_problem(simple_problem):
    return simple_problem.clone()


def test_universe_setter(cells):
    for basic_cell in cells:
        uni = Universe(5)
        basic_cell.universe = uni
        cell_verify(basic_cell)


def test_fill_setter(cells):
    for basic_cell in cells:
        uni = Universe(5)
        basic_cell.fill.universe = uni
        cell_verify(basic_cell)


def test_lattice_setter(cells):
    for basic_cell in cells:
        basic_cell.lattice = montepy.data_inputs.lattice.Lattice.HEXAHEDRA
        cell_verify(basic_cell)


def test_uni_fill_latt_setter(cells):
    for basic_cell in cells:
        base_uni = montepy.Universe(1)
        lat_uni = montepy.Universe(2)
        basic_cell.lattice = montepy.data_inputs.lattice.Lattice.HEXAHEDRA
        basic_cell.fill.universe = base_uni
        basic_cell.universe = lat_uni
        cell_verify(basic_cell)


def test_mc_workshop_edge_case():
    problem = montepy.read_input(Path("demo") / "pin_cell.imcnp")
    # grab surfaces
    universe = montepy.Universe(1)
    universe.claim(problem.cells)
    problem.universes.append(universe)
    surfs = problem.surfaces
    right_surf = surfs[104]
    left_surf = surfs[103]
    y_top_surf = surfs[106]
    y_bot_surf = surfs[105]
    z_top_surf = surfs[102]
    z_bot_surf = surfs[101]
    # define cell
    unit_cell = montepy.Cell()
    unit_cell.number = problem.cells.request_number()
    problem.cells.append(unit_cell)
    unit_cell.geometry = -right_surf & +left_surf
    unit_cell.geometry &= -y_top_surf & +y_bot_surf
    unit_cell.geometry &= -z_top_surf & +z_bot_surf
    unit_cell.importance.neutron = 1.0
    # set fill and stuff
    unit_cell.lattice = montepy.data_inputs.lattice.Lattice.HEXAHEDRA
    unit_cell.fill.universe = universe
    # assign to own universe
    lat_universe = montepy.Universe(5)
    problem.universes.append(lat_universe)
    unit_cell.universe = lat_universe
    cell_verify(unit_cell)


def test_no_universe(cp_simple_problem):
    prob = cp_simple_problem
    prob.cells[2].universe = montepy.Universe(5)
    new_cell = montepy.Cell(number=55)
    new_cell.geometry = -prob.surfaces[1000]
    prob.cells.append(new_cell)
    prob.print_in_data_block["u"] = True
    with io.StringIO() as fh:
        prob.write_problem(fh)

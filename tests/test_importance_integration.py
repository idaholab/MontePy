import montepy

import io
from pathlib import Path
import pytest


@pytest.fixture
def problem():
    return montepy.read_input(Path("tests") / "inputs" / "test.imcnp")


@pytest.fixture
def importance_problem():
    return montepy.read_input(Path("tests") / "inputs" / "test_importance.imcnp")


def test_print_explicit_default_imp(problem):  # based on #892

    # Modify an existing cell. Importance remains.
    problem.cells[1].geometry &= +problem.surfaces[1000]
    # Cell 2 should give "imp:n=2.0 imp:p=2.0"
    c2 = montepy.Cell(number=4)
    c2.geometry = -problem.surfaces[1000] & +problem.surfaces[1005]
    c2.importance.all = 2.0
    problem.cells.append(c2)
    # Cell 3 should give "imp:n=1.0 imp:p=1.0"
    c3 = montepy.Cell(number=6)
    c3.geometry = -problem.surfaces[1005] & +problem.surfaces[1010]
    c3.importance.neutron = 1.0
    c3.importance.photon = 1.0
    problem.cells.append(c3)
    # Cell 4 should give "imp:n=4.0 imp:p=1.0"
    c4 = montepy.Cell(number=7)
    c4.geometry = -problem.surfaces[1010]
    c4.importance.neutron = 4.0
    problem.cells.append(c4)
    # Cell 5 DOES give "imp:n=5.0 imp:p=1.0"
    c5 = montepy.Cell(number=8)
    c5.geometry = -problem.surfaces[1015]
    c5.importance.neutron = 5.0
    c5.importance.photon = 1.0
    problem.cells.append(c5)
    # Ensure that this is set:
    # Ensure that this is set:
    problem.print_in_data_block["imp"] = False

    stream = io.StringIO()
    problem.write_problem(stream)
    stream.seek(0)
    for line in stream:
        print(line.rstrip())
    stream.seek(0)
    new_problem = montepy.read_input(stream)
    stream.close()
    cells = new_problem.cells
    for cell_num, imp_str in {
        4: "imp:n=2.0 imp:p=2.0",
        6: "imp:n=1.0 imp:p=1.0",
        7: "imp:n=4.0 imp:p=1.0",
        8: "imp:n=5.0 imp:p=1.0",
    }.items():
        print(cell_num, imp_str)
        assert imp_str in cells[cell_num]._input.input_text


def test_splitting_part_combos(problem):  # based on #913
    # Works, but produces invalid MCNP
    c2 = montepy.Cell(number=4)
    c2.geometry = -problem.surfaces[1000] & +problem.surfaces[1005]
    problem.cells.append(c2)
    c2.importance.photon = 2.0
    c2.importance.neutron = 2.0

    # Crashes MontePy
    c3 = montepy.Cell(number=6)
    c3.geometry = -problem.surfaces[1015] & +problem.surfaces[1010]
    problem.cells.append(c3)
    c3.importance.photon = 3.0
    c3.importance.neutron = 4.0

    with io.StringIO() as stream:
        problem.write_problem(stream)
        stream.seek(0)
        print(stream.read())
        stream.seek(0)
        new_problem = montepy.read_input(stream)
        stream.close()

    cells = new_problem.cells
    for cell_num, imp_str in {
        4: "imp:n=2.0 imp:p=2.0",
        6: "imp:n=4.0 imp:p=3.0",
    }.items():
        print(cell_num, imp_str)
        assert imp_str in cells[cell_num]._input.input_text


def test_diverge_after_push_to_cells(importance_problem):  # based on #892 / #913
    """Test that importances can diverge after push_to_cells from data block."""
    problem = importance_problem
    # Trigger push_to_cells by accessing importance (combined imp:n,p in data block)
    _ = problem.cells[1].importance.neutron
    # Diverge cell 1: neutron=2.0, photon stays 1.0
    problem.cells[1].importance.neutron = 2.0
    # Switch to cell-block output
    problem.print_in_data_block["imp"] = False

    with io.StringIO() as stream:
        problem.write_problem(stream)
        stream.seek(0)
        print(stream.read())
        stream.seek(0)
        new_problem = montepy.read_input(stream)

    cell1_text = new_problem.cells[1]._input.input_text
    print("cell 1 text:", cell1_text)
    # Diverged cell must have separate entries, NOT combined imp:n,p
    assert "imp:n=2" in cell1_text
    assert "imp:p=1" in cell1_text
    assert "imp:n,p" not in cell1_text

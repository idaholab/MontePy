import pytest
import montepy
from montepy import Cell, Universe


@pytest.fixture
def basic_parsed_cell():
    cell = montepy.Cell()
    cell.number = 1
    sphere = montepy.Surface("1 SO 10.0")
    cell.geometry = -sphere
    cell.importance.neutron = 1.0
    return cell


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


def test_universe_nullify(cells):
    """Test that universe can be set to None and deleted."""
    for cell in cells:
        # First set a universe
        uni = Universe(5)
        cell.universe = uni
        assert cell.universe == uni
        
        # Test setting to None
        cell.universe = None
        assert cell.universe is None
        
        # Test setting again to a universe
        cell.universe = uni
        assert cell.universe == uni
        
        # Test deleting the universe
        del cell.universe
        assert cell.universe is None

import pytest
import montepy
from montepy import Cell, Universe


@pytest.fixture
def basic_parsed_cell():
    return Cell("1 0 2")


@pytest.fixture
def basic_cell():
    cell = Cell("2 0 1")
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

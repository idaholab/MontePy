# Copyright 2024 - 2025, Battelle Energy Alliance, LLC All Rights Reserved.
import copy
import os
from hypothesis import given, strategies as st
import numpy as np
from types import GeneratorType
import pytest

import montepy

from montepy.input_parser import syntax_node
from montepy.cell import Cell
from montepy.constants import DEFAULT_VERSION
from montepy.exceptions import *
from montepy.input_parser.block_type import BlockType
from montepy.input_parser.mcnp_input import Input, Jump
from montepy.universe import Universe
from montepy.data_inputs.fill import Fill
from montepy.data_inputs.lattice import LatticeType
from montepy.data_inputs.lattice_input import LatticeInput
from montepy.data_inputs.universe_input import UniverseInput


class TestUniverseInput:
    def setup_method(self):
        list_node = syntax_node.ListNode("numbers")
        list_node.append(syntax_node.ValueNode("5", float))
        classifier = syntax_node.ClassifierNode()
        classifier.prefix = "u"
        tree = syntax_node.SyntaxNode(
            "lattice",
            {
                "classifier": classifier,
                "seperator": syntax_node.ValueNode("=", str),
                "data": list_node,
            },
        )
        self.tree = tree
        self.universe = UniverseInput(in_cell_block=True, key="u", value=tree)

    def test_universe_card_init(self):
        universe_input = self.universe
        assert universe_input.old_number == 5
        assert not universe_input.not_truncated
        # test bad float
        with pytest.raises(ValueError):
            tree = copy.deepcopy(self.tree)
            tree["data"].nodes.pop()
            tree["data"].append(syntax_node.ValueNode("5.5", float))
            UniverseInput(in_cell_block=True, key="U", value=tree)

        # test string
        with pytest.raises(ValueError):
            tree["data"].nodes.pop()
            tree["data"].append(syntax_node.ValueNode("hi", str))
            UniverseInput(in_cell_block=True, key="U", value=tree)

        # test negative universe
        tree["data"].nodes.pop()
        tree["data"].append(syntax_node.ValueNode("-3", float))
        universe_input_neg = UniverseInput(in_cell_block=True, key="U", value=tree)
        assert universe_input_neg.old_number == 3
        assert universe_input_neg.not_truncated is True

        universes = [1, 2, 3]
        input_obj = Input(["U " + " ".join(list(map(str, universes)))], BlockType.DATA)
        uni_card = UniverseInput(input_obj)
        assert uni_card.old_numbers == universes

        # test jump
        input_obj = Input(["U J"], BlockType.DATA)
        uni_card = UniverseInput(input_obj)
        assert uni_card.old_numbers[0] == None

        # test bad float
        with pytest.raises(MalformedInputError):
            input_obj = Input(["U 5.5"], BlockType.DATA)
            UniverseInput(input_obj)

        # test bad str
        with pytest.raises(MalformedInputError):
            input_obj = Input(["U hi"], BlockType.DATA)
            UniverseInput(input_obj)

        # test bad negative
        input_obj = Input(["U -2"], BlockType.DATA)
        UniverseInput(input_obj)

    def test_str(self):
        universe_input = copy.deepcopy(self.universe)
        uni = Universe(5)
        universe_input.universe = uni
        output = str(universe_input)
        assert "u=5" in output
        output = repr(universe_input)
        assert "UNIVERSE" in output
        assert "set_in_block: True" in output
        assert "Universe : Universe(5)" in output

    def test_merge(self):
        universe_input = copy.deepcopy(self.universe)
        with pytest.raises(MalformedInputError):
            universe_input.merge(universe_input)

    def test_universe_setter(self):
        universe_input = copy.deepcopy(self.universe)
        uni = Universe(5)
        universe_input.universe = uni
        assert universe_input.universe == uni
        with pytest.raises(TypeError):
            universe_input.universe = 5

    def test_universe_truncate_setter(self):
        universe_input = copy.deepcopy(self.universe)
        assert universe_input.not_truncated is False
        universe_input.not_truncated = True
        assert universe_input.not_truncated is True
        with pytest.raises(TypeError):
            universe_input.not_truncated = 5


class TestUniverse:
    default_test_input_path = os.path.join("tests", "inputs")

    @pytest.mark.parametrize(
        "universe,expected_cells",
        [
            (1, [2, 99, 5]),
        ],
    )
    def test_filled_cells_generator(self, universe, expected_cells):
        problem = montepy.read_input(
            os.path.join(self.default_test_input_path, "test_universe.imcnp")
        )
        cell_generator = problem.universes[universe].filled_cells
        filled_cells = [cell.number for cell in cell_generator]

        assert (
            filled_cells == expected_cells
        ), f"\nExpected: {expected_cells}\nActual: {filled_cells}"

    def test_detached_universe_returns_generator(self):
        """
        Case 1: Universe with no associated problem
        """
        u1 = montepy.Universe(999)

        result = u1.filled_cells
        assert isinstance(result, GeneratorType)
        assert list(result) == []  # Should yield nothing

    def test_init(self):
        universe = Universe(5)
        assert universe.number == 5
        assert universe.old_number == 5
        with pytest.raises(TypeError):
            Universe("hi")
        with pytest.raises(ValueError):
            Universe(-1)

    def test_number_setter(self):
        universe = Universe(5)
        universe.number = 10
        assert universe.number == 10
        with pytest.raises(TypeError):
            universe.number = "hi"
        with pytest.raises(ValueError):
            universe.number = -1


class TestLattice:
    def setup_method(self):
        list_node = syntax_node.ListNode("numbers")
        list_node.append(syntax_node.ValueNode("1", float))
        classifier = syntax_node.ClassifierNode()
        classifier.prefix = syntax_node.ValueNode("lat", str)
        tree = syntax_node.SyntaxNode(
            "lattice",
            {
                "classifier": classifier,
                "seperator": syntax_node.ValueNode("=", str),
                "data": list_node,
            },
        )
        self.tree = tree
        self.lattice = LatticeInput(in_cell_block=True, key="lat", value=tree)

    def test_lattice_init(self):
        lattice = self.lattice
        assert lattice.lattice == LatticeType(1)
        tree = copy.deepcopy(self.tree)
        with pytest.raises(ValueError):
            tree["data"].nodes.pop()
            tree["data"].append(syntax_node.ValueNode("hi", str))
            LatticeInput(in_cell_block=True, key="lat", value=tree)
        with pytest.raises(ValueError):
            tree["data"].nodes.pop()
            tree["data"].append(syntax_node.ValueNode("5", float))
            LatticeInput(in_cell_block=True, key="lat", value=tree)
        lattices = [1, 2, None, None]
        input = Input(["Lat " + " ".join(list(map(str, lattices)))], BlockType.DATA)
        lattice = LatticeInput(input)
        for answer, lattice in zip(lattices, lattice._lattice):
            assert LatticeType(answer) == lattice.value
        with pytest.raises(MalformedInputError):
            input_obj = Input(["Lat 3"], BlockType.DATA)
            LatticeInput(input_obj)
        with pytest.raises(MalformedInputError):
            input_obj = Input(["Lat str"], BlockType.DATA)
            LatticeInput(input_obj)

    def test_lattice_setter(self):
        lattice = copy.deepcopy(self.lattice)
        lattice.lattice = LatticeType(2)
        assert LatticeType(2) == lattice.lattice
        lattice.lattice = 1
        assert LatticeType(1) == lattice.lattice
        lattice.lattice = None
        assert lattice.lattice is None
        with pytest.raises(TypeError):
            lattice.lattice = "hi"

        with pytest.raises(ValueError):
            lattice.lattice = -1

    def test_lattice_deleter(self):
        lattice = self.lattice
        del lattice.lattice
        assert lattice.lattice is None

    def test_lattice_merge(self):
        lattice = self.lattice
        with pytest.raises(MalformedInputError):
            lattice.merge(lattice)

    def test_lattice_cell_format(self):
        lattice = self.lattice
        output = lattice.format_for_mcnp_input(DEFAULT_VERSION)
        assert "lat=1" in output[0]
        lattice.lattice = None
        output = lattice.format_for_mcnp_input(DEFAULT_VERSION)
        assert output == []

    def test_lattice_repr(self):
        lattice = self.lattice
        out = repr(lattice)
        assert "in_cell: True" in out
        assert "set_in_block: True" in out
        assert "Lattice_values : LatticeType.RECTANGULAR" in out

    def test_deprecated_lattice(self):
        assert (
            montepy.data_inputs.lattice.LatticeType.HEXAHEDRAL
            is montepy.data_inputs.lattice.LatticeType.RECTANGULAR
        )
        with pytest.warns(DeprecationWarning, match="HEXAGONAL"):
            montepy.data_inputs.lattice.Lattice.HEXAGONAL
        with pytest.warns(DeprecationWarning, match="RECTANGULAR"):
            lattype = montepy.data_inputs.lattice.Lattice.HEXAHEDRA
        cell = montepy.Cell()
        with pytest.warns(DeprecationWarning):
            cell.lattice = lattype
        with pytest.warns(DeprecationWarning):
            str(cell.lattice)
        with pytest.warns(DeprecationWarning):
            del cell.lattice


class TestFill:
    def setup_method(self):
        list_node = syntax_node.ListNode("num")
        list_node.append(syntax_node.ValueNode("5", float))
        classifier = syntax_node.ClassifierNode()
        classifier.prefix = syntax_node.ValueNode("fill", str)
        tree = syntax_node.SyntaxNode(
            "fill",
            {
                "classifier": classifier,
                "seperator": syntax_node.ValueNode("=", str),
                "data": list_node,
            },
        )
        self.simple_fill = Fill(in_cell_block=True, key="fill", value=tree)

    def test_complex_transform_fill_init(self):
        input = Input(["1 0 -1 *fill=1 (1.5 0.0 0.0)"], BlockType.CELL)
        cell = Cell(input)
        fill = cell.fill
        assert fill.hidden_transform
        assert fill.universes is None
        assert fill.old_universe_number == 1
        assert len(fill.transform.displacement_vector) == 3
        assert fill.transform.is_in_degrees

        input = Input(["1 0 -1 fill=1 (1.5 0.0 0.0)"], BlockType.CELL)
        cell = Cell(input)
        fill = cell.fill
        assert not fill.transform.is_in_degrees

        input = Input(["1 0 -1 fill=5 (3)"], BlockType.CELL)
        cell = Cell(input)
        fill = cell.fill
        assert not fill.hidden_transform
        assert fill.old_universe_number == 5
        assert fill.old_transform_number == 3
        # test sparse fill
        cell = Cell("1 0 -1 fill=0:0 0:1 0:1 1 1 1")
        fill = cell.fill
        assert fill.old_universe_numbers[0, 0, 0] == 1
        assert fill.old_universe_numbers[0, 1, 1] == 0
        # test bad string
        with pytest.raises(ValueError):
            input = Input(["1 0 -1 fill=hi"], BlockType.CELL)
            cell = Cell(input)
            fill = cell.fill
        with pytest.raises(ValueError):
            input = Input(["1 0 -1 fill=1 (hi)"], BlockType.CELL)
            cell = Cell(input)
        # test negative universe
        with pytest.raises(ValueError):
            input = Input(["1 0 -1 fill=-5"], BlockType.CELL)
            cell = Cell(input)
        with pytest.raises(ValueError):
            input = Input(["1 0 -1 fill=5 (-5)"], BlockType.CELL)
            cell = Cell(input)
        with pytest.raises(ValueError):
            input = Input(["1 0 -1 fill=5 1 0 0"], BlockType.CELL)
            cell = Cell(input)

    @pytest.fixture
    def complicated_fill(self):
        input = Input(["1 0 -1 fill=0:1 0:1 0:1 1 2 3 4 5 6 7 8"], BlockType.CELL)
        cell = Cell(input)
        return cell.fill

    def test_complicated_lattice_fill_init(self, complicated_fill):
        fill = copy.deepcopy(complicated_fill)
        assert fill.universe is None
        assert fill.min_index[0] == 0
        assert fill.max_index[2] == 1
        answer = np.array([[[1, 2], [3, 4]], [[5, 6], [7, 8]]]).T
        assert (fill.old_universe_numbers == answer).all()

    @pytest.mark.parametrize(
        "input_str,expected_error",
        [
            ("1 0 -1 fill=0:1 0:1 0:1 hi", ValueError),  # "String universe"
            ("1 0 -1 fill=0:1 hi:1 0:1 hi", ValueError),  # "String index"
            ("1 0 -1 fill=0:1 0:1 0:1 -1", ValueError),  # "Negative universe"
            (
                "1 0 -1 fill=0:1 1:0 0:1 1 2 3 4 5 6 7 8",
                ValueError,
            ),  # "Inverted bounds"
            ("1 0 -1 fill=0:1 0:1.5 0:1 1 2 3 4 5 6 7 8", ValueError),  # "Float bounds"
        ],
    )
    def test_complicated_fill_init_error(self, input_str, expected_error):
        """Test the complicated fill init with various input errors."""
        with pytest.raises(expected_error):
            input = Input([input_str], BlockType.CELL)
            cell = Cell(input)
            fill = cell.fill

    def test_data_fill_init(self):
        input_obj = Input(["FiLl 1 2 3 4"], BlockType.DATA)
        fill = Fill(input_obj)
        answer = [1, 2, 3, 4]
        assert fill.old_universe_numbers == answer
        # jump
        input_obj = Input(["FiLl 1 2J 4"], BlockType.DATA)
        fill = Fill(input_obj)
        answer = [1, None, None, 4]
        assert fill.old_universe_numbers == answer
        # test negative universe
        with pytest.raises(MalformedInputError):
            input_obj = Input(["FiLl 1 -2 3 4"], BlockType.DATA)
            fill = Fill(input_obj)
        # test string universe
        with pytest.raises(MalformedInputError):
            input_obj = Input(["FiLl 1 foo"], BlockType.DATA)
            fill = Fill(input_obj)

    def test_fill_universe_setter(self):

        fill = copy.deepcopy(self.simple_fill)
        uni = montepy.Universe(6)
        fill.universe = uni
        assert fill.universe.number == uni.number
        assert fill.universes is None
        fill.universe = None
        assert fill.universe is None
        fill.universe = uni
        del fill.universe
        assert fill.universe is None
        with pytest.raises(TypeError):
            fill.universe = "hi"
        with pytest.raises(TypeError):
            fill.multiple_universes = "hi"
        fill.multiple_universes = True
        with pytest.raises(ValueError):
            fill.universe = uni

    def test_fill_universes_setter(self, complicated_fill):
        fill = copy.deepcopy(complicated_fill)
        uni = montepy.Universe(10)
        fill_array = np.array([[[uni, uni], [uni, uni]], [[uni, uni], [uni, uni]]])
        fill.universes = fill_array
        assert (fill.universes == fill_array).all()
        del fill.universes
        assert fill.universes is None
        with pytest.raises(TypeError):
            fill.universes = "hi"
        fill.multiple_universes = False
        with pytest.raises(ValueError):
            fill.universes = np.array([1, 2])
        with pytest.raises(TypeError):
            fill.universes = np.array([[["hi"]]])

        with pytest.raises(IllegalState):
            fill.universes = np.array([[[1]]])

        # Test setting universes with integer IDs when a problem is attached
        problem = montepy.MCNP_Problem("test")
        uni1 = montepy.Universe(1)
        problem.universes.append(uni1)
        cell = montepy.Cell(number=1)
        problem.cells.append(cell)
        cell.fill.universes = np.array([[[1, 0]]])
        assert cell.fill.universes[0, 0, 0] is uni1
        assert cell.fill.universes[0, 0, 1] is None

        # Test that it raises IllegalState when no problem is attached
        cell_no_problem = montepy.Cell(number=2)
        with pytest.raises(IllegalState):
            cell_no_problem.fill.universes = np.array([[[1]]])

        # Test that it raises KeyError for bad IDs
        with pytest.raises(KeyError):
            cell.fill.universes = np.array([[[999]]])

        # Test that it raises ValueError for non-3D array
        with pytest.raises(ValueError):
            cell.fill.universes = np.array([1])

        # Test that it raises TypeError for wrong data type in array
        with pytest.raises(TypeError):
            cell.fill.universes = np.array([[["a", "b"]]])

        # Test setting universes to None
        cell.fill.universes = None
        assert cell.fill.universes is None
        assert cell.fill.multiple_universes is False
        assert cell.fill.universe is None

        # Test setting universes with Universe for 2D array
        fill.multiple_universes = True
        uni2 = montepy.Universe(2)
        fill_array_2d = np.array([[uni1, uni2], [uni2, uni1]])
        fill.universes = fill_array_2d
        assert fill.universes.shape == (2, 2, 1)
        assert fill.universes[0, 0, 0] is uni1
        assert fill.universes[1, 0, 0] is uni2

        # Test 1D array raises ValueError
        with pytest.raises(ValueError):
            fill.universes = np.array([uni1, uni2])

        # Test 4D array raises ValueError
        with pytest.raises(ValueError):
            fill.universes = np.zeros((2, 2, 2, 2))

    def test_fill_str(self, complicated_fill):
        fill = copy.deepcopy(complicated_fill)
        output = str(fill)
        assert "Fill" in output
        output = repr(fill)
        assert "Fill" in output

    def test_fill_merge(self):
        input_obj = Input(["FiLl 1 2 3 4"], BlockType.DATA)
        fill1 = Fill(input_obj)
        fill2 = Fill(input_obj)
        with pytest.raises(MalformedInputError):
            fill1.merge(fill2)

    @given(
        indices=st.lists(st.integers(), min_size=3, max_size=3),
        width=st.lists(st.integers(1), min_size=3, max_size=3),
    )
    def test_fill_index_setter(self, indices, width):
        fill = self.simple_fill.clone()
        fill.multiple_universes = True
        fill.min_index = indices
        end = np.array(indices) + np.array(width)
        fill.max_index = end
        assert fill.min_index == indices
        assert (fill.max_index == end).all()

    @pytest.mark.parametrize(
        "attr, value, expected_exc",
        [
            ("min_index", "hi", TypeError),
            ("max_index", "hi", TypeError),
            ("min_index", ["hi"], TypeError),
            ("max_index", ["hi"], TypeError),
            ("min_index", [1], ValueError),
            ("max_index", [1], ValueError),
        ],
    )
    def test_fill_index_bad_setter(self, attr, value, expected_exc):
        fill = self.simple_fill.clone()
        with pytest.raises(expected_exc):
            setattr(fill, attr, value)

    @given(
        universes=st.lists(st.integers(0, 1_000_000), min_size=1, max_size=10),
        y_len=st.integers(1, 10),
        z_len=st.integers(1, 10),
        fill_amount=st.floats(0.9, 1.0),
    )
    @pytest.mark.filterwarnings("ignore")
    def test_fill_multi_unis(self, universes, y_len, z_len, fill_amount):
        fill = self.simple_fill.clone()
        universes = np.array(
            [[[Universe(u) for u in universes]] * y_len]
            * (int(z_len * fill_amount) + 1)
        )
        fill.multiple_universes = True
        fill.universes = universes
        assert (fill.universes == universes).all()
        assert (fill.min_index == np.array([0, 0, 0])).all()
        assert (fill.max_index == np.array(universes.shape) - np.array([1, 1, 1])).all()
        self.verify_export(fill)

    def verify_export(self, fill):
        output = fill.format_for_mcnp_input((6, 3, 0))
        print(output)
        cell = montepy.Cell("1 0 -2 " + "\n".join(output))
        new_fill = cell.fill
        for attr in [
            "multiple_universes",
            "old_universe_numbers",
            "old_universe_number",
        ]:
            old_val = getattr(fill, attr)
            if "old" in attr:
                if attr.endswith("s"):
                    old_val = getattr(fill, "universes")
                    if old_val is not None:
                        numberer = np.vectorize(lambda u: u.number)
                        old_val = numberer(old_val)
                else:
                    old_val = getattr(fill, "universe")
                    if old_val is not None:
                        old_val = old_val.number
            new_val = getattr(new_fill, attr)
            print(attr, old_val, new_val)
            if isinstance(old_val, np.ndarray):
                assert (old_val == new_val).all()
            else:
                assert old_val == new_val

# Copyright 2024, Battelle Energy Alliance, LLC All Rights Reserved.
import montepy
import os, pytest
from montepy.cell import Cell
from montepy.particle import Particle
from montepy.data_inputs.importance import Importance
from montepy.errors import *
from montepy.input_parser import mcnp_input, block_type


def create_cell_from_input(in_str, block=block_type.BlockType.CELL):
    """Helper to create a Cell object from a given input string."""
    card = mcnp_input.Input([in_str], block)
    return Cell(card)


# Parameterized test for valid importance parsing
# Test cases:
# 1. Combined importance for neutrons and photons (IMP:N,P=1)
#    - Tests multiple particle types in single declaration
#    - Verifies default values for unspecified particles
# 2. Separate importance for electrons and protons (IMP:E=1 IMP:H=1)
#    - Tests individual particle importance declarations
@pytest.mark.parametrize(
    "in_str,expected",
    [
        (
            "1 0 -1 IMP:N,P=1",
            {
                "neutron": 1.0,
                "photon": 1.0,
                "all": None,
                "alpha_particle": 0.0,
                "in_cell_block": True,
            },
        ),
        (
            "1 0 -1 IMP:E=1 IMP:H=1",
            {"electron": 1.0, "proton": 1.0},
        ),
    ],
)
def test_importance_parsing_from_cell(in_str, expected):
    """
    Testing all examples of importance input
    """
    cell = create_cell_from_input(in_str)
    for attr, value in expected.items():
        actual = getattr(cell.importance, attr)
        assert actual == value, f"Expected {attr}={value}, got {actual}"


# Parameterized test for invalid importance values
# Test cases:
# 1. Non-numeric value 'h' for importance
#    - Verifies rejection of non-numeric importance values
#    - Should raise ValueError
# 2. Negative value -2 for importance
#    - Verifies rejection of negative importance values
#    - Should raise ValueError since importance must be non-negative
@pytest.mark.parametrize(
    "in_str,expected_exception",
    [
        ("1 0 -1 IMP:N,P=h", ValueError),  # non-numeric value should raise ValueError
        ("1 0 -1 IMP:N,P=-2", ValueError),  # negative value should raise ValueError
    ],
)
def test_invalid_importance_parsing_from_cell(in_str, expected_exception):
    """
    Testing invalid importance values
    Every test shuould Raises ValueError
    """
    with pytest.raises(expected_exception):
        create_cell_from_input(in_str)


# Valid data case: the card should be parsed correctly
@pytest.mark.parametrize(
    "in_str,expected_neutron,expected_photon",
    [
        ("IMP:N,P 1 0", [1.0, 0.0], [1.0, 0.0]),
    ],
)
def test_importance_init_data_valid(in_str, expected_neutron, expected_photon):
    card = mcnp_input.Input([in_str], block_type.BlockType.CELL)
    imp = Importance(card)
    neutron_vals = [
        val.value for val in imp._particle_importances[Particle.NEUTRON]["data"]
    ]
    photon_vals = [
        val.value for val in imp._particle_importances[Particle.PHOTON]["data"]
    ]
    assert neutron_vals == expected_neutron
    assert photon_vals == expected_photon


# Error cases: each input should raise an exception, optionally with additional keyword arguments.
@pytest.mark.parametrize(
    "in_str, kwargs, expected_exception",
    [
        ("IMP:N,P 1 h", {}, ValueError),  # non-numeric importance
        ("IMP:N,P 1 -2", {}, ValueError),  # negative importance
        ("IMP:N,P 1 2", {"in_cell_block": 1}, TypeError),  # bad in_cell_block type
        ("IMP:N,P 1 2", {"key": 1}, TypeError),  # bad key type
        ("IMP:N,P 1 2", {"value": 1}, TypeError),  # bad value type
    ],
)
def test_importance_init_data_invalid(in_str, kwargs, expected_exception):
    card = mcnp_input.Input([in_str], block_type.BlockType.CELL)
    with pytest.raises(expected_exception):
        Importance(card, **kwargs)


class TestImportance:

    @pytest.fixture
    def cell_with_importance(_):
        """
        Returns a cell with combined importance "IMP:N,P=1"
        """
        return create_cell_from_input("1 0 -1 IMP:N,P=1")

    @pytest.fixture
    def empty_cell(_):
        """
        Creates a cell with no importance assignment
        """
        return create_cell_from_input("1 0 -1")

    @pytest.fixture
    def test_importance_values(_):
        """
        Returns a dictionary of test importance values for different particles.
        """
        return {
            Particle.NEUTRON: 2.5,
            Particle.PHOTON: 3.5,
            Particle.ALPHA_PARTICLE: 1.5,
            Particle.ELECTRON: 4.5,
        }

    def test_str_repr_parsed_cells(self, cell_with_importance):
        """
        Test string and repr representations return types are corect.

        Args:
            parsed_cell: Fixture providing a cell with importance assignments
        """
        imp = cell_with_importance.importance
        s = str(imp)
        r = repr(imp)
        # Verify the string outputs are of type str
        assert isinstance(s, str)
        assert isinstance(r, str)

    def test_str_repr_empty_importance(self):
        """
        Test string and repr representations of an empty importance object.
        Should return appropriate messages indicating the object is empty.
        """
        imp = Importance()
        s = str(imp)
        r = repr(imp)
        # Assuming an empty Importance should have this specific string.
        assert s == "IMPORTANCE: Object is empty"
        # For repr, we simply check that it indicates the object is empty.
        # what __repr__ should return if it is not strictly defined. ??
        assert "False" in r

    def test_str_repr_manual_importance(self, test_importance_values):
        """
        Test string and repr representations of a manually constructed importance object.
        Verifies that each particle type and its importance value are correctly represented.
        """
        imp = Importance()
        # Set importance values for each particle type
        for particle, value in test_importance_values.items():
            setattr(imp, particle.name.lower(), value)

        s = str(imp)
        r = repr(imp)

        # Check that particle names and their values appear in string representation
        for particle, value in test_importance_values.items():
            assert f"{particle.name.lower()}={value}" in s
            assert str(value) in r

    def test_importance_iter_getter_in(self, cell_with_importance):
        """
        Test iteration, getter methods and 'in' operator for importance objects.
        Verifies correct access to particle importances and type checking.

        Args:
            parsed_cells: Fixture providing cells with importance assignments
        """
        cell = cell_with_importance
        imp = cell.importance
        particles = [
            Particle.NEUTRON,
            Particle.PHOTON,
        ]
        for particle in imp:
            assert particle in particles
            assert (
                abs(imp[particle] - 1.0) < 1e-10
            )  # pytest equivalent of assertAlmostEqual
        for particle in particles:
            assert particle in imp
        with pytest.raises(TypeError):
            imp["hi"]

    def test_importance_all_setter(self, cell_with_importance):
        """
        Test the 'all' setter for importance values.

        Args:
            parsed_cells: Fixture providing cells with importance assignments
        """
        cell = cell_with_importance
        problem = montepy.mcnp_problem.MCNP_Problem("foo")
        problem.mode.add(Particle.NEUTRON)
        problem.mode.add(Particle.PHOTON)
        imp = cell.importance
        cell.link_to_problem(problem)
        imp.all = 2.0
        assert imp.neutron == 2.0
        assert imp.photon == 2.0
        # try wrong type
        with pytest.raises(TypeError):
            imp.all = "h"
        # try negative type
        with pytest.raises(ValueError):
            imp.all = -2.0

    def test_importance_setter(self, cell_with_importance, test_importance_values):
        """
        Test setting individual particle importance values.

        Args:
            parsed_cells: Fixture providing cells with importance assignments
        """
        cell = cell_with_importance
        # Test setting first value from test values
        particle, value = next(iter(test_importance_values.items()))
        cell.importance[particle] = value
        assert cell.importance[particle] == value

        cell.importance.neutron = 2.5
        assert cell.importance.neutron == 2.5
        problem = montepy.mcnp_problem.MCNP_Problem("foo")
        cell.link_to_problem(problem)
        # test problem mode enforcement
        with pytest.raises(ValueError):
            cell.importance.photon = 1.0
        # test wrong type
        with pytest.raises(TypeError):
            cell.importance.neutron = "h"
        # test negative
        with pytest.raises(ValueError):
            cell.importance.neutron = -0.5

        cell.importance[Particle.NEUTRON] = 3
        assert cell.importance.neutron == 3.0
        with pytest.raises(TypeError):
            cell.importance[""] = 5
        with pytest.raises(TypeError):
            cell.importance[Particle.NEUTRON] = ""
        with pytest.raises(ValueError):
            cell.importance[Particle.NEUTRON] = -1.0

    def test_importance_deleter(self, cell_with_importance):
        """
        Test deletion of importance values.

        Args:
            parsed_cells: Fixture providing cells with importance assignments
        """
        cell = cell_with_importance
        del cell.importance.neutron
        assert cell.importance.neutron == 0.0
        del cell.importance[Particle.PHOTON]
        assert cell.importance.photon == 0.0
        with pytest.raises(TypeError):
            del cell.importance[""]

    def test_importance_merge(self):
        """
        Test merging of importance objects.
        Verifies proper combination of importance data and proper error handling.
        """
        in_str = "IMP:N,P 1 0"
        card = mcnp_input.Input([in_str], block_type.BlockType.DATA)
        imp1 = Importance(card)
        in_str = "IMP:E 0 0"
        card = mcnp_input.Input([in_str], block_type.BlockType.DATA)
        imp2 = Importance(card)
        imp1.merge(imp2)
        assert [
            val.value for val in imp1._particle_importances[Particle.NEUTRON]["data"]
        ] == [1.0, 0.0]
        assert [
            val.value for val in imp1._particle_importances[Particle.ELECTRON]["data"]
        ] == [0.0, 0.0]
        # test bad type
        with pytest.raises(TypeError):
            imp1.merge("hi")
        # test bad block type
        in_str = "1 0 -1 IMP:N,P=1"
        card = mcnp_input.Input([in_str], block_type.BlockType.CELL)
        cell = Cell(card)
        with pytest.raises(ValueError):
            imp1.merge(cell.importance)
        in_str = "IMP:P 0 0"
        card = mcnp_input.Input([in_str], block_type.BlockType.CELL)
        imp2 = Importance(card)
        with pytest.raises(MalformedInputError):
            imp1.merge(imp2)


def test_redundant_importance():
    with pytest.raises(MalformedInputError):
        montepy.read_input(os.path.join("tests", "inputs", "test_imp_redundant.imcnp"))


def test_default_importance_not_implemented():
    prob = montepy.read_input(os.path.join("tests", "inputs", "test_not_imp.imcnp"))
    prob.print_in_data_block["imp"] = True
    with pytest.raises(NotImplementedError):
        prob.write_problem(io.StringIO())

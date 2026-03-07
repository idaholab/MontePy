# Copyright 2024, Battelle Energy Alliance, LLC All Rights Reserved.
import montepy
import os
import io
import pytest
from montepy.cell import Cell
from montepy.particle import Particle
from montepy.data_inputs.importance import Importance
from montepy.exceptions import *
from montepy.input_parser import mcnp_input, block_type


class TestImportance:
    default_test_input_path = os.path.join("tests", "inputs")

    def create_cell_from_input(self, in_str, block=block_type.BlockType.CELL):
        """Helper to create a Cell object from a given input string."""
        card = mcnp_input.Input([in_str], block)
        return Cell(card)

    @pytest.mark.parametrize(
        "in_str, expected, error",
        [
            # Valid cases
            (
                "1 0 -1 IMP:N,P=1",
                {
                    "neutron": 1.0,
                    "photon": 1.0,
                    "all": None,
                    "alpha_particle": 1.0,
                    "in_cell_block": True,
                },
                None,
            ),
            (
                "1 0 -1 IMP:E=1 IMP:H=1",
                {"electron": 1.0, "proton": 1.0},
                None,
            ),
            (
                "1 0 -1",
                {"neutron": 1.0},
                None,
            ),  # default neutron importance when nothing is set
            # Error cases
            ("1 0 -1 IMP:N,P=h", None, ValueError),  # non-numeric value
            ("1 0 -1 IMP:N,P=-2", None, ValueError),  # negative value
            ("1 0 -1 IMP:N,xx=2", None, ParsingError),  # invalid particle type
        ],
    )
    def test_importance_parsing_from_cell(self, in_str, expected, error):
        """Test importance parsing from cell input string."""
        if error is not None:
            with pytest.raises(error):
                self.create_cell_from_input(in_str)
        else:
            cell = self.create_cell_from_input(in_str)
            for attr, value in expected.items():
                actual = getattr(cell.importance, attr)
                assert actual == pytest.approx(
                    value
                ), f"Expected {attr}={value}, got {actual}"

    @pytest.mark.parametrize(
        "in_str, expected_values",
        [
            (
                "IMP:N,P 1 0",
                {
                    Particle.NEUTRON: [1.0, 0.0],
                    Particle.PHOTON: [1.0, 0.0],
                },
            ),
            (
                "IMP:N,P,E 1 0 2",
                {
                    Particle.NEUTRON: [1.0, 0.0, 2.0],
                    Particle.PHOTON: [1.0, 0.0, 2.0],
                    Particle.ELECTRON: [1.0, 0.0, 2.0],
                },
            ),
        ],
    )
    def test_importance_init_data_valid(self, in_str, expected_values):
        """Test importance data initialization for multiple particles."""
        imp = Importance(in_str)
        for particle, value in expected_values.items():
            actual = [val.value for val in imp._particle_importances[particle]["data"]]
            assert actual == pytest.approx(
                value
            ), f"For {particle.name}, expected {value}, got {actual}"

    @pytest.mark.parametrize(
        "in_str, kwargs, expected_exception",
        [
            ("IMP:N,P 1 h", {}, ValueError),  # non-numeric importance
            ("IMP:N,P 1 -2", {}, ValueError),  # negative importance
            ("IMP:N,P 1 2", {"in_cell_block": 1}, TypeError),  # bad in_cell_block type
            ("IMP:N,P 1 2", {"key": 1}, TypeError),  # bad key type
            ("IMP:N,P 1 2", {"value": 1}, TypeError),  # bad value type
            ("IMP:N,zz 1 2", {}, ParsingError),  # invalid particle type
        ],
    )
    def test_importance_init_data_invalid(self, in_str, kwargs, expected_exception):
        """Test invalid importance data initialization."""
        with pytest.raises(expected_exception):
            Importance(in_str, **kwargs)

    @pytest.fixture
    def cell_with_importance(self):
        """
        Fixture providing a cell with importance assignments and block_type.BlockType.CELL
        """
        return self.create_cell_from_input("1 0 -1 IMP:N,P=1")

    @pytest.fixture
    def empty_cell(self):
        return self.create_cell_from_input("1 0 -1")

    @pytest.fixture
    def test_importance_values(self):
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
        ms = imp.mcnp_str()
        # Verify the string outputs are of type str
        assert isinstance(s, str)
        assert isinstance(r, str)
        assert isinstance(ms, str)

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

    def test_importance_manual_assignment_and_str_repr(self, test_importance_values):
        """
        Test manual assignment of importance values and their string representations.
        Verifies:
        1. Setting importance values for different particles
        2. Getting assigned values back
        3. String representation includes all assignments
        4. Repr string contains all values
        """
        imp = Importance()

        # Set and verify importance values for each particle type
        for particle, value in test_importance_values.items():
            setattr(imp, particle.name.lower(), value)
            assert getattr(imp, particle.name.lower()) == pytest.approx(value)

        # Verify string representation contains all assignments
        s = str(imp)
        for particle, value in test_importance_values.items():
            particle_str = particle.name.lower()
            assert f"{particle_str}={value}" in s

        # Verify repr contains all values in some form
        r = repr(imp)
        for value in test_importance_values.values():
            assert str(value) in r

    def test_importance_iter_getter_in(self, cell_with_importance):
        cell = cell_with_importance
        imp = cell.importance
        particles = [
            Particle.NEUTRON,
            Particle.PHOTON,
        ]
        for particle in imp:
            assert particle in particles
            assert imp[particle] == pytest.approx(1.0)
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
        assert imp.neutron == pytest.approx(2.0)
        assert imp.photon == pytest.approx(2.0)
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
        assert cell.importance[particle] == pytest.approx(value)

        cell.importance.neutron = 2.5
        assert cell.importance.neutron == pytest.approx(2.5)
        problem = montepy.mcnp_problem.MCNP_Problem("foo")
        cell.link_to_problem(problem)
        # test problem mode enforcement
        with pytest.raises(ParticleTypeNotInProblem):
            cell.importance.photon = 1.0
        # test wrong type
        with pytest.raises(TypeError):
            cell.importance.neutron = "h"
        # test negative
        with pytest.raises(ValueError):
            cell.importance.neutron = -0.5

        cell.importance[Particle.NEUTRON] = 3
        assert cell.importance.neutron == pytest.approx(3.0)
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
        assert cell.importance.neutron == pytest.approx(1.0)
        del cell.importance[Particle.PHOTON]
        assert cell.importance.photon == pytest.approx(1.0)
        with pytest.raises(TypeError):
            del cell.importance[""]

    def test_importance_merge(self, cell_with_importance):
        """
        Test merging of importance objects.
        Verifies proper combination of importance data and proper error handling.
        """
        imp1 = Importance("IMP:N,P 1 0")  # Updated initialization
        imp2 = Importance("IMP:E 0 0")  # Updated initialization
        imp1.merge(imp2)

        assert [
            val.value for val in imp1._particle_importances[Particle.NEUTRON]["data"]
        ] == pytest.approx([1.0, 0.0])
        assert [
            val.value for val in imp1._particle_importances[Particle.ELECTRON]["data"]
        ] == pytest.approx([0.0, 0.0])
        # test bad type
        with pytest.raises(TypeError):
            imp1.merge("hi")
        # test bad block type
        with pytest.raises(ValueError):
            imp1.merge(cell_with_importance.importance)
        in_str = "IMP:P 0 0"
        imp2 = Importance(in_str)
        with pytest.raises(MalformedInputError):
            imp1.merge(imp2)

    def test_redundant_importance(self):
        with pytest.raises(MalformedInputError):
            montepy.read_input(
                os.path.join(self.default_test_input_path, "test_imp_redundant.imcnp")
            )

    def test_default_importance_not_implemented(self):
        prob = montepy.read_input(
            os.path.join(self.default_test_input_path, "test_not_imp.imcnp")
        )
        prob.print_in_data_block["imp"] = True
        with pytest.raises(NotImplementedError):
            prob.write_problem(io.StringIO())

    def test_default_cell_importance(self):
        """Test that new cells have default importance of 1.0 (Issue #735)"""
        cell = montepy.Cell()
        assert cell.importance.neutron == 1.0

    # --- Regression tests for Issue #892 ---

    def _make_problem_with_mode(self, *particles):
        """Helper: create a minimal MCNP_Problem with the given mode particles."""
        prob = montepy.mcnp_problem.MCNP_Problem("fake.i")
        for p in particles:
            prob.mode.add(p)
        return prob

    def test_892_importance_all_before_append(self):
        """importance.all set BEFORE deck.cells.append() must be preserved (Issue #892)."""
        prob = montepy.read_input(
            os.path.join(self.default_test_input_path, "test_importance.imcnp")
        )
        # prob has mode n p e; surfaces[1000] is a sphere
        new_cell = montepy.Cell(number=10)
        new_cell.geometry = -prob.surfaces[1000]
        # Set importance BEFORE appending to the problem
        new_cell.importance.all = 2.0
        prob.cells.append(new_cell)

        # After append, importances for all mode particles must be 2.0
        for particle in prob.mode:
            assert new_cell.importance[particle] == pytest.approx(
                2.0
            ), f"Expected importance[{particle}] == 2.0 after all= set before append"

        # has_information must be True so the cell is written out
        assert new_cell.importance.has_information

        # Round-trip: write and verify imp appears in the cell block
        out = io.StringIO()
        prob.write_problem(out)
        output = out.getvalue()
        assert "imp" in output.lower() or "IMP" in output

    def test_892_importance_all_after_append(self):
        """importance.all set AFTER deck.cells.append() must set all mode particles (Issue #892)."""
        prob = montepy.read_input(
            os.path.join(self.default_test_input_path, "test_importance.imcnp")
        )
        new_cell = montepy.Cell(number=11)
        new_cell.geometry = -prob.surfaces[1000]
        prob.cells.append(new_cell)
        # Set importance AFTER appending
        new_cell.importance.all = 2.0

        for particle in prob.mode:
            assert new_cell.importance[particle] == pytest.approx(
                2.0
            ), f"Expected importance[{particle}] == 2.0 after all= set after append"
        assert new_cell.importance.has_information

    def test_892_importance_individual_default_value(self):
        """Explicitly setting importances to default value (1.0) must still be written (Issue #892)."""
        prob = self._make_problem_with_mode(Particle.NEUTRON, Particle.PHOTON)
        new_cell = montepy.Cell(number=5)
        new_cell.importance.neutron = 1.0
        new_cell.importance.photon = 1.0
        prob.cells.append(new_cell)

        # Even though values equal default, they were explicitly set
        assert new_cell.importance._explicitly_set
        assert (
            new_cell.importance.has_information
        ), "has_information should be True when importance was explicitly set to default"

    def test_892_importance_all_default_value_still_written(self):
        """importance.all = 1.0 (default) set before append must still be marked for writing (Issue #892)."""
        prob = self._make_problem_with_mode(Particle.NEUTRON, Particle.PHOTON)
        new_cell = montepy.Cell(number=6)
        new_cell.importance.all = 1.0  # default value, but explicitly set
        prob.cells.append(new_cell)

        assert new_cell.importance._explicitly_set
        assert (
            new_cell.importance.has_information
        ), "has_information should be True when importance.all = 1.0 was explicitly set"

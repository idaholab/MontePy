# Copyright 2024-2026, Battelle Energy Alliance, LLC All Rights Reserved.
"""Tests for :func:`montepy.from_model_xml`."""

import math
import os
import random
import re
import warnings
import xml.etree.ElementTree as ET

import numpy as np
import pytest

import montepy
from montepy.exceptions import UnsupportedFeature
from montepy.geometry_operators import Operator
from montepy.input_parser import openmc_reader
from montepy.surfaces.half_space import UnitHalfSpace

MODEL = os.path.join(os.path.dirname(__file__), "inputs", "openmc_model.xml")

_problem_cache = []


def get_problem():
    """The problem made from the big model. Tests must not change it."""
    if not _problem_cache:
        _problem_cache.append(montepy.from_model_xml(MODEL))
    return _problem_cache[0]


def write_model(tmp_path, geometry, materials=""):
    path = os.path.join(str(tmp_path), "model.xml")
    with open(path, "w") as fh:
        fh.write(
            f"<?xml version='1.0' encoding='utf-8'?>\n<model>\n"
            f"<materials>{materials}</materials>\n"
            f"<geometry>{geometry}</geometry>\n"
            f"<settings><particles>100</particles></settings>\n</model>\n"
        )
    return path


WATER = """
<material id="1" name="water">
  <density value="1.0" units="g/cm3"/>
  <nuclide name="H1" ao="2.0"/>
  <nuclide name="O16" ao="1.0"/>
</material>
"""

SPHERE_WORLD = """
<cell id="1" material="1" region="-1" universe="0"/>
<surface id="1" type="sphere" boundary="vacuum" coeffs="0 0 0 10"/>
"""

# ----------------------------------------------------------------------------
# A small, independent, point locator for OpenMC's XML, and for MontePy's objects
# ----------------------------------------------------------------------------

_OPENMC_SURFACES = {
    "x-plane": lambda p, c: p[0] - c[0],
    "y-plane": lambda p, c: p[1] - c[0],
    "z-plane": lambda p, c: p[2] - c[0],
    "x-cylinder": lambda p, c: (p[1] - c[0]) ** 2 + (p[2] - c[1]) ** 2 - c[2] ** 2,
    "y-cylinder": lambda p, c: (p[0] - c[0]) ** 2 + (p[2] - c[1]) ** 2 - c[2] ** 2,
    "z-cylinder": lambda p, c: (p[0] - c[0]) ** 2 + (p[1] - c[1]) ** 2 - c[2] ** 2,
    "sphere": lambda p, c: sum((p[i] - c[i]) ** 2 for i in range(3)) - c[3] ** 2,
}

_MCNP_SURFACES = {
    "PX": _OPENMC_SURFACES["x-plane"],
    "PY": _OPENMC_SURFACES["y-plane"],
    "PZ": _OPENMC_SURFACES["z-plane"],
    "C/X": _OPENMC_SURFACES["x-cylinder"],
    "C/Y": _OPENMC_SURFACES["y-cylinder"],
    "C/Z": _OPENMC_SURFACES["z-cylinder"],
    "CX": lambda p, c: p[1] ** 2 + p[2] ** 2 - c[0] ** 2,
    "CY": lambda p, c: p[0] ** 2 + p[2] ** 2 - c[0] ** 2,
    "CZ": lambda p, c: p[0] ** 2 + p[1] ** 2 - c[0] ** 2,
    "S": _OPENMC_SURFACES["sphere"],
    "SO": lambda p, c: sum(x**2 for x in p) - c[0] ** 2,
}


class OpenMCModel:
    """Finds the material at a point directly from the XML."""

    def __init__(self, path):
        geometry = ET.parse(path).getroot().find("geometry")
        self.surfaces = {
            int(s.get("id")): (
                s.get("type"),
                [float(c) for c in s.get("coeffs").split()],
            )
            for s in geometry.findall("surface")
        }
        self.universes = {}
        filled = set()
        for elem in geometry.findall("cell"):
            cell = {"id": int(elem.get("id")), "region": None}
            if elem.get("region"):
                cell["region"] = compile(
                    self._to_python(elem.get("region")), "r", "eval"
                )
            cell["fill"] = int(elem.get("fill")) if elem.get("fill") else None
            mat = elem.get("material")
            cell["material"] = int(mat) if mat not in {None, "void"} else None
            cell["translation"] = [
                float(x) for x in elem.get("translation", "0 0 0").split()
            ]
            self.universes.setdefault(int(elem.get("universe", "0")), []).append(cell)
            filled.add(cell["fill"])
        self.lattices = {}
        for elem in geometry.findall("lattice"):
            shape = [
                int(n)
                for n in elem.get("dimension", elem.findtext("dimension")).split()
            ]
            ids = [int(u) for u in elem.findtext("universes").split()]
            n_dim = len(shape)
            nx, ny = shape[:2]
            nz = shape[2] if n_dim == 3 else 1
            self.lattices[int(elem.get("id"))] = {
                "shape": [nx, ny, nz][:n_dim],
                "pitch": [float(x) for x in elem.findtext("pitch").split()],
                "lower_left": [float(x) for x in elem.findtext("lower_left").split()],
                # [z][y from the top][x]
                "universes": np.array(ids).reshape((nz, ny, nx)),
                "outer": int(elem.get("outer")) if elem.get("outer") else None,
            }
            filled.update(ids)
            filled.add(self.lattices[int(elem.get("id"))]["outer"])
        (self.root,) = set(self.universes) - filled

    @staticmethod
    def _to_python(region):
        out = []
        after_operand = False
        for token in re.findall(r"[()|~]|[+-]?\d+", region):
            if token == "|":
                out.append(" or ")
                after_operand = False
                continue
            if token == ")":
                out.append(")")
                after_operand = True
                continue
            if after_operand:
                out.append(" and ")
            after_operand = False
            if token == "(":
                out.append("(")
            elif token == "~":
                out.append(" not ")
            else:
                out.append(
                    f"(s({token[1:]}) < 0)" if token[0] == "-" else f"(s({token}) > 0)"
                )
                after_operand = True
        return "".join(out)

    def find(self, point, universe=None):
        """Returns the material ID, None for a void, "outside" of the root universe, or "undefined"."""
        if universe is None:
            answer = self.find(point, self.root)
            return "outside" if answer == "not found" else answer
        if universe in self.lattices:
            return self._find_in_lattice(point, self.lattices[universe])

        def sense(number):
            kind, coeffs = self.surfaces[number]
            return _OPENMC_SURFACES[kind](point, coeffs)

        for cell in self.universes[universe]:
            if cell["region"] is None or eval(cell["region"], {"s": sense}):
                if cell["fill"] is None:
                    return cell["material"]
                new_point = [x - t for x, t in zip(point, cell["translation"])]
                answer = self.find(new_point, cell["fill"])
                return "undefined" if answer == "not found" else answer
        return "not found"

    def _find_in_lattice(self, point, lattice):
        shape, pitch, lower_left = (
            lattice["shape"],
            lattice["pitch"],
            lattice["lower_left"],
        )
        index = [
            math.floor((point[i] - lower_left[i]) / pitch[i]) for i in range(len(shape))
        ]
        local = list(point)
        for i in range(len(shape)):
            local[i] = point[i] - (lower_left[i] + (index[i] + 0.5) * pitch[i])
        if all(0 <= index[i] < shape[i] for i in range(len(shape))):
            i, j = index[:2]
            k = index[2] if len(shape) == 3 else 0
            universe = lattice["universes"][k, shape[1] - 1 - j, i]
        elif lattice["outer"] is not None:
            universe = lattice["outer"]
        else:
            return "undefined"
        answer = self.find(local, int(universe))
        return "undefined" if answer == "not found" else answer


class MontePyModel:
    """Finds the material at a point from the MontePy objects, with MCNP's rules."""

    def __init__(self, problem):
        self.universes = {}
        for cell in problem.cells:
            self.universes.setdefault(cell.universe.number, []).append(cell)

    def _is_inside(self, half_space, point):
        if isinstance(half_space, UnitHalfSpace):
            surface = half_space.divider
            func = _MCNP_SURFACES[surface.surface_type.value]
            return (func(point, surface.surface_constants) > 0) == half_space.side
        left = self._is_inside(half_space.left, point)
        if half_space.operator == Operator.GROUP:
            return left
        if half_space.operator == Operator.INTERSECTION:
            return left and self._is_inside(half_space.right, point)
        assert half_space.operator == Operator.UNION
        return left or self._is_inside(half_space.right, point)

    def find(self, point, universe=0):
        """Returns the material number, None for a void, "outside" if killed, or "undefined"."""
        for cell in self.universes[universe]:
            if cell.lattice_type is not None:
                return self._find_in_lattice(point, cell)
            if not self._is_inside(cell.geometry, point):
                continue
            if cell.importance.neutron == 0:
                return "outside"
            if cell.fill.universe is None:
                return cell.material.number if cell.material else None
            if cell.fill.transform is not None:
                transform = cell.fill.transform
                assert not np.any(transform.rotation_matrix)
                point = [x - t for x, t in zip(point, transform.displacement_vector)]
            return self.find(point, cell.fill.universe.number)
        return "undefined"

    def _find_in_lattice(self, point, cell):
        """Element [0, 0, 0] is the cell; the index increases across the 1st, 3rd, and 5th surfaces."""
        halves = list(cell.geometry)
        index = [0, 0, 0]
        local = list(point)
        for axis in range(len(halves) // 2):
            upper, lower = halves[2 * axis : 2 * axis + 2]
            assert not upper.side and lower.side
            assert upper.divider.surface_type.value == f"P{'XYZ'[axis]}"
            high, low = upper.divider.location, lower.divider.location
            index[axis] = math.floor((point[axis] - low) / (high - low))
            # the origin of the filling universe moves with the element
            local[axis] = point[axis] - index[axis] * (high - low)
        fill = cell.fill
        if fill.multiple_universes:
            index = [i - m for i, m in zip(index, fill.min_index)]
            if not all(0 <= i < n for i, n in zip(index, fill.universes.shape)):
                return "undefined"
            universe = fill.universes[tuple(index)]
        else:
            universe = fill.universe
        return self.find(local, universe.number)


def compare_at_random_points(path, problem, n_points, extents, seed=1):
    openmc_model = OpenMCModel(path)
    montepy_model = MontePyModel(problem)
    rng = random.Random(seed)
    found = set()
    for i in range(n_points):
        extent = extents[i % len(extents)]
        point = [rng.uniform(-extent, extent) for _ in range(3)]
        expected = openmc_model.find(point)
        answer = montepy_model.find(point)
        assert answer == expected, f"At {point}: OpenMC: {expected}, MontePy: {answer}"
        found.add(answer)
    return found


# ----------------------------------------------------------------------------
# The big model
# ----------------------------------------------------------------------------


def test_model_is_exported():
    assert montepy.from_model_xml is openmc_reader.from_model_xml


def test_model_object_counts():
    problem = get_problem()
    assert isinstance(problem, montepy.MCNP_Problem)
    # 289 from OpenMC + the graveyard
    assert len(problem.cells) == 290
    # 123 from OpenMC + the sphere for the cells with no region
    assert len(problem.surfaces) == 124
    assert len(problem.materials) == 8
    assert "openmc_model.xml" in problem.title.title
    # settings, tallies, and plots are ignored
    assert len(problem.data_inputs) == 8
    assert len(problem.transforms) == 0


def test_model_numbers_are_the_openmc_ids():
    problem = get_problem()
    geometry = ET.parse(MODEL).getroot().find("geometry")
    cell_ids = [int(c.get("id")) for c in geometry.findall("cell")]
    surface_ids = [int(s.get("id")) for s in geometry.findall("surface")]
    assert [c.number for c in problem.cells] == cell_ids + [291]
    assert [s.number for s in problem.surfaces] == surface_ids + [612]
    assert [m.number for m in problem.materials] == list(range(1, 9))


def test_model_names_are_comments():
    problem = get_problem()
    assert "FNS/sample" in problem.cells[288].leading_comments
    assert "heu" in problem.materials[6].leading_comments
    # cell 290 has no name
    assert len(problem.cells[290].leading_comments) == 0


def test_model_materials():
    problem = get_problem()
    heu = problem.materials[6]
    assert not heu.is_atom_fraction
    assert [(n.ZAID, f) for n, f in heu] == [
        (92234, 0.0102),
        (92235, 0.9371),
        (92238, 0.0527),
    ]
    assert all(str(nuclide.library) == "" for nuclide, _ in heu)
    helium = problem.materials[5]
    assert helium.is_atom_fraction
    assert [(n.ZAID, f) for n, f in helium] == [(2003, 1.0)]
    assert len(problem.materials[4]) == 21


@pytest.mark.parametrize(
    "cell_num, mat_num, density",
    [
        (288, 6, 18.74),  # g/cm3
        (1, 1, 0.001205),  # 1.205 kg/m3
        (132, 5, 0.00025),  # 0.25 kg/m3
        (40, 7, 0.93),
    ],
)
def test_model_cell_materials(cell_num, mat_num, density):
    cell = get_problem().cells[cell_num]
    assert cell.material.number == mat_num
    assert cell.is_mass_dens
    assert cell.mass_density == density


def test_model_surfaces():
    problem = get_problem()
    surface = problem.surfaces[144]
    assert isinstance(surface, montepy.YCylinderParAxis)
    assert surface.coordinates == (0.0, 4.0)
    assert surface.radius == 1.6
    # a cylinder on the axis is simplified
    surface = problem.surfaces[605]
    assert isinstance(surface, montepy.YCylinder)
    assert surface.radius == 1.905
    surface = problem.surfaces[2]
    assert isinstance(surface, montepy.YPlane)
    assert surface.location == -12.600000000000001
    # vacuum is not a property of a surface in MCNP
    assert not problem.surfaces[606].is_reflecting
    assert not problem.surfaces[606].is_white_boundary
    for surface in problem.surfaces:
        surface.validate()


def test_model_universes():
    problem = get_problem()
    # universe 94 is the root universe
    assert 94 not in [u.number for u in problem.universes]
    root_cell = problem.cells[290]
    assert root_cell.universe.number == 0
    assert root_cell.fill.universe.number == 93
    assert root_cell.fill.transform is None
    assert [c.number for c in problem.universes[4].cells] == [78, 79]
    assert len(list(problem.universes[4].filled_cells)) == 73
    void_cell = problem.cells[78]
    assert void_cell.material is None
    assert void_cell.fill.universe.number == 3


def test_model_fill_translations():
    problem = get_problem()
    cell = problem.cells[140]
    assert cell.universe.number == 21
    assert cell.fill.universe.number == 4
    transform = cell.fill.transform
    assert transform.hidden_transform
    assert list(transform.displacement_vector) == [-35.56, -27.94, -17.78]
    assert not np.any(transform.rotation_matrix)
    # no region in OpenMC: bounded by the "all of space" sphere
    # no region in OpenMC: both sides of a plane, which is still all of space
    assert str(cell.geometry) == "(+612:-612)"
    plane = problem.surfaces[612]
    assert isinstance(plane, montepy.ZPlane)
    assert plane.location == 0.0
    assert "140 0 612 : -612 imp:n=1.0 U=21" in cell.mcnp_str()
    # the same plane is used for all 75 of these cells
    assert len(list(plane.cells)) == 75
    assert "FILL=4 (-35.56 -27.94 -17.78 )" in cell.mcnp_str()


def test_model_graveyard():
    problem = get_problem()
    outside = problem.cells[291]
    assert outside.importance.neutron == 0.0
    assert outside.material is None
    assert outside.universe.number == 0
    sides = {(unit.divider.number, unit.side) for unit in outside.geometry}
    assert sides == {
        (606, False),
        (607, True),
        (608, False),
        (609, True),
        (610, False),
        (611, True),
    }
    assert "-606 : 607 : -608 : 609 : -610 : 611" in outside.mcnp_str()
    for cell in problem.cells:
        if cell is not outside:
            assert cell.importance.neutron == 1.0


def test_graveyard_flag(tmp_path):
    problem = montepy.from_model_xml(MODEL, graveyard=False)
    assert len(problem.cells) == 289
    assert 291 not in problem.cells.numbers
    assert all(cell.importance.neutron == 1.0 for cell in problem.cells)
    # the user can then add their own
    surfaces = problem.surfaces
    graveyard = montepy.Cell(number=999)
    graveyard.geometry = (
        -surfaces[606]
        | +surfaces[607]
        | -surfaces[608]
        | +surfaces[609]
        | -surfaces[610]
        | +surfaces[611]
    )
    graveyard.importance.neutron = 0.0
    problem.cells.append(graveyard)
    compare_at_random_points(MODEL, problem, 300, [160.0, 45.0])
    path = write_model(tmp_path, SPHERE_WORLD, WATER)
    assert len(montepy.from_model_xml(path).cells) == 2
    assert len(montepy.from_model_xml(path, graveyard=False).cells) == 1
    with pytest.raises(TypeError):
        montepy.from_model_xml(path, graveyard="yes")


def evaluate(half_space, senses):
    """Whether a point is in the geometry, given which surfaces it is on the positive side of."""
    if isinstance(half_space, UnitHalfSpace):
        return senses[half_space.divider.number] == half_space.side
    left = evaluate(half_space.left, senses)
    if half_space.operator == Operator.GROUP:
        return left
    right = evaluate(half_space.right, senses)
    if half_space.operator == Operator.INTERSECTION:
        return left and right
    assert half_space.operator == Operator.UNION
    return left or right


def assert_same_geometry(old, new, rng):
    """Checks that two geometries are the same set logic.

    The trees are not the same: the parser makes ``((a b) c) d``,
    and the converter makes the balanced ``(a b) (c d)``.
    """
    old_sides = [(unit.divider.number, unit.side) for unit in old]
    new_sides = [(unit.divider.number, unit.side) for unit in new]
    assert old_sides == new_sides
    numbers = {number for number, _ in old_sides}
    for _ in range(25):
        senses = {number: rng.random() < 0.5 for number in numbers}
        assert evaluate(old, senses) == evaluate(new, senses)


def test_model_region_logic():
    """The geometry of every cell must be the same set logic as the OpenMC region."""
    problem = get_problem()
    geometry = ET.parse(MODEL).getroot().find("geometry")
    rng = random.Random(2)

    n_checked = 0
    for elem in geometry.findall("cell"):
        region = elem.get("region")
        if not region:
            continue
        cell = problem.cells[int(elem.get("id"))]
        numbers = {abs(int(n)) for n in re.findall(r"-?\d+", region)}
        assert {s.number for s in cell.surfaces} == numbers
        expected = compile(OpenMCModel._to_python(region), "region", "eval")
        for _ in range(50):
            senses = {n: rng.random() < 0.5 for n in numbers}
            sense = lambda n: 1 if senses[n] else -1
            assert evaluate(cell.geometry, senses) == eval(expected, {"s": sense})
        n_checked += 1
    assert n_checked == 214


def test_model_same_material_everywhere():
    """Walks down the universes at random points, in the XML and in the MCNP problem."""
    found = compare_at_random_points(MODEL, get_problem(), 3000, [160.0, 45.0, 9.0])
    # all of the materials but the detector's helium (which is tiny) should be hit
    assert found >= {1, 2, 3, 4, 7, 8, "outside"}


def test_model_sample_and_detector():
    problem = get_problem()
    model = MontePyModel(problem)
    openmc_model = OpenMCModel(MODEL)
    for point, material in [
        ([0.0, -25.0, 0.0], 6),  # the HEU sample
        ([0.0, -27.94, 4.0], 5),  # the He-3 detector, in the front cassette
        ([0.0, 27.94, 0.0], 1),  # air in the empty cassette at the back
        ([0.0, 0.0, 0.0], 7),  # polyethylene in the middle cassette
        ([-5.334, 0.0, -5.334], 8),  # a uranium pin
        ([0.0, 0.0, -90.0], 4),  # the concrete floor
        ([0.0, 0.0, 200.0], "outside"),
    ]:
        assert model.find(point) == material
        assert openmc_model.find(point) == material


def check_file_format(path):
    """A file that MCNP can read has: a title, and 3 blocks split by one blank line."""
    with open(path) as fh:
        lines = fh.read().split("\n")
    assert all(len(line) <= 128 for line in lines)
    assert all(ord(char) < 128 and char != "\t" for line in lines for char in line)
    # the file ends with a new line
    assert lines[-1] == ""
    lines = lines[:-1]
    # one blank line after the cells, and one after the surfaces
    assert len([line for line in lines if not line.strip()]) == 2
    return lines


def test_model_write(tmp_path):
    problem = get_problem()
    out_file = os.path.join(str(tmp_path), "model.imcnp")
    with warnings.catch_warnings():
        # nothing should need to be wrapped, or expanded
        warnings.simplefilter("error")
        problem.write_problem(out_file)
    lines = check_file_format(out_file)
    assert "288 6 -18.74 -605 603 -604 imp:n=1.0 U=93 " in lines
    assert "1 1 -0.001205 50 -51 52 -53 54 -56 imp:n=1.0 U=1 " in lines
    assert "2 PY -12.600000000000001 " in lines
    assert "144 C/Y 0.0 4.0 1.6 " in lines
    assert "M6 92234      -0.0102" in lines
    # read it back: just-in-time parsing
    new_problem = montepy.read_input(out_file)
    for collection in ("cells", "surfaces", "materials"):
        old_numbers = [obj.number for obj in getattr(problem, collection)]
        new_numbers = [obj.number for obj in getattr(new_problem, collection)]
        assert old_numbers == new_numbers
    for old, new in zip(problem.surfaces, new_problem.surfaces):
        assert type(old) == type(new)


def test_model_round_trip(tmp_path):
    """Fully parses the file that was written, and compares everything."""
    problem = get_problem()
    out_file = os.path.join(str(tmp_path), "model.imcnp")
    problem.write_problem(out_file)
    new_problem = montepy.read_input(out_file, jit_parse=False)
    assert len(new_problem.cells) == len(problem.cells)
    rng = random.Random(3)
    for old, new in zip(problem.surfaces, new_problem.surfaces):
        assert old == new
    for old, new in zip(problem.materials, new_problem.materials):
        assert old == new
        assert old.is_atom_fraction == new.is_atom_fraction
    for old, new in zip(problem.cells, new_problem.cells):
        assert old.number == new.number
        assert_same_geometry(old.geometry, new.geometry, rng)
        assert old.importance.neutron == new.importance.neutron
        assert old.universe.number == new.universe.number
        if old.material is None:
            assert new.material is None
        else:
            assert old.material.number == new.material.number
            assert old.mass_density == new.mass_density
        if old.fill.universe is None:
            assert new.fill.universe is None
        else:
            assert old.fill.universe.number == new.fill.universe.number
        if old.fill.transform is None:
            assert new.fill.transform is None
        else:
            assert old.fill.transform.equivalent(new.fill.transform, 1e-12)
    # and the geometry is still the same as in OpenMC
    compare_at_random_points(MODEL, new_problem, 500, [160.0, 45.0])
    # writing it again changes nothing, but for the spaces at the end of a line
    second_file = os.path.join(str(tmp_path), "model2.imcnp")
    new_problem.write_problem(second_file)
    with open(out_file) as first, open(second_file) as second:
        first_lines = [line.rstrip() for line in first]
        second_lines = [line.rstrip() for line in second]
    assert first_lines == second_lines


def test_model_can_be_changed(tmp_path):
    """The objects need to behave like the ones that are read from an MCNP file."""
    problem = montepy.from_model_xml(MODEL)
    problem.surfaces[50].location = -7.5
    cell = problem.cells[288]
    cell.mass_density = 19.1
    cell.geometry &= +problem.surfaces[1]
    problem.cells[4].universe = problem.universes[91]
    problem.cells[140].fill.transform.displacement_vector[0] = 1.5
    problem.materials[6].add_nuclide("U-236", 0.001)
    problem.materials.default_libraries["nlib"] = "80c"
    assert "50 PX -7.5" in problem.surfaces[50].mcnp_str()
    assert "288 6 -19.1" in cell.mcnp_str()
    assert "-605 603 -604 1 imp" in cell.mcnp_str()
    assert "U=91" in problem.cells[4].mcnp_str()
    assert "1.5" in problem.cells[140].mcnp_str()
    assert "92236" in problem.materials[6].mcnp_str()
    clone = problem.clone()
    assert len(clone.cells) == 290
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", montepy.exceptions.LineExpansionWarning)
        problem.write_problem(os.path.join(str(tmp_path), "changed.imcnp"))


# ----------------------------------------------------------------------------
# Regions
# ----------------------------------------------------------------------------


@pytest.mark.parametrize(
    "region, answer",
    [
        ("1", ("surf", 1, True)),
        ("-12", ("surf", 12, False)),
        ("+3", ("surf", 3, True)),
        ("1 -2", ("and", [("surf", 1, True), ("surf", 2, False)])),
        ("1 | -2", ("or", [("surf", 1, True), ("surf", 2, False)])),
        ("1|-2", ("or", [("surf", 1, True), ("surf", 2, False)])),
        # intersection is done before union
        (
            "1 -2 | 3",
            (
                "or",
                [("and", [("surf", 1, True), ("surf", 2, False)]), ("surf", 3, True)],
            ),
        ),
        (
            "1 (-2 | 3)",
            (
                "and",
                [("surf", 1, True), ("or", [("surf", 2, False), ("surf", 3, True)])],
            ),
        ),
        ("((1))", ("surf", 1, True)),
        # De Morgan's laws
        ("~1", ("surf", 1, False)),
        ("~~1", ("surf", 1, True)),
        ("~(1 -2)", ("or", [("surf", 1, False), ("surf", 2, True)])),
        ("~(1 | -2)", ("and", [("surf", 1, False), ("surf", 2, True)])),
        # complement is done before intersection
        ("~1 2", ("and", [("surf", 1, False), ("surf", 2, True)])),
        (
            "~(1 (2 | -3)) 4",
            (
                "and",
                [
                    (
                        "or",
                        [
                            ("surf", 1, False),
                            ("and", [("surf", 2, False), ("surf", 3, True)]),
                        ],
                    ),
                    ("surf", 4, True),
                ],
            ),
        ),
    ],
)
def test_parse_region(region, answer):
    assert openmc_reader._parse_region(region) == answer


@pytest.mark.parametrize(
    "region", ["1 & 2", "(1 2", "1 2)", "1 |", "| 1", "()", "~", "0", "1.5", "a"]
)
def test_parse_region_errors(region):
    with pytest.raises(ValueError):
        openmc_reader._parse_region(region)


def test_complement_region(tmp_path):
    geometry = """
    <cell id="1" material="1" region="~(1 | -2) 3" universe="0"/>
    <cell id="2" material="void" region="~3" universe="0"/>
    <surface id="1" type="x-plane" coeffs="1"/>
    <surface id="2" type="x-plane" coeffs="-1"/>
    <surface id="3" type="z-cylinder" coeffs="0 0 5"/>
    """
    problem = montepy.from_model_xml(write_model(tmp_path, geometry, WATER))
    assert "1 1 -1.0 -1 2 3 imp" in problem.cells[1].mcnp_str()
    assert "2 0 -3 imp" in problem.cells[2].mcnp_str()
    # the outside is: not (-1 2 3) and not (-3)
    assert "3 0 (1 : -2 : -3) 3 imp:n=0.0" in problem.cells[3].mcnp_str()


def test_long_region_is_wrapped(tmp_path):
    n_planes = 400
    surfaces = "".join(
        f'<surface id="{i}" type="x-plane" coeffs="{i}"/>'
        for i in range(1, n_planes + 1)
    )
    region = " ".join(f"({i} | -{i + 1})" for i in range(1, n_planes, 2))
    union = " | ".join(str(-i) for i in range(1, n_planes + 1))
    geometry = f"""
    <cell id="1" material="1" region="{region}" universe="0"/>
    <cell id="2" material="1" region="{union}" universe="0"/>
    {surfaces}
    """
    path = write_model(tmp_path, geometry, WATER)
    problem = montepy.from_model_xml(path)
    for cell in problem.cells:
        lines = [l for l in cell.mcnp_str().split("\n") if not l.startswith("c ")]
        assert len(lines) > 10
        assert all(len(line) <= openmc_reader._GEOMETRY_WIDTH for line in lines)
        assert all(line.startswith(" " * 5) for line in lines[1:])
    assert len(problem.cells[1].surfaces) == n_planes
    out_file = os.path.join(str(tmp_path), "out.imcnp")
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        problem.write_problem(out_file)
    check_file_format(out_file)


def test_parameters_after_long_region(tmp_path):
    """The parameters go on a new line when they do not fit after the geometry."""
    surfaces = "".join(
        f'<surface id="{i}" type="x-plane" coeffs="{i}"/>' for i in range(100, 124)
    )
    # 74 characters in MCNP: this fits on a line, but not with the parameters
    region = " ".join(f"-{i}" for i in range(100, 114))
    geometry = f"""
    <cell id="1" fill="5" region="{region}"/>
    <cell id="2" material="1" universe="5"/>
    {surfaces}
    """
    path = write_model(tmp_path, geometry, WATER)
    problem = montepy.from_model_xml(path, graveyard=False)
    lines = problem.cells[1].mcnp_str().split("\n")
    assert lines == ["1 0 " + region, "     imp:n=1.0 FILL=5 "]
    out_file = os.path.join(str(tmp_path), "out.imcnp")
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        problem.write_problem(out_file)
    with open(out_file) as fh:
        assert all(len(line.rstrip("\n")) <= 80 for line in fh)


# ----------------------------------------------------------------------------
# Surfaces
# ----------------------------------------------------------------------------


@pytest.mark.parametrize(
    "openmc_type, coeffs, mcnp_type, constants",
    [
        ("x-plane", "1.5", "PX", [1.5]),
        ("y-plane", "-1.5", "PY", [-1.5]),
        ("z-plane", "0", "PZ", [0.0]),
        ("plane", "1 2 3 4", "P", [1.0, 2.0, 3.0, 4.0]),
        ("x-cylinder", "1 2 3", "C/X", [1.0, 2.0, 3.0]),
        ("y-cylinder", "1 0 3", "C/Y", [1.0, 0.0, 3.0]),
        ("z-cylinder", "0 2 3", "C/Z", [0.0, 2.0, 3.0]),
        ("x-cylinder", "0 0 3", "CX", [3.0]),
        ("y-cylinder", "0.0 0.0 3", "CY", [3.0]),
        ("z-cylinder", "0 0 3", "CZ", [3.0]),
        ("sphere", "1 2 3 4", "S", [1.0, 2.0, 3.0, 4.0]),
        ("sphere", "0 0 3 4", "S", [0.0, 0.0, 3.0, 4.0]),
        ("sphere", "0 0 0 4", "SO", [4.0]),
        ("x-cone", "1 2 3 0.5", "K/X", [1.0, 2.0, 3.0, 0.5]),
        ("y-cone", "1 2 3 0.5", "K/Y", [1.0, 2.0, 3.0, 0.5]),
        ("z-cone", "1 2 3 0.5", "K/Z", [1.0, 2.0, 3.0, 0.5]),
        ("x-cone", "1 0 0 0.5", "KX", [1.0, 0.5]),
        ("y-cone", "0 2 0 0.5", "KY", [2.0, 0.5]),
        ("z-cone", "0 0 3 0.5", "KZ", [3.0, 0.5]),
        ("quadric", "1 2 3 4 5 6 7 8 9 10", "GQ", [float(i) for i in range(1, 11)]),
        ("x-torus", "1 2 3 4 5 6", "TX", [1.0, 2.0, 3.0, 4.0, 5.0, 6.0]),
        ("y-torus", "1 2 3 4 5 6", "TY", [1.0, 2.0, 3.0, 4.0, 5.0, 6.0]),
        ("z-torus", "1 2 3 4 5 6", "TZ", [1.0, 2.0, 3.0, 4.0, 5.0, 6.0]),
    ],
)
def test_surface_types(tmp_path, openmc_type, coeffs, mcnp_type, constants):
    geometry = f"""
    <cell id="1" material="1" region="-7" universe="0"/>
    <surface id="7" name="my surface" type="{openmc_type}" coeffs="{coeffs}"/>
    """
    problem = montepy.from_model_xml(write_model(tmp_path, geometry, WATER))
    surface = problem.surfaces[7]
    assert surface.surface_type == montepy.SurfaceType(mcnp_type)
    assert surface.surface_constants == constants
    assert type(surface) is not montepy.Surface
    assert "my surface" in surface.leading_comments
    surface.validate()
    text = " ".join(f"{c!r}" for c in constants)
    assert surface.mcnp_str().split("\n")[-1].strip() == f"7 {mcnp_type} {text}"


def test_surface_errors(tmp_path):
    geometry = SPHERE_WORLD.replace('type="sphere"', 'type="hyperboloid"')
    with pytest.raises(UnsupportedFeature):
        montepy.from_model_xml(write_model(tmp_path, geometry, WATER))
    geometry = SPHERE_WORLD.replace('coeffs="0 0 0 10"', 'coeffs="0 0 10"')
    with pytest.raises(ValueError):
        montepy.from_model_xml(write_model(tmp_path, geometry, WATER))
    geometry = SPHERE_WORLD.replace("vacuum", "sticky")
    with pytest.raises(ValueError):
        montepy.from_model_xml(write_model(tmp_path, geometry, WATER))
    geometry = SPHERE_WORLD.replace('region="-1"', 'region="-1 2"')
    with pytest.raises(ValueError):
        montepy.from_model_xml(write_model(tmp_path, geometry, WATER))


def test_boundary_conditions(tmp_path):
    geometry = """
    <cell id="1" material="1" region="1 -2 3 -4 5 -6" universe="0"/>
    <surface id="1" type="x-plane" boundary="reflective" coeffs="-1"/>
    <surface id="2" type="x-plane" boundary="white" coeffs="1"/>
    <surface id="3" type="y-plane" boundary="periodic" periodic_surface_id="4" coeffs="-1"/>
    <surface id="4" type="y-plane" boundary="periodic" periodic_surface_id="3" coeffs="1"/>
    <surface id="5" type="z-plane" boundary="transmission" coeffs="-1"/>
    <surface id="6" type="z-plane" boundary="vacuum" coeffs="1"/>
    """
    path = write_model(tmp_path, geometry, WATER)
    problem = montepy.from_model_xml(path)
    surfaces = problem.surfaces
    assert surfaces[1].is_reflecting and not surfaces[1].is_white_boundary
    assert surfaces[2].is_white_boundary and not surfaces[2].is_reflecting
    assert surfaces[3].periodic_surface is surfaces[4]
    assert surfaces[4].periodic_surface is surfaces[3]
    for number in (5, 6):
        assert not surfaces[number].is_reflecting
        assert not surfaces[number].is_white_boundary
        assert surfaces[number].periodic_surface is None
    assert surfaces[1].mcnp_str().strip() == "*1 PX -1.0"
    assert surfaces[2].mcnp_str().strip() == "+2 PX 1.0"
    assert surfaces[3].mcnp_str().strip() == "3 -4 PY -1.0"
    # OpenMC finds the other surface on its own
    with open(path) as fh:
        text = fh.read()
    with open(path, "w") as fh:
        fh.write(re.sub(r' periodic_surface_id="\d"', "", text))
    problem = montepy.from_model_xml(path)
    assert problem.surfaces[3].periodic_surface is problem.surfaces[4]
    assert problem.surfaces[4].periodic_surface is problem.surfaces[3]


def test_periodic_surface_not_found(tmp_path):
    geometry = """
    <cell id="1" material="1" region="1 -2" universe="0"/>
    <surface id="1" type="x-plane" boundary="periodic" coeffs="-1"/>
    <surface id="2" type="y-plane" boundary="periodic" coeffs="1"/>
    """
    with pytest.warns(UserWarning, match="periodic"):
        problem = montepy.from_model_xml(write_model(tmp_path, geometry, WATER))
    assert problem.surfaces[1].periodic_surface is None
    geometry = geometry.replace('coeffs="-1"', 'coeffs="-1" periodic_surface_id="9"')
    with pytest.raises(ValueError):
        montepy.from_model_xml(write_model(tmp_path, geometry, WATER))


# ----------------------------------------------------------------------------
# Materials
# ----------------------------------------------------------------------------


@pytest.mark.parametrize(
    "density, is_atom, answer",
    [
        ('<density value="2.5" units="g/cm3"/>', False, 2.5),
        ('<density value="2.5" units="g/cc"/>', False, 2.5),
        ('<density value="1.205" units="kg/m3"/>', False, 0.001205),
        ('<density value="0.1" units="atom/b-cm"/>', True, 0.1),
        ('<density value="6.6e22" units="atom/cm3"/>', True, 0.066),
        ('<density units="sum"/>', True, 3.0),
    ],
)
def test_density_units(tmp_path, density, is_atom, answer):
    materials = f"""
    <material id="3">{density}
      <nuclide name="H1" ao="2.0"/><nuclide name="O16" ao="1.0"/>
    </material>"""
    geometry = SPHERE_WORLD.replace('material="1"', 'material="3"')
    problem = montepy.from_model_xml(write_model(tmp_path, geometry, materials))
    cell = problem.cells[1]
    assert cell.material is problem.materials[3]
    assert cell.is_atom_dens == is_atom
    if is_atom:
        assert cell.atom_density == answer
        assert f"1 3 {answer!r} -1 " in cell.mcnp_str()
    else:
        assert cell.mass_density == answer
        assert f"1 3 -{answer!r} -1 " in cell.mcnp_str()
    assert len(problem.cells[1].leading_comments) == 0
    assert len(problem.materials[3].leading_comments) == 0


def test_cell_density(tmp_path):
    geometry = SPHERE_WORLD.replace('material="1"', 'material="1" density="0.7"')
    problem = montepy.from_model_xml(write_model(tmp_path, geometry, WATER))
    assert problem.cells[1].mass_density == 0.7


def test_nuclides(tmp_path):
    materials = """
    <material id="1" name="odd stuff" depletable="true">
      <density value="2.5" units="g/cm3"/>
      <nuclide name="Am242_m1" wo="0.25"/>
      <nuclide name="Am242" wo="0.25"/>
      <nuclide name="Ta180_m1" wo="1e-06"/>
      <nuclide name="C0" wo="0.25"/>
      <element name="Fe" wo="8e-05"/>
    </material>"""
    problem = montepy.from_model_xml(write_model(tmp_path, SPHERE_WORLD, materials))
    material = problem.materials[1]
    assert not material.is_atom_fraction
    nuclides = [nuclide for nuclide, _ in material]
    assert [(n.Z, n.A, n.meta_state) for n in nuclides] == [
        (95, 242, 1),
        (95, 242, 0),
        (73, 180, 1),
        (6, 0, 0),
        (26, 0, 0),
    ]
    assert [fraction for _, fraction in material] == [0.25, 0.25, 1e-06, 0.25, 8e-05]
    assert material.thermal_scattering is None
    lines = material.mcnp_str().split("\n")
    assert lines[0] == "c odd stuff"
    assert [line.split() for line in lines[1:]] == [
        ["M1", "95242", "-0.25"],
        ["95642", "-0.25"],
        ["73580", "-1e-06"],
        ["6000", "-0.25"],
        ["26000", "-8e-05"],
    ]


@pytest.mark.parametrize("library", ["80c", ".80c", montepy.Library("80c")])
def test_library(tmp_path, library):
    path = write_model(tmp_path, SPHERE_WORLD, WATER)
    problem = montepy.from_model_xml(path, library=library)
    material = problem.materials[1]
    assert all(nuclide.library == montepy.Library("80c") for nuclide, _ in material)
    lines = material.mcnp_str().split("\n")
    assert [line.split() for line in lines[1:]] == [
        ["M1", "1001.80c", "2.0"],
        ["8016.80c", "1.0"],
    ]
    # the default is to have no library
    problem = montepy.from_model_xml(path)
    assert all(str(nuclide.library) == "" for nuclide, _ in problem.materials[1])


def test_library_of_big_model():
    problem = montepy.from_model_xml(MODEL, library=".00c")
    for material in problem.materials:
        assert all(str(nuclide.library) == "00c" for nuclide, _ in material)
    assert "92235.00c" in problem.materials[6].mcnp_str()


@pytest.mark.parametrize("library", ["80", ".c", "..80c", "80c.", "u235.80c"])
def test_library_errors(tmp_path, library):
    path = write_model(tmp_path, SPHERE_WORLD, WATER)
    with pytest.raises(ValueError):
        montepy.from_model_xml(path, library=library)


def test_library_wrong_type(tmp_path):
    path = write_model(tmp_path, SPHERE_WORLD, WATER)
    with pytest.raises(TypeError):
        montepy.from_model_xml(path, library=80)
    with pytest.raises(TypeError):
        montepy.from_model_xml(path, sab_register=["lwtr.20t"])
    with pytest.raises(TypeError):
        montepy.from_model_xml(path, sab_register={"c_H_in_H2O": 20})


WATER_WITH_SAB = WATER.replace("</material>", '<sab name="c_H_in_H2O"/></material>')


def test_default_sab_register(tmp_path):
    path = write_model(tmp_path, SPHERE_WORLD, WATER_WITH_SAB)
    problem = montepy.from_model_xml(path)
    material = problem.materials[1]
    law = material.thermal_scattering
    assert law.thermal_scattering_laws == ["lwtr.20t"]
    assert law.parent_material is material
    assert law.mcnp_str().strip() == "MT1 lwtr.20t"
    # the MT input is written right after its material
    assert problem.data_inputs == [material, law]
    out_file = os.path.join(str(tmp_path), "out.imcnp")
    problem.write_problem(out_file)
    lines = [line.strip() for line in check_file_format(out_file)]
    assert lines[-1] == "MT1 lwtr.20t"
    assert lines[-2] == "8016       1.0"
    # a material with no table has no MT input
    problem = montepy.from_model_xml(write_model(tmp_path, SPHERE_WORLD, WATER))
    assert problem.materials[1].thermal_scattering is None
    assert len(problem.data_inputs) == 1


def test_default_sab_register_tables():
    register = openmc_reader.DEFAULT_SAB_REGISTER
    assert register["c_H_in_H2O"] == "lwtr.20t"
    assert register["c_Graphite"] == "grph.20t"
    # the first table is not always the one at room temperature
    assert register["c_Al27"] == "al27.22t"
    assert register["c_Zr_in_ZrH"] == "zr-h.30t"
    for name, law in register.items():
        assert name.startswith("c_")
        assert openmc_reader._THERMAL_LAW.fullmatch(law)
        # the names with a slash are going away
        assert "/" not in law
    # each MCNP table is only used once
    assert len(set(register.values())) == len(register)


def test_custom_sab_register(tmp_path):
    path = write_model(tmp_path, SPHERE_WORLD, WATER_WITH_SAB)
    register = {"c_H_in_H2O": "h-h2o.40t"}
    problem = montepy.from_model_xml(path, library="00c", sab_register=register)
    law = problem.materials[1].thermal_scattering
    assert law.thermal_scattering_laws == ["h-h2o.40t"]
    assert law.mcnp_str().strip() == "MT1 h-h2o.40t"
    assert "1001.00c" in problem.materials[1].mcnp_str()
    # the default register is not changed, and can be built on
    assert openmc_reader.DEFAULT_SAB_REGISTER["c_H_in_H2O"] == "lwtr.20t"
    register = openmc_reader.DEFAULT_SAB_REGISTER | {"c_H_in_H2O": "lwtr.26t"}
    problem = montepy.from_model_xml(path, sab_register=register)
    law = problem.materials[1].thermal_scattering
    assert law.thermal_scattering_laws == ["lwtr.26t"]


def test_sab_not_in_register(tmp_path):
    path = write_model(tmp_path, SPHERE_WORLD, WATER_WITH_SAB)
    # the register that is given replaces the default one
    with pytest.warns(UserWarning, match="c_H_in_H2O"):
        problem = montepy.from_model_xml(path, sab_register={})
    assert problem.materials[1].thermal_scattering is None
    assert len(problem.data_inputs) == 1
    materials = WATER.replace("</material>", '<sab name="c_Unobtainium"/></material>')
    with pytest.warns(UserWarning, match="c_Unobtainium"):
        problem = montepy.from_model_xml(write_model(tmp_path, SPHERE_WORLD, materials))
    assert problem.materials[1].thermal_scattering is None


def test_many_sab_tables(tmp_path):
    materials = """
    <material id="4" name="BeO">
      <density value="3.0" units="g/cm3"/>
      <nuclide name="Be9" ao="1.0"/>
      <nuclide name="O16" ao="1.0"/>
      <sab name="c_Be_in_BeO"/>
      <sab name="c_Unobtainium"/>
      <sab name="c_O_in_BeO" fraction="1.0"/>
    </material>""" + WATER_WITH_SAB
    geometry = SPHERE_WORLD.replace('material="1"', 'material="4"')
    geometry += '<cell id="2" material="1" region="1" universe="0"/>'
    with pytest.warns(UserWarning, match="c_Unobtainium"):
        problem = montepy.from_model_xml(write_model(tmp_path, geometry, materials))
    beo, water = problem.materials[4], problem.materials[1]
    assert beo.thermal_scattering.thermal_scattering_laws == ["be-o.20t", "o-be.20t"]
    assert beo.thermal_scattering.mcnp_str().strip() == "MT4 be-o.20t o-be.20t"
    assert water.thermal_scattering.mcnp_str().strip() == "MT1 lwtr.20t"
    assert problem.data_inputs == [
        beo,
        beo.thermal_scattering,
        water,
        water.thermal_scattering,
    ]


def test_sab_fraction(tmp_path):
    materials = WATER.replace(
        "</material>", '<sab name="c_H_in_H2O" fraction="0.5"/></material>'
    )
    with pytest.warns(UserWarning, match="fraction"):
        problem = montepy.from_model_xml(write_model(tmp_path, SPHERE_WORLD, materials))
    assert problem.materials[1].thermal_scattering.thermal_scattering_laws == [
        "lwtr.20t"
    ]


@pytest.mark.parametrize("law", ["lwtr", "lwtr.20", ".20t", "20t", "lwtr 20t", ""])
def test_sab_register_errors(tmp_path, law):
    path = write_model(tmp_path, SPHERE_WORLD, WATER)
    with pytest.raises(ValueError, match="thermal scattering"):
        montepy.from_model_xml(path, sab_register={"c_H_in_H2O": law})


def test_material_errors(tmp_path):
    def convert(materials, geometry=SPHERE_WORLD):
        return montepy.from_model_xml(write_model(tmp_path, geometry, materials))

    with pytest.raises(ValueError, match="mixes"):
        convert(WATER.replace('name="O16" ao', 'name="O16" wo'))
    with pytest.raises(ValueError, match="no nuclides"):
        convert('<material id="1"><density value="1" units="g/cm3"/></material>')
    with pytest.raises(ValueError, match="density"):
        convert(WATER.replace('<density value="1.0" units="g/cm3"/>', ""))
    with pytest.raises(ValueError, match="units"):
        convert(WATER.replace("g/cm3", "lb/ft3"))
    with pytest.raises(ValueError, match="sum"):
        convert(
            '<material id="1"><density units="sum"/><nuclide name="H1" wo="1.0"/></material>'
        )
    with pytest.raises(ValueError, match="nuclide name"):
        convert(WATER.replace("O16", "Oxygen-16"))
    with pytest.raises(ValueError, match="fraction"):
        convert(WATER.replace(' ao="1.0"', ""))
    with pytest.raises(UnsupportedFeature):
        convert(
            '<material id="1"><density units="macro" value="1.0"/><macroscopic name="UO2"/></material>'
        )
    with pytest.raises(ValueError, match="does not exist"):
        convert(WATER.replace('id="1"', 'id="2"'))
    with pytest.raises(UnsupportedFeature):
        convert(WATER, SPHERE_WORLD.replace('material="1"', 'material="1 1 1"'))
    with pytest.raises(ValueError, match="no material"):
        convert(WATER, SPHERE_WORLD.replace(' material="1"', ""))


def test_no_materials(tmp_path):
    path = os.path.join(str(tmp_path), "model.xml")
    geometry = SPHERE_WORLD.replace('material="1"', 'material="void"')
    with open(path, "w") as fh:
        fh.write(f"<model><geometry>{geometry}</geometry></model>")
    problem = montepy.from_model_xml(path)
    assert len(problem.materials) == 0
    assert problem.cells[1].material is None
    assert "1 0 -1 imp:n=1.0" in problem.cells[1].mcnp_str()


def test_sub_elements(tmp_path):
    """OpenMC accepts sub-elements in the place of attributes."""
    geometry = """
    <cell><id>4</id><name>ball</name><material>1</material><region>-1</region></cell>
    <surface><id>1</id><type>sphere</type><coeffs>0 0 0 10</coeffs>
      <boundary>reflective</boundary></surface>
    """
    problem = montepy.from_model_xml(write_model(tmp_path, geometry, WATER))
    assert problem.cells[4].material.number == 1
    assert "ball" in problem.cells[4].leading_comments
    assert problem.surfaces[1].is_reflecting
    assert problem.surfaces[1].radius == 10.0


# ----------------------------------------------------------------------------
# Universes
# ----------------------------------------------------------------------------

NESTED = """
<cell id="1" fill="5" region="-1" universe="{root}" {transform}/>
<cell id="2" material="1" region="-2" universe="5"/>
<cell id="3" material="void" region="2" universe="5"/>
<surface id="1" type="sphere" boundary="vacuum" coeffs="0 0 0 10"/>
<surface id="2" type="x-plane" coeffs="0"/>
"""


@pytest.mark.parametrize("root", [0, 7])
def test_root_universe(tmp_path, root):
    geometry = NESTED.format(root=root, transform="")
    problem = montepy.from_model_xml(write_model(tmp_path, geometry, WATER))
    assert sorted(u.number for u in problem.universes) == [0, 5]
    assert problem.cells[1].universe.number == 0
    assert problem.cells[1].fill.universe is problem.universes[5]
    assert problem.cells[1].fill.transform is None
    assert problem.cells[2].universe is problem.universes[5]
    assert "U=" not in problem.cells[1].mcnp_str()
    assert "U=5" in problem.cells[2].mcnp_str()
    assert "4 0 1 imp:n=0.0" in problem.cells[4].mcnp_str()


def test_universe_0_is_not_the_root(tmp_path):
    geometry = NESTED.format(root=7, transform="").replace('"5"', '"0"')
    with pytest.warns(UserWarning, match="renumbered to 8"):
        problem = montepy.from_model_xml(write_model(tmp_path, geometry, WATER))
    assert sorted(u.number for u in problem.universes) == [0, 8]
    assert problem.cells[1].universe.number == 0
    assert problem.cells[1].fill.universe.number == 8
    assert problem.cells[2].universe.number == 8


def test_universe_errors(tmp_path):
    # two root universes
    geometry = SPHERE_WORLD + '<cell id="2" material="1" region="1" universe="3"/>'
    with pytest.raises(ValueError, match="root"):
        montepy.from_model_xml(write_model(tmp_path, geometry, WATER))
    # a universe that does not exist
    geometry = SPHERE_WORLD.replace('material="1"', 'fill="4"')
    with pytest.raises(ValueError, match="no cells"):
        montepy.from_model_xml(write_model(tmp_path, geometry, WATER))
    # a loop of universes
    geometry = NESTED.format(root=5, transform="")
    with pytest.raises(ValueError, match="root"):
        montepy.from_model_xml(write_model(tmp_path, geometry, WATER))


def test_no_graveyard_needed(tmp_path):
    """Nothing is outside of a root universe that is all of space."""
    geometry = """
    <cell id="1" fill="5"/>
    <cell id="2" material="1" universe="5"/>
    """
    problem = montepy.from_model_xml(write_model(tmp_path, geometry, WATER))
    assert [c.number for c in problem.cells] == [1, 2]
    assert [s.number for s in problem.surfaces] == [1]
    assert problem.cells[1].universe.number == 0
    assert str(problem.cells[1].geometry) == "(+1:-1)"
    assert str(problem.cells[2].geometry) == "(+1:-1)"
    assert isinstance(problem.surfaces[1], montepy.ZPlane)
    assert "2 1 -1.0 1 : -1 imp:n=1.0 U=5" in problem.cells[2].mcnp_str()
    # every point is in the cell, even the ones on the plane
    model = MontePyModel(problem)
    for z in (-1e20, -1.0, 0.0, 1.0, 1e20):
        assert model.find([1e20, -1e20, z]) == 1


def test_translation(tmp_path):
    geometry = NESTED.format(root=0, transform='translation="1.5 -2.0 1e-3"')
    path = write_model(tmp_path, geometry, WATER)
    problem = montepy.from_model_xml(path)
    transform = problem.cells[1].fill.transform
    assert transform.hidden_transform
    assert transform.is_main_to_aux
    assert not transform.is_in_degrees
    assert list(transform.displacement_vector) == [1.5, -2.0, 0.001]
    assert "FILL=5 (1.5 -2.0 0.001 )" in problem.cells[1].mcnp_str()
    assert len(problem.transforms) == 0
    found = compare_at_random_points(path, problem, 500, [12.0])
    assert found == {1, None, "outside"}


@pytest.mark.parametrize(
    "rotation, matrix",
    [
        # OpenMC: the universe is turned by +90 degrees about z, so its x axis is the cell's y axis.
        ("0 0 90", [[0, 1, 0], [-1, 0, 0], [0, 0, 1]]),
        ("90 0 0", [[1, 0, 0], [0, 0, 1], [0, -1, 0]]),
        ("0 90 0", [[0, 0, -1], [0, 1, 0], [1, 0, 0]]),
        ("0 0 0", [[1, 0, 0], [0, 1, 0], [0, 0, 1]]),
        ("0 1 0 -1 0 0 0 0 1", [[0, 1, 0], [-1, 0, 0], [0, 0, 1]]),
    ],
)
def test_rotation(tmp_path, rotation, matrix):
    geometry = NESTED.format(root=0, transform=f'rotation="{rotation}"')
    problem = montepy.from_model_xml(write_model(tmp_path, geometry, WATER))
    transform = problem.cells[1].fill.transform
    assert list(transform.displacement_vector) == [0.0, 0.0, 0.0]
    assert transform.rotation_matrix.reshape((3, 3)).tolist() == matrix
    assert not transform.is_in_degrees
    text = " ".join(str(float(x)) for row in matrix for x in row)
    assert f"FILL=5 (0.0 0.0 0.0 {text} )" in problem.cells[1].mcnp_str()


def test_rotation_matrix_is_openmc_convention():
    """OpenMC turns the universe about x, then y, then z: so the inverse takes a point into the universe."""

    def turn(axis, angle):
        cos, sin = math.cos(math.radians(angle)), math.sin(math.radians(angle))
        i, j = [(1, 2), (2, 0), (0, 1)][axis]
        matrix = np.eye(3)
        matrix[i, i] = matrix[j, j] = cos
        matrix[i, j], matrix[j, i] = -sin, sin
        return matrix

    phi, theta, psi = 10.0, 20.0, 30.0
    matrix = openmc_reader._rotation_matrix([phi, theta, psi])
    # This is what OpenMC does: the formula from its documentation, with the opposite angles.
    answer = turn(2, -psi) @ turn(1, -theta) @ turn(0, -phi)
    np.testing.assert_allclose(matrix, answer, atol=1e-14)
    np.testing.assert_allclose(matrix @ matrix.T, np.eye(3), atol=1e-14)
    with pytest.raises(ValueError):
        openmc_reader._rotation_matrix([1.0, 2.0])


def test_translation_and_rotation(tmp_path):
    transform = 'translation="1 2 3" rotation="0 0 90"'
    geometry = NESTED.format(root=0, transform=transform)
    problem = montepy.from_model_xml(write_model(tmp_path, geometry, WATER))
    assert (
        "FILL=5 (1.0 2.0 3.0 0.0 1.0 0.0 -1.0 0.0 0.0 0.0 0.0 1.0 )"
        in problem.cells[1].mcnp_str()
    )
    geometry = NESTED.format(root=0, transform='translation="1 2"')
    with pytest.raises(ValueError):
        montepy.from_model_xml(write_model(tmp_path, geometry, WATER))


# ----------------------------------------------------------------------------
# Lattices
# ----------------------------------------------------------------------------

PINS = """
<cell id="1" fill="9" region="1 -2 3 -4 5 -6" universe="0" {transform}/>
<cell id="11" material="1" region="-10 -12" universe="1"/>
<cell id="12" material="void" region="10 | 12" universe="1"/>
<cell id="21" material="2" region="-10" universe="2"/>
<cell id="22" material="1" region="10" universe="2"/>
<surface id="1" type="x-plane" boundary="vacuum" coeffs="-10"/>
<surface id="2" type="x-plane" boundary="vacuum" coeffs="10"/>
<surface id="3" type="y-plane" boundary="vacuum" coeffs="-10"/>
<surface id="4" type="y-plane" boundary="vacuum" coeffs="10"/>
<surface id="5" type="z-plane" boundary="vacuum" coeffs="-10"/>
<surface id="6" type="z-plane" boundary="vacuum" coeffs="10"/>
<surface id="10" type="z-cylinder" coeffs="0.1 0.05 0.3"/>
<surface id="11" type="x-plane" coeffs="0.1"/>
<surface id="12" type="z-plane" coeffs="0.3"/>
"""

# a universe that is not the same everywhere, to be used as an outer universe
UNIVERSE_3 = """
<cell id="31" material="2" region="-11" universe="3"/>
<cell id="32" material="void" region="11" universe="3"/>
"""

TWO_MATERIALS = WATER + """
<material id="2" name="iron">
  <density value="7.8" units="g/cm3"/>
  <nuclide name="Fe56" ao="1.0"/>
</material>
"""

LATTICE_2D = """
<lattice id="9" name="pins" {outer}>
  <pitch>1.5 1.0</pitch>
  <dimension>3 2</dimension>
  <lower_left>-2.0 -0.5</lower_left>
  <universes>
    1 2 2
    2 1 1 </universes>
</lattice>
"""

LATTICE_3D = """
<lattice id="9" {outer}>
  <pitch>1.5 1.0 2.0</pitch>
  <dimension>2 3 2</dimension>
  <lower_left>-2.0 -0.5 -1.0</lower_left>
  <universes>
    1 2
    2 2
    1 1

    2 1
    1 2
    2 2 </universes>
</lattice>
"""


def test_lattice_2d(tmp_path):
    geometry = PINS.format(transform="") + LATTICE_2D.format(outer="")
    path = write_model(tmp_path, geometry, TWO_MATERIALS)
    problem = montepy.from_model_xml(path)
    assert [c.number for c in problem.cells] == [1, 11, 12, 21, 22, 23, 24, 25]
    lattice, window, outside = (problem.cells[n] for n in (23, 24, 25))
    assert "pins" in lattice.leading_comments
    assert lattice.lattice_type == montepy.LatticeType.RECTANGULAR
    assert lattice.material is None
    # a new universe for the lattice itself
    assert lattice.universe.number == 10
    # x is the first index, and OpenMC lists the top row first
    numbers = np.vectorize(lambda u: u.number)(lattice.fill.universes)
    assert numbers.shape == (3, 2, 1)
    assert numbers[:, :, 0].tolist() == [[2, 1], [1, 2], [1, 2]]
    assert list(lattice.fill.min_index) == [0, 0, 0]
    assert list(lattice.fill.max_index) == [2, 1, 0]
    # element [0, 0, 0] is centered on the origin, and is infinite in z
    assert [
        (u.divider.surface_type.value, u.divider.location, u.side)
        for u in lattice.geometry
    ] == [
        ("PX", 0.75, False),
        ("PX", -0.75, True),
        ("PY", 0.5, False),
        ("PY", -0.5, True),
    ]
    assert "LAT=1 FILL=0:2 0:1 0:0 2 1 1 1 2 2" in lattice.mcnp_str()
    # universe 9 is what the cells that are filled with the lattice see
    assert problem.cells[1].fill.universe.number == 9
    assert window.universe.number == 9
    assert window.fill.universe is lattice.universe
    assert window.lattice_type is None
    # the center of the lower left element
    assert list(window.fill.transform.displacement_vector) == [-1.25, 0.0, 0.0]
    assert "24 0 17 : -17 imp:n=1.0 U=9 FILL=10 (-1.25 0.0 0.0 )" in window.mcnp_str()
    assert sorted(u.number for u in problem.universes) == [0, 1, 2, 9, 10]
    assert outside.importance.neutron == 0.0
    found = compare_at_random_points(path, problem, 2000, [3.0, 11.0])
    # there is nothing around a lattice with no outer universe
    assert found == {1, 2, None, "outside", "undefined"}


def test_lattice_3d(tmp_path):
    geometry = PINS.format(transform='translation="0.5 -0.25 1.0"')
    geometry += LATTICE_3D.format(outer="")
    path = write_model(tmp_path, geometry, TWO_MATERIALS)
    problem = montepy.from_model_xml(path)
    lattice, window = problem.cells[23], problem.cells[24]
    numbers = np.vectorize(lambda u: u.number)(lattice.fill.universes)
    assert numbers.shape == (2, 3, 2)
    # [x][y][z]
    assert numbers[:, :, 0].tolist() == [[1, 2, 1], [1, 2, 2]]
    assert numbers[:, :, 1].tolist() == [[2, 1, 2], [2, 2, 1]]
    assert len(lattice.geometry) == 6
    # this does not fit on one line of 80 characters: there is one row (along x) per line
    rows = ["1 1", "2 2", "1 2", "2 2", "1 2", "2 1 "]
    answer = "\n".join(["LAT=1 FILL=0:1 0:2 0:1"] + [" " * 5 + row for row in rows])
    assert lattice.mcnp_str().endswith(answer)
    assert list(window.fill.transform.displacement_vector) == [-1.25, 0.0, 0.0]
    assert list(problem.cells[1].fill.transform.displacement_vector) == [
        0.5,
        -0.25,
        1.0,
    ]
    found = compare_at_random_points(path, problem, 3000, [3.0, 11.0])
    # there is nothing around a lattice with no outer universe
    assert found == {1, 2, None, "outside", "undefined"}


def test_big_lattice_is_wrapped(tmp_path):
    """The universes of a big lattice are written with one row per line, and no line is too long."""
    nx, ny = 40, 3
    rows = [[1 + (i + j) % 2 for i in range(nx)] for j in range(ny)]
    text = "\n".join(" ".join(map(str, row)) for row in rows)
    geometry = PINS.format(transform="") + f"""
    <lattice id="9">
      <pitch>0.5 1.0</pitch>
      <dimension>{nx} {ny}</dimension>
      <lower_left>-10.0 -1.5</lower_left>
      <universes>{text}</universes>
    </lattice>"""
    path = write_model(tmp_path, geometry, TWO_MATERIALS)
    problem = montepy.from_model_xml(path)
    lattice = problem.cells[23]
    lines = lattice.mcnp_str().split("\n")
    assert all(len(line) <= 80 for line in lines)
    assert lines[1].endswith("LAT=1 FILL=0:39 0:2 0:0")
    # a row is too long for one line, so it is on two lines. MCNP's first row is OpenMC's last one.
    values = " ".join(lines[2:4]).split()
    assert [int(value) for value in values] == rows[-1]
    assert len(lines[2]) > 70
    assert len(lines) == 2 + 2 * ny
    out_file = os.path.join(str(tmp_path), "out.imcnp")
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        problem.write_problem(out_file)
    check_file_format(out_file)
    with open(out_file) as fh:
        assert all(len(line.rstrip("\n")) <= 80 for line in fh)
    compare_at_random_points(path, problem, 1000, [3.0, 11.0])


def test_two_digit_material_is_not_an_expansion(tmp_path):
    """A material number that is longer than the 0 of a void cell is not reported as an expansion."""
    materials = WATER.replace('id="1"', 'id="14"')
    geometry = SPHERE_WORLD.replace('material="1"', 'material="14"')
    problem = montepy.from_model_xml(write_model(tmp_path, geometry, materials))
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        problem.write_problem(os.path.join(str(tmp_path), "out.imcnp"))
    assert "1 14 -1.0 -1 imp:n=1.0" in problem.cells[1].mcnp_str()


def test_sab_order_with_many_materials(tmp_path):
    """Every MT input is right after its material, even when more materials come after it."""
    materials = ""
    for number in range(1, 6):
        material = WATER_WITH_SAB if number in {2, 4} else WATER
        materials += material.replace('id="1"', f'id="{number}"')
    problem = montepy.from_model_xml(write_model(tmp_path, SPHERE_WORLD, materials))
    answer = []
    for material in problem.materials:
        answer.append(material)
        if material.number in {2, 4}:
            answer.append(material.thermal_scattering)
    assert [m.number for m in problem.materials] == [1, 2, 3, 4, 5]
    assert problem.data_inputs == answer
    # a material that is added later goes after all of them
    new_material = montepy.Material(number=9)
    problem.materials.append(new_material)
    assert problem.data_inputs == answer + [new_material]


@pytest.mark.parametrize("lattice", [LATTICE_2D, LATTICE_3D])
@pytest.mark.parametrize("outer", [1, 3])
def test_lattice_outer(tmp_path, lattice, outer):
    geometry = PINS.format(transform='translation="0.5 -0.25 1.0"')
    geometry += lattice.format(outer=f'outer="{outer}"')
    if outer == 3:
        geometry += UNIVERSE_3
    path = write_model(tmp_path, geometry, TWO_MATERIALS)
    problem = montepy.from_model_xml(path)
    first = max(c.number for c in problem.cells) - 4
    lattice, outer_lattice, window, around, outside = (
        problem.cells[n] for n in range(first, first + 5)
    )
    n_dim = len(lattice.geometry) // 2
    assert lattice.fill.multiple_universes
    # the outer universe is repeated with the pitch of the lattice
    assert outer_lattice.lattice_type == montepy.LatticeType.RECTANGULAR
    assert not outer_lattice.fill.multiple_universes
    assert outer_lattice.fill.universe.number == outer
    assert str(outer_lattice.geometry) == str(lattice.geometry)
    assert len({lattice.universe.number, outer_lattice.universe.number, 9}) == 3
    assert f"LAT=1 FILL={outer}" in outer_lattice.mcnp_str()
    # the lattice is only seen inside of its extent
    assert window.universe.number == 9 and around.universe.number == 9
    assert window.fill.universe is lattice.universe
    assert around.fill.universe is outer_lattice.universe
    bounds = [(u.divider.location, u.side) for u in window.geometry]
    if n_dim == 2:
        answer = [(-2.0, True), (2.5, False), (-0.5, True), (1.5, False)]
    else:
        answer = [(-2.0, True), (1.0, False), (-0.5, True), (2.5, False)]
        answer += [(-1.0, True), (3.0, False)]
    assert bounds == answer
    assert len(around.geometry) == 2 * n_dim
    for cell in (window, around):
        assert list(cell.fill.transform.displacement_vector) == [-1.25, 0.0, 0.0]
    assert outside.importance.neutron == 0.0
    found = compare_at_random_points(path, problem, 3000, [3.0, 11.0])
    assert found == {1, 2, None, "outside"}
    out_file = os.path.join(str(tmp_path), "lattice.imcnp")
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        problem.write_problem(out_file)
    check_file_format(out_file)


def test_lattice_in_a_lattice(tmp_path):
    geometry = PINS.format(transform="").replace('fill="9"', 'fill="8"')
    geometry += LATTICE_2D.format(outer='outer="1"')
    geometry += """
    <lattice id="8">
      <pitch>6.0 6.0</pitch>
      <dimension>2 2</dimension>
      <lower_left>-6.0 -6.0</lower_left>
      <universes>
        9 2
        1 9 </universes>
    </lattice>
    """
    path = write_model(tmp_path, geometry, TWO_MATERIALS)
    problem = montepy.from_model_xml(path)
    assert problem.cells[1].fill.universe.number == 8
    found = compare_at_random_points(path, problem, 3000, [7.0, 11.0])
    # there is nothing around a lattice with no outer universe
    assert found == {1, 2, None, "outside", "undefined"}


def test_lattice_errors(tmp_path):
    def convert(lattice):
        geometry = PINS.format(transform="") + lattice
        return montepy.from_model_xml(write_model(tmp_path, geometry, TWO_MATERIALS))

    base = LATTICE_2D.format(outer="")
    with pytest.raises(ValueError, match="6 universes"):
        convert(base.replace("2 1 1 <", "2 1 <"))
    with pytest.raises(ValueError, match="2 or 3 values"):
        convert(base.replace("<pitch>1.5 1.0</pitch>", "<pitch>1.5</pitch>"))
    with pytest.raises(ValueError, match="positive"):
        convert(base.replace("<pitch>1.5 1.0</pitch>", "<pitch>1.5 -1.0</pitch>"))
    with pytest.raises(ValueError, match="no cells"):
        convert(base.replace("2 1 1 <", "2 1 5 <"))
    with pytest.raises(ValueError, match="no cells"):
        convert(LATTICE_2D.format(outer='outer="5"'))


# ----------------------------------------------------------------------------
# Files
# ----------------------------------------------------------------------------


def test_unsupported(tmp_path):
    hex_lattice = '<hex_lattice id="9" n_rings="1"><pitch>1</pitch><center>0 0</center><universes>1</universes></hex_lattice>'
    geometry = PINS.format(transform="") + hex_lattice
    with pytest.raises(UnsupportedFeature, match="[Hh]exagonal"):
        montepy.from_model_xml(write_model(tmp_path, geometry, TWO_MATERIALS))
    geometry = SPHERE_WORLD + '<dagmc_universe id="9" filename="dagmc.h5m"/>'
    with pytest.raises(UnsupportedFeature, match="DAGMC"):
        montepy.from_model_xml(write_model(tmp_path, geometry, WATER))


def test_bad_files(tmp_path):
    path = os.path.join(str(tmp_path), "model.xml")
    with pytest.raises(FileNotFoundError):
        montepy.from_model_xml(path)
    with pytest.raises(TypeError):
        montepy.from_model_xml(5)
    for text, message in [
        ("this is not XML", "XML"),
        ("<geometry></geometry>", "model.xml"),
        ("<model><materials/></model>", "geometry"),
        ("<model><geometry/></model>", "root"),
        ('<model><geometry><cell material="void"/></geometry></model>', "id"),
    ]:
        with open(path, "w") as fh:
            fh.write(text)
        with pytest.raises(ValueError, match=message):
            montepy.from_model_xml(path)


def test_path_types(tmp_path):
    import pathlib

    path = write_model(tmp_path, SPHERE_WORLD, WATER)
    problem = montepy.from_model_xml(pathlib.Path(path))
    assert len(problem.cells) == 2
    assert problem.title.title == "Converted from the OpenMC model: model.xml"
    assert "2 0 1 imp:n=0.0" in problem.cells[2].mcnp_str()


# ----------------------------------------------------------------------------
# What was fixed in MontePy for objects that are made from scratch
# ----------------------------------------------------------------------------


def test_new_cell_leading_comment():
    cell = montepy.Cell(number=5)
    surface = montepy.SphereAtOrigin(number=1)
    surface.radius = 2.0
    cell.geometry = -surface
    cell.leading_comments = [montepy.input_parser.syntax_node.CommentNode("c hi")]
    assert "hi" in cell.leading_comments
    assert cell.mcnp_str().split("\n")[0] == "c hi"
    assert cell.mcnp_str().split("\n")[1].startswith("5 0 -1")


def test_new_cell_fill_transform():
    problem = montepy.MCNP_Problem()
    surface = montepy.SphereAtOrigin(number=1)
    surface.radius = 2.0
    universe = montepy.Universe(3)
    problem.universes.append(universe)
    # a transform with no number
    cell = montepy.Cell(number=5)
    cell.geometry = -surface
    cell.fill.universe = universe
    transform = montepy.Transform(pass_through=True)
    transform.displacement_vector = np.array([1.0, 2.0, 3.0])
    cell.fill.transform = transform
    problem.cells.append(cell)
    assert "FILL=3 (1 2 3 )" in cell.mcnp_str()
    # a transform with a number
    transform = montepy.Transform(number=7)
    transform.displacement_vector = np.array([1.0, 2.0, 3.0])
    problem.transforms.append(transform)
    cell = montepy.Cell(number=6)
    cell.geometry = -surface
    cell.fill.universe = universe
    cell.fill.transform = transform
    problem.cells.append(cell)
    assert "FILL=3 (7)" in cell.mcnp_str()
    transform.number = 8
    assert "FILL=3 (8)" in cell.mcnp_str()
    # and taking it away again
    cell.fill.transform = None
    assert cell.mcnp_str().rstrip().endswith("FILL=3")

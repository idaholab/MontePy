# Copyright 2024, Battelle Energy Alliance, LLC All Rights Reserved.
import hypothesis
from hypothesis import given, settings, strategies as st
import copy
import montepy
import montepy.cells
from montepy.errors import NumberConflictError
import unittest
import pytest
import os


class TestNumberedObjectCollection(unittest.TestCase):
    def setUp(self):
        self.simple_problem = montepy.read_input("tests/inputs/test.imcnp")

    def test_bad_init(self):
        with self.assertRaises(TypeError):
            montepy.cells.Cells(5)

    def test_numbers(self):
        cell_numbers = [1, 2, 3, 99, 5]
        surf_numbers = [1000, 1005, 1010, 1015, 1020, 1025]
        mat_numbers = [1, 2, 3]
        problem = self.simple_problem
        self.assertEqual(list(problem.cells.numbers), cell_numbers)
        self.assertEqual(list(problem.surfaces.numbers), surf_numbers)
        self.assertEqual(list(problem.materials.numbers), mat_numbers)

    def test_number_conflict_init(self):
        cells = list(self.simple_problem.cells)
        cells.append(cells[1])
        with self.assertRaises(NumberConflictError):
            montepy.cells.Cells(cells)

    def test_check_number(self):
        with self.assertRaises(NumberConflictError):
            self.simple_problem.cells.check_number(1)
        with self.assertRaises(TypeError):
            self.simple_problem.cells.check_number("5")
        # testing a number that shouldn't conflict to ensure error isn't raised
        self.simple_problem.cells.check_number(20)

    def test_objects(self):
        generated = list(self.simple_problem.cells)
        objects = self.simple_problem.cells.objects
        self.assertEqual(generated, objects)

    def test_pop(self):
        cells = copy.deepcopy(self.simple_problem.cells)
        size = len(cells)
        target = list(cells)[-1]
        popped = cells.pop()
        self.assertEqual(target, popped)
        self.assertEqual(size - 1, len(cells))
        with self.assertRaises(TypeError):
            cells.pop("hi")

    def test_extend(self):
        surfaces = copy.deepcopy(self.simple_problem.surfaces)
        extender = list(surfaces)[0:2]
        size = len(surfaces)
        with self.assertRaises(NumberConflictError):
            surfaces.extend(extender)
        self.assertEqual(len(surfaces), size)
        extender = copy.deepcopy(extender)
        extender[0].number = 50
        extender[1].number = 60
        surfaces.extend(extender)
        self.assertEqual(len(surfaces), size + 2)
        # force a num_cache miss
        extender = copy.deepcopy(extender)
        for surf in extender:
            surf._problem = None
        surfaces[1000].number = 1
        extender[0].number = 1000
        extender[1].number = 70
        surfaces.extend(extender)
        self.assertEqual(len(surfaces), size + 4)
        with self.assertRaises(TypeError):
            surfaces.extend(5)
        with self.assertRaises(TypeError):
            surfaces.extend([5])

    def test_iter(self):
        size = len(self.simple_problem.cells)
        counter = 0
        for cell in self.simple_problem.cells:
            counter += 1
        self.assertEqual(size, counter)

    def test_append(self):
        cells = copy.deepcopy(self.simple_problem.cells)
        cell = copy.deepcopy(cells[1])
        size = len(cells)
        with self.assertRaises(NumberConflictError):
            cells.append(cell)
        with self.assertRaises(TypeError):
            cells.append(5)
        cell.number = 20
        cells.append(cell)
        self.assertEqual(len(cells), size + 1)

    def test_append_renumber(self):
        cells = copy.deepcopy(self.simple_problem.cells)
        size = len(cells)
        cell = copy.deepcopy(cells[1])
        cell.number = 20
        cells.append_renumber(cell)
        self.assertEqual(len(cells), size + 1)
        with self.assertRaises(TypeError):
            cells.append_renumber(5)
        with self.assertRaises(TypeError):
            cells.append_renumber(cell, "hi")
        cell = copy.deepcopy(cell)
        cell._problem = None
        cell.number = 1
        cells.append_renumber(cell)
        self.assertEqual(cell.number, 4)
        self.assertEqual(len(cells), size + 2)

    def test_append_renumber_problems(self):
        print(hex(id(self.simple_problem.materials._problem)))
        prob1 = copy.deepcopy(self.simple_problem)
        prob2 = copy.deepcopy(self.simple_problem)
        print(hex(id(self.simple_problem.materials._problem)))
        # Delete Material 2, making its number available.
        prob2.materials.remove(prob2.materials[2])
        len_mats = len(prob2.materials)
        mat1 = prob1.materials[1]
        new_num = prob2.materials.append_renumber(mat1)
        assert new_num == 2, "Material not renumbered correctly."
        assert len(prob2.materials) == len_mats + 1, "Material not appended"
        assert prob2.materials[2] is mat1, "Material 2 is not the new material"

    def test_request_number(self):
        cells = self.simple_problem.cells
        self.assertEqual(cells.request_number(6), 6)
        self.assertEqual(cells.request_number(1), 4)
        self.assertEqual(cells.request_number(99, 6), 105)
        with self.assertRaises(TypeError):
            cells.request_number("5")
        with self.assertRaises(TypeError):
            cells.request_number(1, "5")

    def test_next_number(self):
        cells = self.simple_problem.cells
        self.assertEqual(cells.next_number(), 100)
        self.assertEqual(cells.next_number(6), 105)
        with self.assertRaises(TypeError):
            cells.next_number("5")
        with self.assertRaises(ValueError):
            cells.next_number(-1)

    def test_getitem(self):
        cells = self.simple_problem.cells
        list_version = list(cells)
        self.assertEqual(cells[1], list_version[0])
        # force stale cache misses
        cells[1].number = 20
        with self.assertRaises(KeyError):
            cells[1]
        # force cache miss
        self.assertEqual(cells[20], list_version[0])
        with self.assertRaises(TypeError):
            cells["5"]

    def test_delete(self):
        cells = copy.deepcopy(self.simple_problem.cells)
        size = len(cells)
        del cells[1]
        self.assertEqual(size - 1, len(cells))
        with self.assertRaises(TypeError):
            del cells["5"]

    def test_setitem(self):
        cells = copy.deepcopy(self.simple_problem.cells)
        cell = cells[1]
        size = len(cells)
        with self.assertRaises(NumberConflictError):
            cells[1] = cell
        with self.assertRaises(TypeError):
            cells[1] = 5
        with self.assertRaises(TypeError):
            cells["1"] = cell
        cell = copy.deepcopy(cell)
        cell.number = 20
        cells[50] = cell
        self.assertEqual(len(cells), size + 1)

    def test_iadd(self):
        cells = copy.deepcopy(self.simple_problem.cells)
        list_cells = list(cells)
        size = len(cells)
        with self.assertRaises(NumberConflictError):
            cells += list_cells
        with self.assertRaises(NumberConflictError):
            cells += montepy.cells.Cells(list_cells)

        with self.assertRaises(TypeError):
            cells += 5
        with self.assertRaises(TypeError):
            cells += [5]

        list_cells = [copy.deepcopy(cells[1])]
        list_cells[0].number = 20
        cells += list_cells
        self.assertEqual(len(cells), size + 1)

        this_problem = copy.deepcopy(self.simple_problem)
        for cell in this_problem.cells:
            cell.number += 1000
        this_problem.cells += self.simple_problem.cells
        self.assertEqual(len(this_problem.cells), size * 2)

    def test_slice(self):
        test_numbers = [c.number for c in self.simple_problem.cells[1:5]]
        self.assertEqual([1, 2, 3, 5], test_numbers)
        test_numbers = [c.number for c in self.simple_problem.cells[2:]]
        self.assertEqual([2, 3, 5, 99], test_numbers)
        test_numbers = [c.number for c in self.simple_problem.cells[::-3]]
        self.assertEqual([99, 3], test_numbers)
        test_numbers = [c.number for c in self.simple_problem.cells[:6:3]]
        self.assertEqual([3], test_numbers)
        test_numbers = [c.number for c in self.simple_problem.cells[5::-1]]
        self.assertEqual([5, 3, 2, 1], test_numbers)
        test_numbers = [s.number for s in self.simple_problem.surfaces[1000::10]]
        self.assertEqual([1000, 1010, 1020], test_numbers)
        test_numbers = [s.number for s in self.simple_problem.surfaces[:]]
        self.assertEqual([1000, 1005, 1010, 1015, 1020, 1025], test_numbers)
        test_numbers = [m.number for m in self.simple_problem.materials[:2]]
        self.assertEqual([1, 2], test_numbers)
        test_numbers = [m.number for m in self.simple_problem.materials[::2]]
        self.assertEqual([2], test_numbers)

    def test_get(self):
        cell_found = self.simple_problem.cells.get(1)
        self.assertEqual(self.simple_problem.cells[1], cell_found)
        surf_not_found = self.simple_problem.surfaces.get(39)  # 39 buried, 0 found
        self.assertIsNone(surf_not_found)
        default_mat = self.simple_problem.materials[3]
        self.assertEqual(
            self.simple_problem.materials.get(42, default_mat), default_mat
        )

    def test_keys(self):
        cell_nums = []
        for c in self.simple_problem.cells:
            cell_nums.append(c.number)
        cell_keys = []
        for k in self.simple_problem.cells.keys():
            cell_keys.append(k)
        self.assertEqual(cell_nums, cell_keys)

    def test_values(self):
        list_cells = list(self.simple_problem.cells)
        list_values = list(self.simple_problem.cells.values())
        self.assertEqual(list_cells, list_values)

    def test_items(self):
        zipped = zip(
            self.simple_problem.cells.keys(), self.simple_problem.cells.values()
        )
        cell_items = self.simple_problem.cells.items()
        self.assertTupleEqual(tuple(zipped), tuple(cell_items))

    def test_surface_generators(self):
        answer_num = [1000, 1010]
        spheres = list(self.simple_problem.surfaces.so)
        self.assertEqual(len(answer_num), len(spheres))
        for i, sphere in enumerate(spheres):
            self.assertEqual(answer_num[i], sphere.number)

    def test_number_adding_concurancy(self):
        surfaces = copy.deepcopy(self.simple_problem.surfaces)
        new_surf = copy.deepcopy(surfaces[1005])
        new_surf.number = 5
        surfaces.append(new_surf)
        size = len(surfaces)
        new_surf = copy.deepcopy(new_surf)
        with self.assertRaises(NumberConflictError):
            surfaces.append(new_surf)
        surfaces.append_renumber(new_surf)
        self.assertEqual(len(surfaces), size + 1)
        self.assertEqual(new_surf.number, 6)

    def test_str(self):
        cells = self.simple_problem.cells
        self.assertEqual(str(cells), "Cells: [1, 2, 3, 99, 5]")
        key_phrases = [
            "Numbered_object_collection: obj_class: <class 'montepy.cell.Cell'>",
            "Objects: [CELL: 1",
            "Number cache: {1: CELL: 1",
        ]
        for phrase in key_phrases:
            self.assertIn(phrase, repr(cells))


# test data numbered object
@pytest.fixture(scope="module")
def read_simple_problem():
    return montepy.read_input(os.path.join("tests", "inputs", "test.imcnp"))


@pytest.fixture
def cp_simple_problem(read_simple_problem):
    return copy.deepcopy(read_simple_problem)


def test_data_init(cp_simple_problem):
    new_mats = montepy.materials.Materials(
        list(cp_simple_problem.materials), problem=cp_simple_problem
    )
    assert list(new_mats) == list(cp_simple_problem.materials)


def test_data_append(cp_simple_problem):
    prob = cp_simple_problem
    new_mat = copy.deepcopy(next(iter(prob.materials)))
    new_mat.number = prob.materials.request_number()
    prob.materials.append(new_mat)
    assert new_mat in prob.materials
    assert new_mat in prob.data_inputs
    assert prob.data_inputs.count(new_mat) == 1
    # trigger getting data_inputs end
    prob.materials.clear()
    prob.materials.append(new_mat)
    assert new_mat in prob.materials
    assert new_mat in prob.data_inputs
    assert prob.data_inputs.count(new_mat) == 1
    prob.data_inputs.clear()
    prob.materials._last_index = None
    new_mat = copy.deepcopy(next(iter(prob.materials)))
    new_mat.number = prob.materials.request_number()
    prob.materials.append(new_mat)
    assert new_mat in prob.materials
    assert new_mat in prob.data_inputs
    assert prob.data_inputs.count(new_mat) == 1
    # trigger getting index of last material
    prob.materials._last_index = None
    new_mat = copy.deepcopy(next(iter(prob.materials)))
    new_mat.number = prob.materials.request_number()
    prob.materials.append(new_mat)
    assert new_mat in prob.materials
    assert new_mat in prob.data_inputs
    assert prob.data_inputs.count(new_mat) == 1


def test_data_append_renumber(cp_simple_problem):
    prob = cp_simple_problem
    new_mat = copy.deepcopy(next(iter(prob.materials)))
    prob.materials.append_renumber(new_mat)
    assert new_mat in prob.materials
    assert new_mat in prob.data_inputs
    assert prob.data_inputs.count(new_mat) == 1


def test_data_remove(cp_simple_problem):
    prob = cp_simple_problem
    old_mat = next(iter(prob.materials))
    prob.materials.remove(old_mat)
    assert old_mat not in prob.materials
    assert old_mat not in prob.data_inputs


def test_data_delete(cp_simple_problem):
    prob = cp_simple_problem
    old_mat = next(iter(prob.materials))
    del prob.materials[old_mat.number]
    assert old_mat not in prob.materials
    assert old_mat not in prob.data_inputs
    with pytest.raises(TypeError):
        del prob.materials["foo"]


def test_data_clear(cp_simple_problem):
    data_len = len(cp_simple_problem.data_inputs)
    mat_len = len(cp_simple_problem.materials)
    cp_simple_problem.materials.clear()
    assert len(cp_simple_problem.materials) == 0
    assert len(cp_simple_problem.data_inputs) == data_len - mat_len


def test_data_pop(cp_simple_problem):
    old_mat = next(reversed(list(cp_simple_problem.materials)))
    popper = cp_simple_problem.materials.pop()
    assert popper is old_mat
    assert old_mat not in cp_simple_problem.materials
    assert old_mat not in cp_simple_problem.data_inputs
    with pytest.raises(TypeError):
        cp_simple_problem.materials.pop("foo")


# disable function scoped fixtures
@settings(suppress_health_check=[hypothesis.HealthCheck.function_scoped_fixture])
@given(start_num=st.integers(), step=st.integers())
def test_num_collect_clone(cp_simple_problem, start_num, step):
    surfs = copy.deepcopy(cp_simple_problem.surfaces)
    if start_num <= 0 or step <= 0:
        with pytest.raises(ValueError):
            surfs.clone(start_num, step)
        return
    for clear in [False, True]:
        if clear:
            surfs.link_to_problem(None)
        new_surfs = surfs.clone(start_num, step)
        for new_surf, old_surf in zip(new_surfs, surfs):
            assert new_surf is not old_surf
            assert new_surf.surface_type == old_surf.surface_type
            assert new_surf.number != old_surf.number


def test_num_collect_clone_default(cp_simple_problem):
    surfs = copy.deepcopy(cp_simple_problem.surfaces)
    for clear in [False, True]:
        if clear:
            surfs.link_to_problem(None)
        new_surfs = surfs.clone()
        for new_surf, old_surf in zip(new_surfs, surfs):
            assert new_surf is not old_surf
            assert new_surf.surface_type == old_surf.surface_type
            assert new_surf.number != old_surf.number


@pytest.mark.parametrize(
    "args, error",
    [
        (("c", 1), TypeError),
        ((1, "d"), TypeError),
        ((-1, 1), ValueError),
        ((0, 1), ValueError),
        ((1, 0), ValueError),
        ((1, -1), ValueError),
    ],
)
def test_num_collect_clone_bad(cp_simple_problem, args, error):
    surfs = cp_simple_problem.surfaces
    with pytest.raises(error):
        surfs.clone(*args)

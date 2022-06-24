import copy
import mcnpy
from mcnpy.errors import NumberConflictError
import unittest


class TestNumberedObjectCollection(unittest.TestCase):
    def setUp(self):
        self.simple_problem = mcnpy.read_input("tests/inputs/test.imcnp")

    def test_numbers(self):
        cell_numbers = [1, 2, 3, 99, 5]
        surf_numbers = [1000, 1005, 1010]
        mat_numbers = [1, 2, 3]
        problem = self.simple_problem
        self.assertEqual(list(problem.cells.numbers), cell_numbers)
        self.assertEqual(list(problem.surfaces.numbers), surf_numbers)
        self.assertEqual(list(problem.materials.numbers), mat_numbers)

    def test_number_conflict_init(self):
        cells = list(self.simple_problem.cells)
        cells.append(cells[1])
        with self.assertRaises(NumberConflictError):
            mcnpy.cells.Cells(cells)

    def test_check_number(self):
        with self.assertRaises(NumberConflictError):
            self.simple_problem.cells.check_number(1)
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
        extender[0].number = 1000
        extender[1].number = 70
        surfaces[1000].number = 1
        surfaces.extend(extender)
        self.assertEqual(len(surfaces), size + 4)

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
        cell = copy.deepcopy(cell)
        cell.number = 1
        cells.append_renumber(cell)
        self.assertEqual(cell.number, 4)
        self.assertEqual(len(cells), size + 2)

    def test_request_number(self):
        cells = self.simple_problem.cells
        self.assertEqual(cells.request_number(6), 6)
        self.assertEqual(cells.request_number(1), 4)
        self.assertEqual(cells.request_number(99, 6), 105)

    def test_next_number(self):
        cells = self.simple_problem.cells
        self.assertEqual(cells.next_number(), 100)
        self.assertEqual(cells.next_number(6), 105)

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

    def test_delete(self):
        cells = copy.deepcopy(self.simple_problem.cells)
        size = len(cells)
        del cells[1]
        self.assertEqual(size - 1, len(cells))

    def test_setitem(self):
        cells = copy.deepcopy(self.simple_problem.cells)
        cell = cells[1]
        size = len(cells)
        with self.assertRaises(NumberConflictError):
            cells[1] = cell
        with self.assertRaises(TypeError):
            cells[1] = 5
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
            cells += mcnpy.cells.Cells(list_cells)

        with self.assertRaises(TypeError):
            cells += 5
        with self.assertRaises(TypeError):
            cells += [5]

        list_cells = [copy.deepcopy(cells[1])]
        list_cells[0].number = 20
        cells += list_cells
        self.assertEqual(len(cells), size + 1)

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

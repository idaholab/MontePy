# Copyright 2024, Battelle Energy Alliance, LLC All Rights Reserved.
import hypothesis
from hypothesis import given, settings, strategies as st
import copy
import itertools as it

import montepy
import montepy.cells
from montepy.exceptions import NumberConflictError
import pytest
import os


class TestNumberedObjectCollection:

    @pytest.fixture(scope="class")
    def read_simple_problem(_):
        return montepy.read_input(os.path.join("tests", "inputs", "test.imcnp"))

    @pytest.fixture
    def cp_simple_problem(_, read_simple_problem):
        return copy.deepcopy(read_simple_problem)

    def test_bad_init(self):
        with pytest.raises(TypeError):
            montepy.Cells(5)
        with pytest.raises(TypeError):
            montepy.Cells([5])

    def test_numbers(self, cp_simple_problem):
        cell_numbers = [1, 2, 3, 99, 5]
        surf_numbers = [1000, 1005, 1010, 1015, 1020, 1025]
        mat_numbers = [1, 2, 3]
        problem = cp_simple_problem
        assert list(problem.cells.numbers) == cell_numbers
        assert list(problem.surfaces.numbers) == surf_numbers
        assert list(problem.materials.numbers) == mat_numbers

    def test_number_conflict_init(self, cp_simple_problem):
        cells = list(cp_simple_problem.cells)
        cells.append(cells[1])
        with pytest.raises(NumberConflictError):
            montepy.cells.Cells(cells)

    def test_check_number(self, cp_simple_problem):
        with pytest.raises(NumberConflictError):
            cp_simple_problem.cells.check_number(1)
        with pytest.raises(TypeError):
            cp_simple_problem.cells.check_number("5")
        # testing a number that shouldn't conflict to ensure error isn't raised
        cp_simple_problem.cells.check_number(20)
        mat = montepy.Material()
        cp_simple_problem.materials.append_renumber(mat)
        assert mat.number > 0
        with pytest.raises(ValueError):
            cp_simple_problem.materials.check_number(-1)

    def test_objects(self, cp_simple_problem):
        generated = list(cp_simple_problem.cells)
        objects = cp_simple_problem.cells.objects
        assert generated == objects

    def test_pop(self, cp_simple_problem):
        cells = copy.deepcopy(cp_simple_problem.cells)
        size = len(cells)
        target = list(cells)[-1]
        popped = cells.pop()
        assert target == popped
        assert size - 1 == len(cells)
        with pytest.raises(TypeError):
            cells.pop("hi")

    def test_extend(self, cp_simple_problem):
        surfaces = copy.deepcopy(cp_simple_problem.surfaces)
        extender = list(surfaces)[0:2]
        size = len(surfaces)
        with pytest.raises(NumberConflictError):
            surfaces.extend(extender)
        assert len(surfaces) == size
        extender = copy.deepcopy(extender)
        extender[0].number = 50
        extender[1].number = 60
        surfaces.extend(extender)
        assert len(surfaces) == size + 2
        # force a num_cache miss
        extender = copy.deepcopy(extender)
        for surf in extender:
            surf._problem = None
        surfaces[1000].number = 1
        extender[0].number = 1000
        extender[1].number = 70
        surfaces.extend(extender)
        assert len(surfaces) == size + 4
        with pytest.raises(TypeError):
            surfaces.extend(5)
        with pytest.raises(TypeError):
            surfaces.extend([5])

    def test_iter(self, cp_simple_problem):
        size = len(cp_simple_problem.cells)
        counter = 0
        for cell in cp_simple_problem.cells:
            counter += 1
        assert size == counter

    def test_append(self, cp_simple_problem):
        cells = copy.deepcopy(cp_simple_problem.cells)
        cell = copy.deepcopy(cells[1])
        size = len(cells)
        with pytest.raises(NumberConflictError):
            cells.append(cell)
        with pytest.raises(TypeError):
            cells.append(5)
        cell.number = 20
        cells.append(cell)
        assert len(cells) == size + 1

    def test_add(_):
        cells = montepy.Cells()
        cell = montepy.Cell()
        cell.number = 2
        cells.add(cell)
        assert cell in cells
        # test silent no-op
        cells.add(cell)
        cell = copy.deepcopy(cell)
        with pytest.raises(NumberConflictError):
            cells.add(cell)
        with pytest.raises(TypeError):
            cells.add(5)

    def test_update(_):
        cells = montepy.Cells()
        cell_list = []
        for i in range(1, 6):
            cell_list.append(montepy.Cell())
            cell_list[-1].number = i
        cells.update(cell_list)
        for cell in cell_list:
            assert cell in cells
        with pytest.raises(TypeError):
            cells.update(5)
        with pytest.raises(TypeError):
            cells.update({5})
        cell = montepy.Cell()
        cell.number = 1
        cells.update([cell])
        assert cells[1] is cell_list[0]
        assert cells[1] is not cell

    def test_append_renumber(self, cp_simple_problem):
        cells = copy.deepcopy(cp_simple_problem.cells)
        size = len(cells)
        cell = copy.deepcopy(cells[1])
        cell.number = 20
        cells.append_renumber(cell)
        assert len(cells) == size + 1
        with pytest.raises(TypeError):
            cells.append_renumber(5)
        with pytest.raises(TypeError):
            cells.append_renumber(cell, "hi")
        cell = copy.deepcopy(cell)
        cell._problem = None
        cell.number = 1
        cells.append_renumber(cell)
        assert cell.number == 4
        assert len(cells) == size + 2

    def test_append_renumber_problems(self, cp_simple_problem):
        print(hex(id(cp_simple_problem.materials._problem)))
        prob1 = copy.deepcopy(cp_simple_problem)
        prob2 = copy.deepcopy(cp_simple_problem)
        print(hex(id(cp_simple_problem.materials._problem)))
        # Delete Material 2, making its number available.
        len_mats = len(prob2.materials)
        mat1 = prob1.materials[1]
        new_num = prob2.materials.append_renumber(mat1)
        assert new_num == 4, "Material not renumbered correctly."
        assert len(prob2.materials) == len_mats + 1, "Material not appended"
        assert prob2.materials[4] is mat1, "Material 2 is not the new material"

    def test_request_number(self, cp_simple_problem):
        cells = cp_simple_problem.cells
        assert cells.request_number(6) == 6
        assert cells.request_number(1) == 4
        assert cells.request_number(99, 6) == 105
        with pytest.raises(TypeError):
            cells.request_number("5")
        with pytest.raises(TypeError):
            cells.request_number(1, "5")

    def test_next_number(self, cp_simple_problem):
        cells = cp_simple_problem.cells
        assert cells.next_number() == 100
        assert cells.next_number(6) == 105
        with pytest.raises(TypeError):
            cells.next_number("5")
        with pytest.raises(ValueError):
            cells.next_number(-1)

    def test_getitem(self, cp_simple_problem):
        cells = cp_simple_problem.cells
        list_version = list(cells)
        assert cells[1] == list_version[0]
        # force stale cache misses
        cells[1].number = 20
        with pytest.raises(KeyError):
            cells[1]
        # force cache miss
        assert cells[20] == list_version[0]
        with pytest.raises(TypeError):
            cells["5"]

    def test_delete(self, cp_simple_problem):
        cells = copy.deepcopy(cp_simple_problem.cells)
        size = len(cells)
        del cells[1]
        assert size - 1 == len(cells)
        with pytest.raises(TypeError):
            del cells["5"]

    def test_setitem(self, cp_simple_problem):
        cells = copy.deepcopy(cp_simple_problem.cells)
        cell = cells[1]
        size = len(cells)
        cell = copy.deepcopy(cell)
        with pytest.raises(NumberConflictError):
            cells[1] = cell
        with pytest.raises(TypeError):
            cells[1] = 5
        with pytest.raises(TypeError):
            cells["1"] = cell
        cell = copy.deepcopy(cell)
        cell.number = 20
        cells[50] = cell
        assert len(cells) == size + 1

    def test_iadd(self, cp_simple_problem):
        cells = copy.deepcopy(cp_simple_problem.cells)
        list_cells = list(cells)
        size = len(cells)
        with pytest.raises(NumberConflictError):
            cells += list_cells
        with pytest.raises(NumberConflictError):
            cells += montepy.cells.Cells(list_cells)

        with pytest.raises(TypeError):
            cells += 5
        with pytest.raises(TypeError):
            cells += [5]

        list_cells = [copy.deepcopy(cells[1])]
        list_cells[0].number = 20
        cells += list_cells
        assert len(cells) == size + 1

        this_problem = copy.deepcopy(cp_simple_problem)
        # just ignore materials being added
        this_problem.materials.clear()
        for cell in this_problem.cells:
            cell.number += 1000
        this_problem.cells += cp_simple_problem.cells
        assert len(this_problem.cells) == size * 2

    def test_slice(self, cp_simple_problem):
        test_numbers = [c.number for c in cp_simple_problem.cells[1:5]]
        assert [1, 2, 3, 5] == test_numbers
        test_numbers = [c.number for c in cp_simple_problem.cells[2:]]
        assert [2, 3, 5, 99] == test_numbers
        test_numbers = [c.number for c in cp_simple_problem.cells[::-3]]
        assert [99, 3] == test_numbers
        test_numbers = [c.number for c in cp_simple_problem.cells[:6:3]]
        assert [3] == test_numbers
        test_numbers = [c.number for c in cp_simple_problem.cells[5::-1]]
        assert [5, 3, 2, 1] == test_numbers
        test_numbers = [s.number for s in cp_simple_problem.surfaces[1000::10]]
        assert [1000, 1010, 1020] == test_numbers
        test_numbers = [s.number for s in cp_simple_problem.surfaces[:]]
        assert [1000, 1005, 1010, 1015, 1020, 1025] == test_numbers
        test_numbers = [m.number for m in cp_simple_problem.materials[:2]]
        assert [1, 2] == test_numbers
        test_numbers = [m.number for m in cp_simple_problem.materials[::2]]
        assert [2] == test_numbers

    def test_get(self, cp_simple_problem):
        cell_found = cp_simple_problem.cells.get(1)
        assert cp_simple_problem.cells[1] == cell_found
        surf_not_found = cp_simple_problem.surfaces.get(39)  # 39 buried, 0 found
        assert (surf_not_found) is None
        default_mat = cp_simple_problem.materials[3]
        assert cp_simple_problem.materials.get(42, default_mat) == default_mat
        # force a cache miss
        cells = cp_simple_problem.cells
        cells.link_to_problem(None)
        cell = cells[1]
        cell.number = 23
        assert cells.get(23) is cell

    def test_keys(self, cp_simple_problem):
        cell_nums = []
        for c in cp_simple_problem.cells:
            cell_nums.append(c.number)
        cell_keys = []
        for k in cp_simple_problem.cells.keys():
            cell_keys.append(k)
        assert cell_nums == cell_keys
        cells = montepy.Cells()
        # test blank keys
        assert len(list(cells.keys())) == 0

    def test_values(self, cp_simple_problem):
        list_cells = list(cp_simple_problem.cells)
        list_values = list(cp_simple_problem.cells.values())
        assert list_cells == list_values
        cells = montepy.Cells()
        assert len(list(cells.keys())) == 0

    def test_items(self, cp_simple_problem):
        zipped = zip(cp_simple_problem.cells.keys(), cp_simple_problem.cells.values())
        cell_items = cp_simple_problem.cells.items()
        assert tuple(zipped) == tuple(cell_items)
        cells = montepy.Cells()
        assert len(list(cells.keys())) == 0

    def test_eq(_, cp_simple_problem):
        cells = cp_simple_problem.cells
        new_cells = copy.copy(cells)
        assert cells == new_cells
        new_cells = montepy.Cells()
        assert cells != new_cells
        for i in range(len(cells)):
            cell = montepy.Cell()
            cell.number = i + 500
            new_cells.add(cell)
        assert new_cells != cells
        new_cells[501].number = 2
        assert new_cells != cells
        with pytest.raises(TypeError):
            cells == 5

    def test_surface_generators(self, cp_simple_problem):
        answer_num = [1000, 1010]
        spheres = list(cp_simple_problem.surfaces.so)
        assert len(answer_num) == len(spheres)
        for i, sphere in enumerate(spheres):
            assert answer_num[i] == sphere.number

    def test_number_adding_concurancy(self, cp_simple_problem):
        surfaces = copy.deepcopy(cp_simple_problem.surfaces)
        new_surf = copy.deepcopy(surfaces[1005])
        new_surf.number = 5
        surfaces.append(new_surf)
        size = len(surfaces)
        new_surf1 = copy.deepcopy(new_surf)
        with pytest.raises(NumberConflictError):
            surfaces.append(new_surf1)
        surfaces.append_renumber(new_surf1)
        assert len(surfaces) == size + 1
        assert new_surf1.number == 6

    def test_str(self, cp_simple_problem):
        cells = cp_simple_problem.cells
        assert str(cells) == "Cells: [1, 2, 3, 99, 5]"
        assert "Cells([Cell(" in repr(cells)

    def test_data_init(_, cp_simple_problem):
        new_mats = montepy.materials.Materials(
            list(cp_simple_problem.materials), problem=cp_simple_problem
        )
        assert list(new_mats) == list(cp_simple_problem.materials)

    def test_data_append(_, cp_simple_problem):
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

    def test_data_append_renumber(_, cp_simple_problem):
        prob = cp_simple_problem
        new_mat = copy.deepcopy(next(iter(prob.materials)))
        prob.materials.append_renumber(new_mat)
        assert new_mat in prob.materials
        assert new_mat in prob.data_inputs
        assert prob.data_inputs.count(new_mat) == 1

    def test_data_remove(_, cp_simple_problem):
        prob = cp_simple_problem
        old_mat = next(iter(prob.materials))
        prob.materials.remove(old_mat)
        assert old_mat not in prob.materials
        assert old_mat not in prob.data_inputs
        with pytest.raises(TypeError):
            prob.materials.remove(5)
        mat = montepy.Material()
        with pytest.raises(KeyError):
            prob.materials.remove(mat)
        # do a same number fakeout
        mat = copy.deepcopy(prob.materials[2])
        with pytest.raises(KeyError):
            prob.materials.remove(mat)

    def test_numbered_discard(_, cp_simple_problem):
        mats = cp_simple_problem.materials
        mat = mats[2]
        mats.discard(mat)
        assert mat not in mats
        # no error
        mats.discard(mat)
        mats.discard(5)

    def test_numbered_contains(_, cp_simple_problem):
        mats = cp_simple_problem.materials
        mat = mats[2]
        assert mat in mats
        assert 5 not in mats
        mat = montepy.Material()
        mat.number = 100
        assert mat not in mats
        # num cache fake out
        mat.number = 2
        assert mat not in mats

    @pytest.fixture
    def mats_sets(_):
        mats1 = montepy.Materials()
        mats2 = montepy.Materials()
        for i in range(1, 10):
            mat = montepy.Material()
            mat.number = i
            mats1.append(mat)
        for i in range(5, 15):
            mat = montepy.Material()
            mat.number = i
            mats2.append(mat)
        return (mats1, mats2)

    @pytest.mark.parametrize(
        "name, operator",
        [
            ("and", lambda a, b: a & b),
            ("or", lambda a, b: a | b),
            ("sub", lambda a, b: a - b),
            ("xor", lambda a, b: a ^ b),
            ("sym diff", lambda a, b: a.symmetric_difference(b)),
        ],
    )
    def test_numbered_set_logic(_, mats_sets, name, operator):
        mats1, mats2 = mats_sets
        mats1_nums = set(mats1.keys())
        mats2_nums = set(mats2.keys())
        new_mats = operator(mats1, mats2)
        new_nums = set(new_mats.keys())
        assert new_nums == operator(mats1_nums, mats2_nums)

    @pytest.mark.parametrize(
        "name",
        ["iand", "ior", "isub", "ixor", "sym_diff", "diff", "union", "intersection"],
    )
    def test_numbered_set_logic_update(_, mats_sets, name):
        def operator(a, b):
            if name == "iand":
                a &= b
            elif name == "ior":
                a |= b
            elif name == "isub":
                a -= b
            elif name == "ixor":
                a ^= b
            elif name == "sym_diff":
                a.symmetric_difference_update(b)
            elif name == "diff":
                a.difference_update(b)
            elif name == "union":
                a.update(b)
            elif name == "intersection":
                a.intersection_update(b)

        mats1, mats2 = mats_sets
        mats1_nums = set(mats1.keys())
        mats2_nums = set(mats2.keys())
        operator(mats1, mats2)
        new_nums = set(mats1.keys())
        operator(mats1_nums, mats2_nums)
        assert new_nums == mats1_nums

    @pytest.mark.parametrize(
        "name, operator",
        [
            ("le", lambda a, b: a <= b),
            ("lt", lambda a, b: a < b),
            ("ge", lambda a, b: a >= b),
            ("gt", lambda a, b: a > b),
            ("subset", lambda a, b: a.issubset(b)),
            ("superset", lambda a, b: a.issuperset(b)),
            ("disjoint", lambda a, b: a.isdisjoint(b)),
        ],
    )
    def test_numbered_set_logic_test(_, mats_sets, name, operator):
        mats1, mats2 = mats_sets
        mats1_nums = set(mats1.keys())
        mats2_nums = set(mats2.keys())
        answer = operator(mats1, mats2)
        assert answer == operator(mats1_nums, mats2_nums)

    @pytest.mark.parametrize(
        "name, operator",
        [
            ("intersection", lambda a, *b: a.intersection(*b)),
            ("union", lambda a, *b: a.union(*b)),
            ("difference", lambda a, *b: a.difference(*b)),
        ],
    )
    def test_numbered_set_logic_multi(_, mats_sets, name, operator):
        mats3 = montepy.Materials()
        for i in range(7, 19):
            mat = montepy.Material()
            mat.number = i
            mats3.add(mat)
        mats1, mats2 = mats_sets
        mats1_nums = set(mats1.keys())
        mats2_nums = set(mats2.keys())
        mats3_nums = set(mats3.keys())
        new_mats = operator(mats1, mats2, mats3)
        new_nums = set(new_mats.keys())
        assert new_nums == operator(mats1_nums, mats2_nums, mats3_nums)

    def test_numbered_set_logic_bad(_):
        mats = montepy.Materials()
        with pytest.raises(TypeError):
            mats & 5
        with pytest.raises(TypeError):
            mats &= {5}
        with pytest.raises(TypeError):
            mats |= {5}
        with pytest.raises(TypeError):
            mats -= {5}
        with pytest.raises(TypeError):
            mats ^= {5}
        with pytest.raises(TypeError):
            mats > 5
        with pytest.raises(TypeError):
            mats.union(5)

    def test_data_delete(_, cp_simple_problem):
        prob = cp_simple_problem
        old_mat = next(iter(prob.materials))
        del prob.materials[old_mat.number]
        assert old_mat not in prob.materials
        assert old_mat not in prob.data_inputs
        with pytest.raises(TypeError):
            del prob.materials["foo"]

    def test_data_clear(_, cp_simple_problem):
        data_len = len(cp_simple_problem.data_inputs)
        mat_len = len(cp_simple_problem.materials)
        cp_simple_problem.materials.clear()
        assert len(cp_simple_problem.materials) == 0
        assert len(cp_simple_problem.data_inputs) == data_len - mat_len

    def test_data_pop(_, cp_simple_problem):
        old_mat = next(reversed(list(cp_simple_problem.materials)))
        old_len = len(cp_simple_problem.materials)
        popper = cp_simple_problem.materials.pop()
        assert popper is old_mat
        assert len(cp_simple_problem.materials) == old_len - 1
        assert old_mat not in cp_simple_problem.materials
        assert old_mat not in cp_simple_problem.data_inputs
        with pytest.raises(TypeError):
            cp_simple_problem.materials.pop("foo")

    def test_numbered_starting_number(_):
        cells = montepy.Cells()
        assert cells.starting_number == 1
        cells.starting_number = 5
        assert cells.starting_number == 5
        with pytest.raises(TypeError):
            cells.starting_number = "hi"
        with pytest.raises(ValueError):
            cells.starting_number = -1

    # disable function scoped fixtures
    @settings(suppress_health_check=[hypothesis.HealthCheck.function_scoped_fixture])
    @given(start_num=st.integers(), step=st.integers())
    def test_num_collect_clone(_, read_simple_problem, start_num, step):
        cp_simple_problem = copy.deepcopy(read_simple_problem)
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

    @settings(
        suppress_health_check=[hypothesis.HealthCheck.function_scoped_fixture],
        deadline=500,
    )
    @given(
        start_num=st.integers(),
        step=st.integers(),
        clone_mat=st.booleans(),
        clone_region=st.booleans(),
    )
    def test_cells_clone(
        _, read_simple_problem, start_num, step, clone_mat, clone_region
    ):
        cp_simple_problem = copy.deepcopy(read_simple_problem)
        cells = copy.deepcopy(cp_simple_problem.cells)
        if start_num <= 0 or step <= 0:
            with pytest.raises(ValueError):
                cells.clone(starting_number=start_num, step=step)
            return
        for clear in [False, True]:
            if clear:
                cells.link_to_problem(None)
            new_cells = cells.clone(clone_mat, clone_region, start_num, step)
            for new_cell, old_cell in zip(new_cells, cells):
                assert new_cell is not old_cell
                assert new_cell.number != old_cell.number
                assert new_cell.geometry is not old_cell.geometry
                if clone_mat and old_cell.material:
                    assert new_cell.material is not old_cell.material
                else:
                    assert new_cell.material == old_cell.material
                if clone_region:
                    if len(old_cell.surfaces) > 0:
                        assert new_cell.surfaces != old_cell.surfaces
                    if len(old_cell.complements) > 0:
                        assert new_cell.complements != old_cell.complements
                else:
                    assert new_cell.surfaces == old_cell.surfaces
                    assert new_cell.complements == old_cell.complements
                assert new_cell.importance.neutron == old_cell.importance.neutron

    def test_num_collect_clone_default(_, cp_simple_problem):
        surfs = copy.deepcopy(cp_simple_problem.surfaces)
        for clear in [False, True]:
            if clear:
                surfs.link_to_problem(None)
            new_surfs = surfs.clone()
            for new_surf, old_surf in zip(new_surfs, surfs):
                assert new_surf is not old_surf
                assert new_surf.surface_type == old_surf.surface_type
                assert new_surf.number != old_surf.number

    def test_num_collect_link_problem(_, cp_simple_problem):
        cells = montepy.Cells()
        cells.link_to_problem(cp_simple_problem)
        assert cells._problem == cp_simple_problem
        cells.link_to_problem(None)
        assert cells._problem is None
        with pytest.raises(TypeError):
            cells.link_to_problem("hi")

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
    def test_num_collect_clone_bad(_, cp_simple_problem, args, error):
        surfs = cp_simple_problem.surfaces
        with pytest.raises(error):
            surfs.clone(*args)


class TestMaterials:

    @pytest.fixture(scope="class")
    def m0_prob(_):
        return montepy.read_input(
            os.path.join("tests", "inputs", "test_importance.imcnp")
        )

    @pytest.fixture
    def cp_m0_prob(_, m0_prob):
        return copy.deepcopy(m0_prob)

    def test_m0_defaults(_, m0_prob):
        prob = m0_prob
        assert prob.materials.default_libraries["nlib"] == "00c"
        assert prob.materials.default_libraries["plib"] == "80p"
        assert prob.materials.default_libraries["alib"] is None

    def test_m0_defaults_fresh(_):
        prob = montepy.MCNP_Problem("")
        prob.materials.default_libraries["nlib"] = "00c"
        prob.materials.default_libraries["plib"] = "80p"
        assert prob.materials.default_libraries["nlib"] == "00c"
        assert prob.materials.default_libraries["plib"] == "80p"
        assert prob.materials.default_libraries["alib"] is None

    @pytest.mark.parametrize(
        "nuclides, threshold, num",
        [
            (("26054", "26056"), 1.0, 1),
            ((montepy.Nuclide("H-1"),), 0.0, 1),
            (("B",), 1.0, 0),
        ],
    )
    def test_get_containing_all(_, m0_prob, nuclides, threshold, num):
        ret = list(m0_prob.materials.get_containing_all(*nuclides, threshold=threshold))
        assert len(ret) == num
        for mat in ret:
            assert isinstance(mat, montepy.Material)
        with pytest.raises(TypeError):
            next(m0_prob.materials.get_containing_all(m0_prob))

    @pytest.mark.parametrize(
        "nuclides, threshold, num",
        [
            (("26054", "26056"), 1.0, 1),
            ((montepy.Nuclide("H-1"),), 0.0, 1),
            (("B",), 1.0, 0),
            (("U-235", "H-1"), 0.0, 2),
        ],
    )
    def test_get_containing_any(_, m0_prob, nuclides, threshold, num):
        ret = list(m0_prob.materials.get_containing_any(*nuclides, threshold=threshold))
        assert len(ret) == num
        for mat in ret:
            assert isinstance(mat, montepy.Material)
        with pytest.raises(TypeError):
            next(m0_prob.materials.get_containing_any(m0_prob))

    @pytest.fixture
    def h2o(_):
        mat = montepy.Material()
        mat.number = 1
        mat.add_nuclide("H-1.80c", 2.0)
        mat.add_nuclide("O-16.80c", 1.0)
        return mat

    @pytest.fixture
    def mass_h2o(_):
        mat = montepy.Material()
        mat.number = 1
        mat.is_atom_fraction = False
        mat.add_nuclide("H-1.80c", 2.0)
        mat.add_nuclide("O-16.80c", 1.0)
        return mat

    @pytest.fixture
    def boric_acid(_):
        mat = montepy.Material()
        mat.number = 2
        for nuclide, fraction in {
            "1001.80c": 3.0,
            "B-10.80c": 1.0 * 0.189,
            "B-11.80c": 1.0 * 0.796,
            "O-16.80c": 3.0,
        }.items():
            mat.add_nuclide(nuclide, fraction)
        return mat

    @pytest.fixture
    def mats_dict(_, h2o, mass_h2o, boric_acid):
        return {"h2o": h2o, "mass_h2o": mass_h2o, "boric_acid": boric_acid}

    @pytest.mark.parametrize(
        "args, error, use_fixture",
        [
            (("hi", [1]), TypeError, False),
            ((["hi"], [1]), TypeError, False),
            (([], [1]), ValueError, False),  # empty materials
            ((["h2o", "mass_h2o"], [1, 2]), ValueError, True),  # mismatch is_atom
            ((["h2o", "boric_acid"], [1.0]), ValueError, True),  # mismatch lengths
            ((["h2o", "boric_acid"], "hi"), TypeError, True),
            ((["h2o", "boric_acid"], ["hi"]), TypeError, True),
            ((["h2o", "boric_acid"], [-1.0, 2.0]), ValueError, True),
            ((["h2o", "boric_acid"], [1.0, 2.0], "hi"), TypeError, True),
            ((["h2o", "boric_acid"], [1.0, 2.0], -1), ValueError, True),
            ((["h2o", "boric_acid"], [1.0, 2.0], 1, "hi"), TypeError, True),
            ((["h2o", "boric_acid"], [1.0, 2.0], 1, -1), ValueError, True),
        ],
    )
    def test_mix_bad(_, mats_dict, args, error, use_fixture):
        if use_fixture:
            mats = []
            for mat in args[0]:
                mats.append(mats_dict[mat])
            args = (mats,) + args[1:]
        with pytest.raises(error):
            mats = montepy.Materials()
            mats.mix(*args)

    @given(
        starting_num=st.one_of(st.none(), st.integers(1)),
        step=st.one_of(st.none(), st.integers(1)),
    )
    def test_mix(_, starting_num, step):
        mat = montepy.Material()
        mat.number = 1
        mat.add_nuclide("H-1.80c", 2.0)
        mat.add_nuclide("O-16.80c", 1.0)
        parents = [mat]
        mat = montepy.Material()
        mat.number = 2
        for nuclide, fraction in {
            "1001.80c": 3.0,
            "B-10.80c": 1.0 * 0.189,
            "B-11.80c": 1.0 * 0.796,
            "O-16.80c": 3.0,
        }.items():
            mat.add_nuclide(nuclide, fraction)
        parents.append(mat)
        boron_conc = 10 * 1e-6
        fractions = [1 - boron_conc, boron_conc]
        mats = montepy.Materials()
        for par in parents:
            mats.append(par)
        new_mat = mats.mix(
            parents,
            fractions,
            starting_num,
            step,
        )
        assert sum(new_mat.values) == pytest.approx(
            1.0
        )  # should normalize to 1 with fractions
        assert new_mat.is_atom_fraction == parents[0].is_atom_fraction
        flat_fracs = []
        for par, frac in zip(parents, fractions):
            par.normalize()
            flat_fracs += [frac] * len(par)
        for (new_nuc, new_frac), (old_nuc, old_frac), fraction in zip(
            new_mat, it.chain(*parents), flat_fracs
        ):
            assert new_nuc == old_nuc
            assert new_nuc is not old_nuc
            assert new_frac == pytest.approx(old_frac * fraction)
        if starting_num is None:
            starting_num = mats.starting_number
        if step is None:
            step = mats.step
        if starting_num not in [p.number for p in parents]:
            assert new_mat.number == starting_num
        else:
            assert (new_mat.number - starting_num) % step == 0

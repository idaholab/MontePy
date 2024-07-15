# Copyright 2024, Battelle Energy Alliance, LLC All Rights Reserved.
import copy
import unittest
from unittest import TestCase, expectedFailure
import os

import montepy
from montepy.data_inputs import material, thermal_scattering, volume
from montepy.input_parser.mcnp_input import (
    Input,
    Jump,
    Message,
    Title,
    ReadInput,
)
from montepy.errors import *
from montepy.particle import Particle
import numpy as np


class testFullFileIntegration(TestCase):
    @classmethod
    def setUpClass(cls):
        file_name = "tests/inputs/test.imcnp"
        cls.simple_problem = montepy.read_input(file_name)
        cls.importance_problem = montepy.read_input(
            os.path.join("tests", "inputs", "test_importance.imcnp")
        )
        cls.universe_problem = montepy.read_input(
            os.path.join("tests", "inputs", "test_universe.imcnp")
        )

    def test_original_input(self):
        cell_order = [Message, Title] + [Input] * 17
        for i, input_ob in enumerate(self.simple_problem.original_inputs):
            self.assertIsInstance(input_ob, cell_order[i])

    def test_original_input_dos(self):
        problem = montepy.read_input(os.path.join("tests", "inputs", "test_dos.imcnp"))
        cell_order = [Message, Title] + [Input] * 16
        for i, input_ob in enumerate(problem.original_inputs):
            self.assertIsInstance(input_ob, cell_order[i])

    def test_original_input_tabs(self):
        problem = montepy.read_input(os.path.join("tests", "inputs", "test_tab.imcnp"))
        cell_order = [Message, Title] + [Input] * 17
        for i, input_ob in enumerate(problem.original_inputs):
            self.assertIsInstance(input_ob, cell_order[i])

    # TODO formalize this or see if this is covered by other tests.
    def test_lazy_comments_check(self):
        problem = self.simple_problem
        material = problem.materials[2]
        for comment in material._tree.comments:
            print(repr(comment))
        print(material._tree.get_trailing_comment())

    def test_material_parsing(self):
        mat_numbers = [1, 2, 3]
        for i, mat in enumerate(self.simple_problem.materials):
            self.assertEqual(mat.number, mat_numbers[i])

    def test_surface_parsing(self):
        surf_numbers = [1000, 1005, 1010]
        for i, surf in enumerate(self.simple_problem.surfaces):
            self.assertEqual(surf.number, surf_numbers[i])

    def test_data_card_parsing(self):
        M = material.Material
        V = volume.Volume
        cards = [M, M, M, "KSRC", "KCODE", "PHYS:P", "MODE", V]
        for i, card in enumerate(self.simple_problem.data_inputs):
            if isinstance(cards[i], str):
                self.assertEqual(card.classifier.format().upper().rstrip(), cards[i])
            else:
                self.assertIsInstance(card, cards[i])
            if i == 2:
                self.assertTrue(card.thermal_scattering is not None)

    def test_cells_parsing_linking(self):
        cell_numbers = [1, 2, 3, 99, 5]
        mats = self.simple_problem.materials
        mat_answer = [mats[1], mats[2], mats[3], None, None]
        surfs = self.simple_problem.surfaces
        surf_answer = [{surfs[1000]}, {surfs[1005]}, set(surfs), {surfs[1010]}, set()]
        cells = self.simple_problem.cells
        complements = [set()] * 4 + [{cells[99]}]
        for i, cell in enumerate(self.simple_problem.cells):
            self.assertEqual(cell.number, cell_numbers[i])
            self.assertEqual(cell.material, mat_answer[i])
            surfaces = set(cell.surfaces)
            self.assertTrue(surfaces.union(surf_answer[i]) == surfaces)
            self.assertTrue(
                set(cell.complements).union(complements[i]) == complements[i]
            )

    def test_message(self):
        lines = ["this is a message", "it should show up at the beginning", "foo"]
        for i, line in enumerate(self.simple_problem.message.lines):
            self.assertEqual(line, lines[i])

    def test_title(self):
        answer = "MCNP Test Model for MOAA"
        self.assertEqual(answer, self.simple_problem.title.title)

    def test_read_card_recursion(self):
        problem = montepy.read_input("tests/inputs/testReadRec1.imcnp")
        self.assertEqual(len(problem.cells), 1)
        self.assertEqual(len(problem.surfaces), 1)
        self.assertIn(montepy.particle.Particle.PHOTON, problem.mode)

    def test_problem_str(self):
        output = str(self.simple_problem)
        self.assertIn("MCNP problem for: tests/inputs/test.imcnp", output)

    def test_write_to_file(self):
        out = "foo.imcnp"
        try:
            problem = copy.deepcopy(self.simple_problem)
            problem.write_to_file(out)
            with open(out, "r") as fh:
                for line in fh:
                    print(line.rstrip())
            test_problem = montepy.read_input(out)
            for i, cell in enumerate(self.simple_problem.cells):
                num = cell.number
                self.assertEqual(num, test_problem.cells[num].number)
                for attr in {"universe", "volume"}:
                    print(f"testing the attribute: {attr}")
                    gold = getattr(self.simple_problem.cells[num], attr)
                    test = getattr(test_problem.cells[num], attr)
                    if attr in {"universe"} and gold is not None:
                        gold, test = (gold.number, test.number)
                    self.assertEqual(gold, test)
            for i, surf in enumerate(self.simple_problem.surfaces):
                num = surf.number
                self.assertEqual(surf.number, test_problem.surfaces[num].number)
            for i, data in enumerate(self.simple_problem.data_inputs):
                if isinstance(data, material.Material):
                    self.assertEqual(data.number, test_problem.data_inputs[i].number)
                    if data.thermal_scattering is not None:
                        assert (
                            test_problem.data_inputs[i].thermal_scattering is not None
                        )
                elif isinstance(data, volume.Volume):
                    self.assertEqual(str(data), str(test_problem.data_inputs[i]))
                else:
                    print("Rewritten data", data.data)
                    print("Original input data", test_problem.data_inputs[i].data)
                    self.assertEqual(data.data, test_problem.data_inputs[i].data)
        finally:
            if os.path.exists(out):
                os.remove(out)

    def test_cell_material_setter(self):
        cell = copy.deepcopy(self.simple_problem.cells[1])
        mat = self.simple_problem.materials[2]
        cell.material = mat
        self.assertEqual(cell.material, mat)
        cell.material = None
        self.assertIsNone(cell.material)
        with self.assertRaises(TypeError):
            cell.material = 5

    def test_problem_cells_setter(self):
        problem = copy.deepcopy(self.simple_problem)
        cells = copy.deepcopy(self.simple_problem.cells)
        cells.remove(cells[1])
        with self.assertRaises(TypeError):
            problem.cells = 5
        with self.assertRaises(TypeError):
            problem.cells = [5]
        with self.assertRaises(TypeError):
            problem.cells.append(5)
        problem.cells = cells
        self.assertEqual(problem.cells.objects, cells.objects)
        problem.cells = list(cells)
        self.assertEqual(problem.cells[2], cells[2])
        # test that cell modifiers are still there
        output = problem.cells._importance.format_for_mcnp_input((6, 2, 0))

    def test_problem_test_setter(self):
        problem = copy.deepcopy(self.simple_problem)
        sample_title = "This is a title"
        problem.title = sample_title
        self.assertEqual(problem.title.title, sample_title)
        with self.assertRaises(TypeError):
            problem.title = 5

    def test_problem_children_adder(self):
        problem = copy.deepcopy(self.simple_problem)
        BT = montepy.input_parser.block_type.BlockType
        in_str = "5 SO 5.0"
        card = montepy.input_parser.mcnp_input.Input([in_str], BT.SURFACE)
        surf = montepy.surfaces.surface_builder.surface_builder(card)
        in_str = "M5 6000.70c 1.0"
        card = montepy.input_parser.mcnp_input.Input([in_str], BT.SURFACE)
        mat = montepy.data_inputs.material.Material(card)
        in_str = "TR1 0 0 1"
        input = montepy.input_parser.mcnp_input.Input([in_str], BT.DATA)
        transform = montepy.data_inputs.transform.Transform(input)
        surf.transform = transform
        cell_num = 1000
        cell = montepy.Cell()
        cell.material = mat
        cell.geometry = -surf
        cell.mass_density = 1.0
        cell.number = cell_num
        cell.universe = problem.universes[350]
        problem.cells.append(cell)
        problem.add_cell_children_to_problem()
        self.assertIn(surf, problem.surfaces)
        self.assertIn(mat, problem.materials)
        self.assertIn(mat, problem.data_inputs)
        self.assertIn(transform, problem.transforms)
        self.assertIn(transform, problem.data_inputs)
        for cell_num in [1, cell_num]:
            print(cell_num)
            if cell_num == 1000:
                with self.assertWarns(LineExpansionWarning):
                    output = problem.cells[cell_num].format_for_mcnp_input((6, 2, 0))
            else:
                output = problem.cells[cell_num].format_for_mcnp_input((6, 2, 0))
            print(output)
            self.assertIn("U=350", "\n".join(output).upper())

    def test_problem_mcnp_version_setter(self):
        problem = copy.deepcopy(self.simple_problem)
        with self.assertRaises(ValueError):
            problem.mcnp_version = (4, 5, 3)
        problem.mcnp_version = (6, 2, 5)
        self.assertEqual(problem.mcnp_version, (6, 2, 5))

    def test_problem_duplicate_surface_remover(self):
        problem = montepy.read_input("tests/inputs/test_redundant_surf.imcnp")
        surfaces = problem.surfaces
        nums = list(problem.surfaces.numbers)
        survivors = (
            nums[0:3] + nums[5:8] + [nums[9]] + nums[11:13] + [nums[13]] + [nums[-2]]
        )
        problem.remove_duplicate_surfaces(1e-4)
        self.assertEqual(list(problem.surfaces.numbers), survivors)
        cell_surf_answer = "-1 3 -6"
        self.assertIn(
            cell_surf_answer, problem.cells[2].format_for_mcnp_input((6, 2, 0))[1]
        )

    def test_surface_periodic(self):
        problem = montepy.read_input("tests/inputs/test_surfaces.imcnp")
        surf = problem.surfaces[1]
        periodic = problem.surfaces[2]
        self.assertEqual(surf.periodic_surface, periodic)
        self.assertIn("1 -2 SO", surf.format_for_mcnp_input((6, 2, 0))[0])
        surf.periodic_surface = problem.surfaces[3]
        self.assertEqual(surf.periodic_surface, problem.surfaces[3])
        del surf.periodic_surface
        self.assertIsNone(surf.periodic_surface)
        with self.assertRaises(TypeError):
            surf.periodic_surface = 5

    def test_surface_transform(self):
        problem = montepy.read_input("tests/inputs/test_surfaces.imcnp")
        surf = problem.surfaces[1]
        transform = problem.data_inputs[0]
        del surf.periodic_surface
        surf.transform = transform
        self.assertEqual(surf.transform, transform)
        self.assertIn("1 1 SO", surf.format_for_mcnp_input((6, 2, 0))[0])
        del surf.transform
        self.assertIsNone(surf.transform)
        self.assertIn("1 SO", surf.format_for_mcnp_input((6, 2, 0))[0])
        with self.assertRaises(TypeError):
            surf.transform = 5

    def test_materials_setter(self):
        problem = copy.deepcopy(self.simple_problem)
        with self.assertRaises(TypeError):
            problem.materials = 5
        with self.assertRaises(TypeError):
            problem.materials = [5]
        size = len(problem.materials)
        problem.materials = list(problem.materials)
        self.assertEqual(len(problem.materials), size)
        problem.materials = problem.materials
        self.assertEqual(len(problem.materials), size)

    def test_reverse_pointers(self):
        problem = self.simple_problem
        complements = list(problem.cells[99].cells_complementing_this)
        self.assertIn(problem.cells[5], complements)
        self.assertEqual(len(complements), 1)
        cells = list(problem.materials[1].cells)
        self.assertIn(problem.cells[1], cells)
        self.assertEqual(len(cells), 1)
        cells = list(problem.surfaces[1005].cells)
        self.assertIn(problem.cells[2], problem.surfaces[1005].cells)
        self.assertEqual(len(cells), 2)

    def test_surface_card_pass_through(self):
        problem = montepy.read_input("tests/inputs/test_surfaces.imcnp")
        surf = problem.surfaces[1]
        # Test input pass through
        answer = ["1 -2 SO -5"]
        self.assertEqual(surf.format_for_mcnp_input((6, 2, 0)), answer)
        # Test changing periodic surface
        new_prob = copy.deepcopy(problem)
        surf = new_prob.surfaces[1]
        new_prob.surfaces[2].number = 5
        self.assertEqual(int(surf.format_for_mcnp_input((6, 2, 0))[0].split()[1]), -5)
        # Test changing transform
        new_prob = copy.deepcopy(problem)
        surf = new_prob.surfaces[4]
        surf.transform.number = 5
        self.assertEqual(int(surf.format_for_mcnp_input((6, 2, 0))[0].split()[1]), 5)
        # test changing surface constants
        new_prob = copy.deepcopy(problem)
        surf = new_prob.surfaces[4]
        surf.location = 2.5
        self.assertEqual(
            float(surf.format_for_mcnp_input((6, 2, 0))[0].split()[-1]), 2.5
        )

    def test_surface_broken_link(self):
        with self.assertRaises(montepy.errors.MalformedInputError):
            montepy.read_input("tests/inputs/test_broken_surf_link.imcnp")
        with self.assertRaises(montepy.errors.MalformedInputError):
            montepy.read_input("tests/inputs/test_broken_transform_link.imcnp")

    def test_material_broken_link(self):
        with self.assertRaises(montepy.errors.BrokenObjectLinkError):
            problem = montepy.read_input("tests/inputs/test_broken_mat_link.imcnp")

    def test_cell_surf_broken_link(self):
        with self.assertRaises(montepy.errors.BrokenObjectLinkError):
            problem = montepy.read_input(
                "tests/inputs/test_broken_cell_surf_link.imcnp"
            )

    def test_cell_complement_broken_link(self):
        with self.assertRaises(montepy.errors.BrokenObjectLinkError):
            problem = montepy.read_input("tests/inputs/test_broken_complement.imcnp")

    def test_cell_card_pass_through(self):
        problem = copy.deepcopy(self.simple_problem)
        cell = problem.cells[1]
        # test input pass-through
        answer = [
            "C cells",
            "c # hidden vertical Do not touch",
            "c",
            "1 1 20",
            "         -1000  $ dollar comment",
            "        imp:n,p=1 U=350 trcl=5 ",
        ]
        self.assertEqual(cell.format_for_mcnp_input((6, 2, 0)), answer)
        # test surface change
        new_prob = copy.deepcopy(problem)
        new_prob.surfaces[1000].number = 5
        cell = new_prob.cells[1]
        output = cell.format_for_mcnp_input((6, 2, 0))
        print(output)
        self.assertEqual(int(output[4].split("$")[0]), -5)
        # test mass density printer
        cell.mass_density = 10.0
        with self.assertWarns(LineExpansionWarning):
            output = cell.format_for_mcnp_input((6, 2, 0))
        print(output)
        self.assertAlmostEqual(float(output[3].split()[2]), -10)
        # ensure that surface number updated
        # Test material number change
        new_prob = copy.deepcopy(problem)
        new_prob.materials[1].number = 5
        cell = new_prob.cells[1]
        output = cell.format_for_mcnp_input((6, 2, 0))
        self.assertEqual(int(output[3].split()[1]), 5)

    def test_thermal_scattering_pass_through(self):
        problem = copy.deepcopy(self.simple_problem)
        mat = problem.materials[3]
        therm = mat.thermal_scattering
        mat.number = 5
        self.assertEqual(
            therm.format_for_mcnp_input((6, 2, 0)), ["MT5 lwtr.23t h-zr.20t h/zr.28t"]
        )

    def test_cutting_comments_parse(self):
        problem = montepy.read_input("tests/inputs/breaking_comments.imcnp")
        comments = problem.cells[1].comments
        self.assertEqual(len(comments), 3)
        self.assertIn("this is a cutting comment", list(comments)[2].contents)
        comments = problem.materials[2].comments
        self.assertEqual(len(comments), 2)

    def test_cutting_comments_print_no_mutate(self):
        problem = montepy.read_input("tests/inputs/breaking_comments.imcnp")
        cell = problem.cells[1]
        output = cell.format_for_mcnp_input((6, 2, 0))
        self.assertEqual(len(output), 5)
        self.assertEqual("c this is a cutting comment", output[3])
        material = problem.materials[2]
        output = material.format_for_mcnp_input((6, 2, 0))
        self.assertEqual(len(output), 5)
        self.assertEqual("c          26057.80c        2.12", output[3])

    def test_cutting_comments_print_mutate(self):
        problem = montepy.read_input("tests/inputs/breaking_comments.imcnp")
        cell = problem.cells[1]
        cell.number = 8
        output = cell.format_for_mcnp_input((6, 2, 0))
        print(output)
        self.assertEqual(len(output), 5)
        self.assertEqual("c this is a cutting comment", output[3])
        material = problem.materials[2]
        material.number = 5
        output = material.format_for_mcnp_input((6, 2, 0))
        print(output)
        self.assertEqual(len(output), 5)
        self.assertEqual("c          26057.80c        2.12", output[3])

    def test_comments_setter(self):
        cell = copy.deepcopy(self.simple_problem.cells[1])
        comment = self.simple_problem.surfaces[1000].comments[0]
        cell.leading_comments = [comment]
        self.assertEqual(cell.comments[0], comment)
        cell.leading_comments = comment
        self.assertEqual(cell.comments[0], comment)
        with self.assertRaises(TypeError):
            cell.leading_comments = [5]
        with self.assertRaises(TypeError):
            cell.leading_comments = 5

    def test_problem_linker(self):
        cell = montepy.Cell()
        with self.assertRaises(TypeError):
            cell.link_to_problem(5)

    def test_importance_parsing(self):
        problem = self.importance_problem
        cell = problem.cells[1]
        self.assertEqual(cell.importance.neutron, 1.0)
        self.assertEqual(cell.importance.photon, 1.0)
        self.assertEqual(cell.importance.electron, 0.0)
        problem = self.simple_problem
        cell = problem.cells[1]
        self.assertEqual(cell.importance.neutron, 1.0)
        self.assertEqual(cell.importance.photon, 1.0)

    def test_importance_format_unmutated(self):
        imp = self.importance_problem.cells._importance
        output = imp.format_for_mcnp_input((6, 2, 0))
        print(output)
        self.assertEqual(len(output), 2)
        self.assertEqual("imp:n,p 1 1 1 0 3", output[0])
        self.assertEqual("imp:e   0 0 0 1 2", output[1])

    def test_importance_format_mutated(self):
        problem = copy.deepcopy(self.importance_problem)
        imp = problem.cells._importance
        problem.cells[1].importance.neutron = 0.5
        with self.assertWarns(LineExpansionWarning):
            output = imp.format_for_mcnp_input((6, 2, 0))
        print(output)
        self.assertEqual(len(output), 3)
        self.assertIn("imp:n 0.5 1 1 0 3", output)

    def test_importance_write_unmutated(self):
        out_file = "test_import_unmute"
        try:
            self.importance_problem.write_to_file(out_file)
            found_np = False
            found_e = False
            with open(out_file, "r") as fh:
                for line in fh:
                    print(line.rstrip())
                    if "imp:n,p 1" in line:
                        found_np = True
                    elif "imp:e" in line:
                        found_e = True
            self.assertTrue(found_np)
            self.assertTrue(found_e)
        finally:
            try:
                os.remove(out_file)
            except FileNotFoundError:
                pass

    def test_importance_write_mutated(self):
        out_file = "test_import_mute"
        problem = copy.deepcopy(self.importance_problem)
        problem.cells[1].importance.neutron = 0.5
        try:
            with self.assertWarns(LineExpansionWarning):
                problem.write_to_file(out_file)
            found_n = False
            found_e = False
            with open(out_file, "r") as fh:
                for line in fh:
                    print(line.rstrip())
                    if "imp:n 0.5" in line:
                        found_n = True
                    elif "imp:e" in line:
                        found_e = True
            self.assertTrue(found_n)
            self.assertTrue(found_e)
        finally:
            try:
                os.remove(out_file)
            except FileNotFoundError:
                pass

    def test_importance_write_cell(self):
        for state in ["no change", "new unmutated cell", "new mutated cell"]:
            out_file = "test_import_cell"
            problem = copy.deepcopy(self.importance_problem)
            if "new" in state:
                cell = copy.deepcopy(problem.cells[5])
                cell.number = 999
                problem.cells.append(cell)
            problem.print_in_data_block["imp"] = False
            try:
                if "new" in state:
                    with self.assertWarns(LineExpansionWarning):
                        problem.write_to_file(out_file)
                else:
                    problem.write_to_file(out_file)
                found_np = False
                found_e = False
                found_data_np = False
                with open(out_file, "r") as fh:
                    for line in fh:
                        print(line.rstrip())
                        if "imp:n,p=1" in line:
                            found_np = True
                        elif "imp:e=1" in line:
                            found_e = True
                        elif "imp:e 1" in line.lower():
                            found_data_np = True
                self.assertTrue(found_np)
                self.assertTrue(found_e)
                self.assertTrue(not found_data_np)
            finally:
                try:
                    os.remove(out_file)
                except FileNotFoundError:
                    pass

    def test_importance_write_data(self):
        out_file = "test_import_data_2"
        problem = copy.deepcopy(self.simple_problem)
        problem.print_in_data_block["imp"] = True
        try:
            problem.write_to_file(out_file)
            found_n = False
            found_p = False
            with open(out_file, "r") as fh:
                for line in fh:
                    print(line.rstrip())
                    if "imp:n 1" in line:
                        found_n = True
                    if "imp:p 1 0.5" in line:
                        found_p = True
            self.assertTrue(found_n)
            self.assertTrue(found_p)
        finally:
            try:
                os.remove(out_file)
            except FileNotFoundError:
                pass

    def test_avoid_blank_cell_modifier_write(self):
        out_file = "test_modifier_data"
        problem = copy.deepcopy(self.simple_problem)
        problem.print_in_data_block["U"] = True
        problem.print_in_data_block["FILL"] = True
        problem.print_in_data_block["LAT"] = True
        problem.cells[5].fill.transform = None
        problem.cells[5].fill.universe = None
        problem.cells[1].universe = problem.universes[0]
        for cell in problem.cells:
            del cell.volume
        problem.cells.allow_mcnp_volume_calc = True
        try:
            problem.write_to_file(out_file)
            found_universe = False
            found_lattice = False
            found_vol = False
            found_fill = False
            with open(out_file, "r") as fh:
                for line in fh:
                    print(line.rstrip())
                    if "U " in line:
                        found_universe = True
                    if "LAT " in line:
                        found_lat = True
                    if "FILL " in line:
                        found_fill = True
                    if "VOL " in line:
                        found_vol = True
            self.assertTrue(not found_universe)
            self.assertTrue(not found_lattice)
            self.assertTrue(not found_vol)
            self.assertTrue(not found_fill)
        finally:
            try:
                os.remove(out_file)
            except FileNotFoundError:
                pass

    def test_set_mode(self):
        problem = copy.deepcopy(self.importance_problem)
        problem.set_mode("e p")
        particles = {Particle.ELECTRON, Particle.PHOTON}
        self.assertEqual(len(problem.mode), 2)
        for part in particles:
            self.assertIn(part, problem.mode)

    def test_set_equal_importance(self):
        problem = copy.deepcopy(self.importance_problem)
        problem.cells.set_equal_importance(0.5, [5])
        for cell in problem.cells:
            for particle in problem.mode:
                if cell.number != 5:
                    print(cell.number, particle)
                    self.assertEqual(cell.importance[particle], 0.5)
        for particle in problem.mode:
            self.assertEqual(problem.cells[5].importance.neutron, 0.0)
        problem.cells.set_equal_importance(0.75, [problem.cells[99]])
        for cell in problem.cells:
            for particle in problem.mode:
                if cell.number != 99:
                    print(cell.number, particle)
                    self.assertEqual(cell.importance[particle], 0.75)
        for particle in problem.mode:
            self.assertEqual(problem.cells[99].importance.neutron, 0.0)
        with self.assertRaises(TypeError):
            problem.cells.set_equal_importance("5", [5])
        with self.assertRaises(ValueError):
            problem.cells.set_equal_importance(-0.5, [5])
        with self.assertRaises(TypeError):
            problem.cells.set_equal_importance(5, "a")
        with self.assertRaises(TypeError):
            problem.cells.set_equal_importance(5, ["a"])

    def test_check_volume_calculated(self):
        self.assertTrue(not self.simple_problem.cells[1].volume_mcnp_calc)

    def test_redundant_volume(self):
        with self.assertRaises(montepy.errors.MalformedInputError):
            montepy.read_input(
                os.path.join("tests", "inputs", "test_vol_redundant.imcnp")
            )

    def test_delete_vol(self):
        problem = copy.deepcopy(self.simple_problem)
        del problem.cells[1].volume
        self.assertTrue(not problem.cells[1].volume_is_set)

    def test_enable_mcnp_vol_calc(self):
        problem = copy.deepcopy(self.simple_problem)
        problem.cells.allow_mcnp_volume_calc = True
        self.assertTrue(problem.cells.allow_mcnp_volume_calc)
        self.assertNotIn("NO", str(problem.cells._volume))
        problem.cells.allow_mcnp_volume_calc = False
        self.assertIn("NO", str(problem.cells._volume))
        with self.assertRaises(TypeError):
            problem.cells.allow_mcnp_volume_calc = 5

    def test_cell_multi_volume(self):
        in_str = "1 0 -1 VOL=1 VOL 5"
        with self.assertRaises(ValueError):
            cell = montepy.Cell(
                Input([in_str], montepy.input_parser.block_type.BlockType.CELL)
            )

    def test_universe_cell_parsing(self):
        problem = self.simple_problem
        answers = [350] + [0] * 4
        for cell, answer in zip(problem.cells, answers):
            print(cell, answer)
            self.assertEqual(cell.universe.number, answer)

    def test_universe_fill_data_parsing(self):
        problem = montepy.read_input(
            os.path.join("tests", "inputs", "test_universe_data.imcnp")
        )
        answers = [350, 0, 0, 1]
        for cell, answer in zip(problem.cells, answers):
            print(cell, answer)
            self.assertEqual(cell.universe.number, answer)
        for cell in problem.cells:
            print(cell)
            if cell.number != 99:
                self.assertTrue(not cell.not_truncated)
            else:
                self.assertTrue(cell.not_truncated)
        self.assertTrue(problem.cells[99].not_truncated)
        answers = [None, None, 350, None, None]
        for cell, answer in zip(problem.cells, answers):
            print(cell.number, cell.fill.universe, answer)
            if answer is None:
                self.assertIsNone(cell.fill.universe)
            else:
                self.assertTrue(cell.fill.universe, answer)

    def test_universe_cells(self):
        answers = {350: [1], 0: [2, 3, 5], 1: [99]}
        problem = montepy.read_input(
            os.path.join("tests", "inputs", "test_universe_data.imcnp")
        )
        for uni_number, cell_answers in answers.items():
            for cell, answer in zip(problem.universes[uni_number].cells, cell_answers):
                self.assertEqual(cell.number, answer)

    def test_cell_not_truncate_setter(self):
        problem = copy.deepcopy(self.simple_problem)
        cell = problem.cells[1]
        cell.not_truncated = True
        self.assertTrue(cell.not_truncated)
        with self.assertRaises(ValueError):
            cell = problem.cells[2]
            cell.not_truncated = True

    def test_universe_setter(self):
        problem = copy.deepcopy(self.simple_problem)
        universe = problem.universes[350]
        cell = problem.cells[3]
        cell.universe = universe
        self.assertEqual(cell.universe, universe)
        self.assertEqual(cell.universe.number, 350)
        with self.assertRaises(TypeError):
            cell.universe = 5

    def test_universe_cell_formatter(self):
        problem = copy.deepcopy(self.simple_problem)
        universe = problem.universes[350]
        cell = problem.cells[3]
        cell.universe = universe
        cell.not_truncated = True
        with self.assertWarns(LineExpansionWarning):
            output = cell.format_for_mcnp_input((6, 2, 0))
        self.assertIn("U=-350", " ".join(output))

    def test_universe_data_formatter(self):
        problem = montepy.read_input(
            os.path.join("tests", "inputs", "test_universe_data.imcnp")
        )
        # test unmutated
        output = problem.cells._universe.format_for_mcnp_input((6, 2, 0))
        print(output)
        self.assertIn("u 350 2J -1", output)
        universe = problem.universes[350]
        # test mutated
        cell = problem.cells[3]
        cell.universe = universe
        cell.not_truncated = True
        with self.assertWarns(LineExpansionWarning):
            output = problem.cells._universe.format_for_mcnp_input((6, 2, 0))
        print(output)
        self.assertIn("u 350 J -350 -1", output)
        # test appending a new mutated cell
        new_cell = copy.deepcopy(cell)
        new_cell.number = 1000
        new_cell.universe = universe
        new_cell.not_truncated = False
        problem.cells.append(new_cell)
        with self.assertWarns(LineExpansionWarning):
            output = problem.cells._universe.format_for_mcnp_input((6, 2, 0))
        print(output)
        self.assertIn("u 350 J -350 -1 J 350 ", output)
        # test appending a new UNmutated cell
        problem = montepy.read_input(
            os.path.join("tests", "inputs", "test_universe_data.imcnp")
        )
        cell = problem.cells[3]
        new_cell = copy.deepcopy(cell)
        new_cell.number = 1000
        new_cell.universe = universe
        new_cell.not_truncated = False
        # lazily implement pulling cell in from other model
        new_cell._mutated = False
        new_cell._universe._mutated = False
        problem.cells.append(new_cell)
        with self.assertWarns(LineExpansionWarning):
            output = problem.cells._universe.format_for_mcnp_input((6, 2, 0))
        print(output)
        self.assertIn("u 350 2J -1 J 350 ", output)

    def test_universe_number_collision(self):
        problem = montepy.read_input(
            os.path.join("tests", "inputs", "test_universe_data.imcnp")
        )
        with self.assertRaises(montepy.errors.NumberConflictError):
            problem.universes[0].number = 350

        with self.assertRaises(ValueError):
            problem.universes[350].number = 0

    def test_universe_repr(self):
        uni = self.simple_problem.universes[0]
        output = repr(uni)
        self.assertIn("Number: 0", output)
        self.assertIn("Problem: set", output)
        self.assertIn("Cells: [2", output)

    def test_lattice_format_data(self):
        problem = copy.deepcopy(self.simple_problem)
        cells = problem.cells
        cells[1].lattice = 1
        cells[99].lattice = 2
        answer = "LAT 1 2J 2"
        output = cells._lattice.format_for_mcnp_input((6, 2, 0))
        self.assertIn(answer, output[0])

    def test_lattice_push_to_cells(self):
        problem = copy.deepcopy(self.simple_problem)
        lattices = [1, 2, Jump(), Jump()]
        card = Input(
            ["Lat " + " ".join(list(map(str, lattices)))],
            montepy.input_parser.block_type.BlockType.DATA,
        )
        lattice = montepy.data_inputs.lattice_input.LatticeInput(card)
        lattice.link_to_problem(problem)
        lattice.push_to_cells()
        for cell, answer in zip(problem.cells, lattices):
            print(cell.number, answer)
            if isinstance(answer, int):
                self.assertEqual(cell.lattice.value, answer)
            else:
                self.assertIsNone(cell.lattice)

    def test_universe_problem_parsing(self):
        problem = self.universe_problem
        for cell in problem.cells:
            if cell.number == 1:
                self.assertEqual(cell.universe.number, 1)
            else:
                self.assertEqual(cell.universe.number, 0)

    def test_importance_end_repeat(self):
        problem = copy.deepcopy(self.universe_problem)
        for cell in problem.cells:
            if cell.number in {99, 5}:
                cell.importance.photon = 1.0
            else:
                cell.importance.photon = 0.0
        problem.print_in_data_block["IMP"] = True
        output = problem.cells._importance.format_for_mcnp_input((6, 2, 0))
        # OG value was 0.5 so 0.0 is correct.
        self.assertIn("imp:p 0 0.0", output)

    def test_fill_parsing(self):
        problem = self.universe_problem
        answers = [None, np.array([[[1], [0]], [[0], [1]]]), None, 1, 1]
        for cell, answer in zip(problem.cells, answers):
            if answer is None:
                self.assertIsNone(cell.fill.universe)
            elif isinstance(answer, np.ndarray):
                self.assertTrue(cell.fill.multiple_universes)
                self.assertTrue(
                    (cell.fill.min_index == np.array([0.0, 0.0, 0.0])).all()
                )
                self.assertTrue(
                    (cell.fill.max_index == np.array([1.0, 1.0, 0.0])).all()
                )
                self.assertEqual(cell.fill.universes[0][0][0].number, answer[0][0][0])
                self.assertEqual(cell.fill.universes[1][1][0].number, answer[1][1][0])
                self.assertEqual(cell.fill.transform, problem.transforms[5])
            else:
                self.assertEqual(cell.fill.universe.number, answer)

    def test_fill_transform_setter(self):
        problem = copy.deepcopy(self.universe_problem)
        transform = problem.transforms[5]
        cell = problem.cells[5]
        cell.fill.transform = transform
        self.assertEqual(cell.fill.transform, transform)
        self.assertTrue(not cell.fill.hidden_transform)
        cell.fill.transform = None
        self.assertIsNone(cell.fill.transform)
        with self.assertRaises(TypeError):
            cell.fill.transform = "hi"
        cell.fill.transform = transform
        del cell.fill.transform
        self.assertIsNone(cell.fill.transform)

    def test_fill_cell_format(self):
        problem = copy.deepcopy(self.universe_problem)
        fill = problem.cells[5].fill
        output = fill.format_for_mcnp_input((6, 2, 0))
        answer = "fill=1 (1 0.0 0.0)"
        self.assertEqual(output[0], answer)
        # test *fill
        fill.transform.is_in_degrees = True
        output = fill.format_for_mcnp_input((6, 2, 0))
        answer = "*fill=1 (1 0.0 0.0)"
        self.assertEqual(output[0], answer)
        # test changing the transform
        fill.transform.displacement_vector[0] = 2.0
        output = fill.format_for_mcnp_input((6, 2, 0))
        self.assertEqual(output[0], "*fill=1 (2 0.0 0.0)")
        # test without transform
        fill.transform = None
        answer = "fill=1 "
        output = fill.format_for_mcnp_input((6, 2, 0))
        self.assertEqual(output[0], answer)
        # test with no fill
        fill.universe = None
        output = fill.format_for_mcnp_input((6, 2, 0))
        self.assertEqual(len(output), 0)
        # test with complex universe lattice fill
        fill = problem.cells[2].fill
        output = fill.format_for_mcnp_input((6, 2, 0))
        answers = ["fill= 0:1 0:1 0:0 1 0 0 1 (5)"]
        self.assertEqual(output, answers)
        problem.print_in_data_block["FILL"] = True
        # test that complex fill is not printed in data block
        with self.assertRaises(ValueError):
            output = problem.cells._fill.format_for_mcnp_input((6, 2, 0))
        problem = copy.deepcopy(self.simple_problem)
        problem.cells[5].fill.transform = None
        problem.print_in_data_block["FILL"] = True
        output = problem.cells._fill.format_for_mcnp_input((6, 2, 0))
        self.assertEqual(output, ["FILL 4J 350 "])

    def test_universe_cells_claim(self):
        problem = copy.deepcopy(self.universe_problem)
        universe = problem.universes[1]
        universe.claim(problem.cells[2])
        self.assertEqual(problem.cells[2].universe, universe)
        universe = montepy.Universe(5)
        problem.universes.append(universe)
        universe.claim(problem.cells)
        for cell in problem.cells:
            self.assertEqual(cell.universe, universe)
        with self.assertRaises(TypeError):
            universe.claim("hi")
        with self.assertRaises(TypeError):
            universe.claim(["hi"])

    def test_universe_cells(self):
        problem = self.universe_problem
        answers = [1]
        universe = problem.universes[1]
        self.assertEqual(len(answers), len(list(universe.cells)))
        for cell, answer in zip(universe.cells, answers):
            self.assertEqual(cell.number, answer)

    def test_data_print_control_str(self):
        self.assertEqual(
            str(self.simple_problem.print_in_data_block),
            "Print data in data block: {'imp': False, 'u': False, 'fill': False, 'vol': True}",
        )

    def test_cell_validator(self):
        problem = copy.deepcopy(self.simple_problem)
        cell = problem.cells[1]
        del cell.mass_density
        with self.assertRaises(montepy.errors.IllegalState):
            cell.validate()
        cell = montepy.Cell()
        # test no geometry at all
        with self.assertRaises(montepy.errors.IllegalState):
            cell.validate()
        surf = problem.surfaces[1000]
        cell.surfaces.append(surf)
        # test surface added but geomtry not defined
        with self.assertRaises(montepy.errors.IllegalState):
            cell.validate()

    def test_importance_rewrite(self):
        out_file = "test_import_data_1"
        problem = copy.deepcopy(self.simple_problem)
        problem.print_in_data_block["imp"] = True
        try:
            problem.write_to_file(out_file)
            problem = montepy.read_input(out_file)
            os.remove(out_file)
            problem.print_in_data_block["imp"] = False
            problem.write_to_file(out_file)
            found_n = False
            found_p = False
            found_vol = False
            with open(out_file, "r") as fh:
                for line in fh:
                    print(line.rstrip())
                    if "IMP:N 1 2R" in line:
                        found_n = True
                    if "IMP:P 1 0.5" in line:
                        found_p = True
                    if "vol NO 2J 1 1.5 J" in line:
                        found_vol = True
            self.assertTrue(not found_n)
            self.assertTrue(not found_p)
            self.assertTrue(found_vol)
        finally:
            try:
                os.remove(out_file)
            except FileNotFoundError:
                pass

    def test_parsing_error(self):
        in_file = os.path.join("tests", "inputs", "test_bad_syntax.imcnp")
        with self.assertRaises(montepy.errors.ParsingError):
            problem = montepy.read_input(in_file)

    def test_leading_comments(self):
        cell = copy.deepcopy(self.simple_problem.cells[1])
        leading_comments = cell.leading_comments
        self.assertIn("cells", leading_comments[0].contents)
        del cell.leading_comments
        self.assertFalse(cell.leading_comments)
        cell.leading_comments = leading_comments[0:1]
        self.assertIn("cells", cell.leading_comments[0].contents)
        self.assertEqual(len(cell.leading_comments), 1)

    def test_wrap_warning(self):
        cell = copy.deepcopy(self.simple_problem.cells[1])
        with self.assertWarns(montepy.errors.LineExpansionWarning):
            output = cell.wrap_string_for_mcnp("h" * 130, (6, 2, 0), True)
            self.assertEqual(len(output), 2)
        output = cell.wrap_string_for_mcnp("h" * 127, (6, 2, 0), True)
        self.assertEqual(len(output), 1)

    def test_expansion_warning_crash(self):
        problem = copy.deepcopy(self.simple_problem)
        cell = problem.cells[99]
        cell.material = problem.materials[1]
        cell.mass_density = 10.0
        problem.materials[1].number = 987654321
        problem.surfaces[1010].number = 123456789
        out = "bad_warning.imcnp"
        try:
            with self.assertWarns(montepy.errors.LineExpansionWarning):
                problem.write_to_file(out)
        finally:
            try:
                os.remove(out)
            except FileNotFoundError:
                pass

    def test_alternate_encoding(self):
        with self.assertRaises(UnicodeDecodeError):
            problem = montepy.read_input(
                os.path.join("tests", "inputs", "bad_encoding.imcnp"), replace=False
            )
        problem = montepy.read_input(
            os.path.join("tests", "inputs", "bad_encoding.imcnp"), replace=True
        )

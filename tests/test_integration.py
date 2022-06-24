import copy
import unittest
from unittest import TestCase, expectedFailure
import os

import mcnpy
from mcnpy.data_cards import material, thermal_scattering
from mcnpy.input_parser.mcnp_input import Card, Comment, Message, Title, ReadCard


class testFullFileIntegration(TestCase):
    def setUp(self):
        file_name = "tests/inputs/test.imcnp"
        self.simple_problem = mcnpy.read_input(file_name)

    def test_original_input(self):
        cell_order = [Message, Title, Comment]
        cell_order += [Card] * 5 + [Comment]
        cell_order += [Comment] + [Card] * 3
        cell_order += [Comment, Card] * 3
        cell_order += [Card, Comment] + [Card] * 5
        for i, input_ob in enumerate(self.simple_problem.original_inputs):
            self.assertIsInstance(input_ob, cell_order[i])

    def test_original_input_dos(self):
        problem = mcnpy.read_input(os.path.join("tests", "inputs", "test_dos.imcnp"))
        cell_order = [Message, Title, Comment]
        cell_order += [Card] * 5 + [Comment]
        cell_order += [Comment] + [Card] * 3
        cell_order += [Comment, Card] * 3
        cell_order += [Card, Comment] + [Card] * 5
        for i, input_ob in enumerate(problem.original_inputs):
            self.assertIsInstance(input_ob, cell_order[i])

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
        MT = thermal_scattering.ThermalScatteringLaw
        cards = [M, M, M, MT, "KSRC", "KCODE", "PHYS:P", "MODE"]
        for i, card in enumerate(self.simple_problem.data_cards):
            if isinstance(cards[i], str):
                self.assertEqual(card.words[0].upper(), cards[i])
            else:
                self.assertIsInstance(card, cards[i])

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
        problem = mcnpy.read_input("tests/inputs/testReadRec1.imcnp")
        self.assertEqual(len(problem.cells), 1)
        self.assertEqual(len(problem.surfaces), 1)
        self.assertEqual(len(problem.data_cards), 1)

    def test_problem_str(self):
        output = str(self.simple_problem)
        answer_part = [
            "MCNP problem for: tests/inputs/test.imcnp",
            "MESSAGE:\nthis is a message",
            "it should show up at the beginning",
            "foo",
        ]
        for line in answer_part:
            self.assertIn(line, output)

    def test_write_to_file(self):
        out = "foo.imcnp"
        try:
            self.simple_problem.write_to_file(out)
            test_problem = mcnpy.read_input(out)
            for i, cell in enumerate(self.simple_problem.cells):
                num = cell.number
                self.assertEqual(num, test_problem.cells[num].number)
            for i, surf in enumerate(self.simple_problem.surfaces):
                num = surf.number
                self.assertEqual(surf.number, test_problem.surfaces[num].number)
            for i, data in enumerate(self.simple_problem.data_cards):
                if isinstance(data, material.Material):
                    self.assertEqual(data.number, test_problem.data_cards[i].number)
                else:
                    self.assertEqual(data.words, test_problem.data_cards[i].words)
        finally:
            if os.path.exists(out):
                os.remove(out)

    def test_cell_material_setter(self):
        cell = self.simple_problem.cells[1]
        mat = self.simple_problem.materials[2]
        cell.material = mat
        self.assertEqual(cell.material, mat)
        cell.material = None
        self.assertIsNone(cell.material)
        with self.assertRaises(TypeError):
            cell.material = 5

    def test_cell_surfaces_setter(self):
        cell = self.simple_problem.cells[1]
        surfaces = self.simple_problem.surfaces
        cell.surfaces = surfaces
        self.assertEqual(cell.surfaces, surfaces)

    def test_cell_complements_setter(self):
        cell = self.simple_problem.cells[1]
        complement_numbers = list(self.simple_problem.cells.numbers)[1:]
        complements = []
        for num in complement_numbers:
            complements.append(self.simple_problem.cells[num])
        with self.assertRaises(TypeError):
            cell.complements = 5
        with self.assertRaises(TypeError):
            cell.complements = [5, 6]
        with self.assertRaises(TypeError):
            cell.complements.append(5)
        cell.complements = complements
        self.assertEqual(list(cell.complements), complements)

    def test_problem_cells_setter(self):
        problem = copy.deepcopy(self.simple_problem)
        cells = self.simple_problem.cells
        cells.remove(cells[1])
        with self.assertRaises(TypeError):
            problem.cells = 5
        with self.assertRaises(TypeError):
            problem.cells = [5]
        with self.assertRaises(TypeError):
            problem.cells.append(5)
        problem.cells = cells
        self.assertEqual(problem.cells, cells)
        problem.cells = list(cells)
        self.assertEqual(problem.cells[2], cells[2])

    def test_problem_test_setter(self):
        problem = copy.copy(self.simple_problem)
        sample_title = "This is a title"
        problem.title = sample_title
        self.assertEqual(problem.title.title, sample_title)
        with self.assertRaises(AssertionError):
            problem.title = 5

    def test_problem_children_adder(self):
        problem = copy.copy(self.simple_problem)
        BT = mcnpy.input_parser.block_type.BlockType
        in_str = "5 SO 5.0"
        card = mcnpy.input_parser.mcnp_input.Card([in_str], BT.SURFACE)
        surf = mcnpy.surfaces.surface_builder.surface_builder(card)
        in_str = "M5 6000.70c 1.0"
        card = mcnpy.input_parser.mcnp_input.Card([in_str], BT.SURFACE)
        mat = mcnpy.data_cards.material.Material(card, None)
        cell = mcnpy.Cell()
        cell.material = mat
        cell.surfaces = [surf]
        cell.density = (1.0, False)
        problem.cells.append(cell)
        problem.add_cell_children_to_problem()
        self.assertIn(surf, problem.surfaces)
        self.assertIn(mat, problem.materials)
        self.assertIn(mat, problem.data_cards)

    def test_problem_mcnp_version_setter(self):
        problem = copy.copy(self.simple_problem)
        with self.assertRaises(AssertionError):
            problem.mcnp_version = (4, 5, 3)
        problem.mcnp_version = (6, 2, 5)
        self.assertEqual(problem.mcnp_version, (6, 2, 5))

    def test_problem_duplicate_surface_remover(self):
        problem = mcnpy.read_input("tests/inputs/test_redundant_surf.imcnp")
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
        problem = mcnpy.read_input("tests/inputs/test_surfaces.imcnp")
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
        problem = mcnpy.read_input("tests/inputs/test_surfaces.imcnp")
        surf = problem.surfaces[1]
        transform = problem.data_cards[0]
        del surf.periodic_surface
        surf.transform = transform
        self.assertEqual(surf.transform, transform)
        self.assertIn("1 1 SO", surf.format_for_mcnp_input((6, 2, 0))[0])
        del surf.transform
        self.assertIsNone(surf.transform)

    def test_materials_setter(self):
        problem = copy.deepcopy(self.simple_problem)
        with self.assertRaises(AssertionError):
            problem.materials = 5
        with self.assertRaises(AssertionError):
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
        problem = mcnpy.read_input("tests/inputs/test_surfaces.imcnp")
        surf = problem.surfaces[1]
        # Test card pass through
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
        with self.assertRaises(mcnpy.errors.MalformedInputError):
            mcnpy.read_input("tests/inputs/test_broken_surf_link.imcnp")
        with self.assertRaises(mcnpy.errors.MalformedInputError):
            mcnpy.read_input("tests/inputs/test_broken_transform_link.imcnp")

    def test_material_broken_link(self):
        with self.assertRaises(mcnpy.errors.BrokenObjectLinkError):
            problem = mcnpy.read_input("tests/inputs/test_broken_mat_link.imcnp")

    def test_cell_surf_broken_link(self):
        with self.assertRaises(mcnpy.errors.BrokenObjectLinkError):
            problem = mcnpy.read_input("tests/inputs/test_broken_cell_surf_link.imcnp")

    def test_cell_complement_broken_link(self):
        with self.assertRaises(mcnpy.errors.BrokenObjectLinkError):
            problem = mcnpy.read_input("tests/inputs/test_broken_complement.imcnp")

    def test_cell_card_pass_through(self):
        problem = copy.deepcopy(self.simple_problem)
        cell = problem.cells[1]
        # test card pass-through
        answer = [
            "C cells",
            "C ",
            "1 1 20",
            "         -1000",
            "     imp:n,p=1 U=350 trcl=5",
        ]
        self.assertEqual(cell.format_for_mcnp_input((6, 2, 0)), answer)
        # test surface change
        new_prob = copy.deepcopy(problem)
        new_prob.surfaces[1000].number = 5
        cell = new_prob.cells[1]
        output = cell.format_for_mcnp_input((6, 2, 0))
        self.assertEqual(int(output[3]), -5)
        # test mass density printer
        cell.density = (10.0, False)
        output = cell.format_for_mcnp_input((6, 2, 0))
        self.assertAlmostEqual(float(output[2].split()[2]), -10)
        # ensure that surface number updated
        # Test material number change
        new_prob = copy.deepcopy(problem)
        new_prob.materials[1].number = 5
        cell = new_prob.cells[1]
        output = cell.format_for_mcnp_input((6, 2, 0))
        self.assertEqual(int(output[2].split()[1]), 5)

    def test_cell_fill_formatting(self):
        cell = copy.deepcopy(self.simple_problem.cells[1])
        cell._mutated = True
        cell.parameters["FILL"] = ["5", "(4)"]
        output = cell.format_for_mcnp_input((6, 2, 0))
        self.assertIn("FILL=5 (4)", output[4])

    def test_thermal_scattering_pass_through(self):
        problem = copy.deepcopy(self.simple_problem)
        mat = problem.materials[3]
        therm = mat.thermal_scattering
        mat.number = 5
        self.assertEqual(therm.format_for_mcnp_input((6, 2, 0)), ["MT5 lwtr.23t"])

    def test_cutting_comments_parse(self):
        problem = mcnpy.read_input("tests/inputs/breaking_comments.imcnp")
        comments = problem.cells[1].comments
        self.assertEqual(len(comments), 2)
        self.assertIn("this is a cutting comment", comments[1].lines[0])
        comments = problem.materials[2].comments
        self.assertEqual(len(comments), 2)

    def test_cutting_comments_print_no_mutate(self):
        problem = mcnpy.read_input("tests/inputs/breaking_comments.imcnp")
        cell = problem.cells[1]
        output = cell.format_for_mcnp_input((6, 2, 0))
        self.assertEqual(len(output), 5)
        self.assertEqual("C this is a cutting comment", output[3])
        material = problem.materials[2]
        output = material.format_for_mcnp_input((6, 2, 0))
        self.assertEqual(len(output), 5)
        self.assertEqual("C          26057.80c        2.12", output[3])

    def test_cutting_comments_print_mutate(self):
        problem = mcnpy.read_input("tests/inputs/breaking_comments.imcnp")
        cell = problem.cells[1]
        cell.number = 8
        output = cell.format_for_mcnp_input((6, 2, 0))
        self.assertEqual(len(output), 5)
        self.assertEqual("C this is a cutting comment", output[1])
        material = problem.materials[2]
        material.number = 5
        output = material.format_for_mcnp_input((6, 2, 0))
        self.assertEqual(len(output), 5)
        self.assertEqual("C          26057.80c        2.12", output[1])

    def test_comments_setter(self):
        cell = copy.deepcopy(self.simple_problem.cells[1])
        comment = self.simple_problem.surfaces[1000].comments[0]
        cell.comments = [comment]
        self.assertEqual(cell.comments[0], comment)
        with self.assertRaises(AssertionError):
            cell.comments = comment
        with self.assertRaises(AssertionError):
            cell.comments = [5]
        with self.assertRaises(AssertionError):
            cell.comments = 5

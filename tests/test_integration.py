import copy
from unittest import TestCase
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

    def test_material_parsing(self):
        mat_numbers = [1, 2, 3]
        for i, mat in enumerate(self.simple_problem.materials):
            self.assertEqual(mat.material_number, mat_numbers[i])

    def test_surface_parsing(self):
        surf_numbers = [1000, 1005, 1010]
        for i, surf in enumerate(self.simple_problem.surfaces):
            self.assertEqual(surf.surface_number, surf_numbers[i])

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
        mat_answer = [mats[0], mats[1], mats[2], None, None]
        surfs = self.simple_problem.surfaces
        surf_answer = [{surfs[0]}, {surfs[1]}, set(surfs), {surfs[2]}, set()]
        cells = self.simple_problem.cells
        complements = [set()] * 4 + [{cells[3]}]
        for i, cell in enumerate(self.simple_problem.cells):
            self.assertEqual(cell.cell_number, cell_numbers[i])
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
                self.assertEqual(cell.cell_number, test_problem.cells[i].cell_number)
            for i, surf in enumerate(self.simple_problem.surfaces):
                self.assertEqual(
                    surf.surface_number, test_problem.surfaces[i].surface_number
                )
            for i, data in enumerate(self.simple_problem.data_cards):
                if isinstance(data, material.Material):
                    self.assertEqual(
                        data.material_number, test_problem.data_cards[i].material_number
                    )
                else:
                    self.assertEqual(data.words, test_problem.data_cards[i].words)
        finally:
            if os.path.exists(out):
                os.remove(out)

    def test_cell_material_setter(self):
        cell = self.simple_problem.cells[0]
        mat = self.simple_problem.materials[0]
        cell.material = mat
        self.assertEqual(cell.material, mat)
        cell.material = None
        self.assertIsNone(cell.material)
        with self.assertRaises(AssertionError):
            cell.material = 5

    def test_cell_surfaces_setter(self):
        cell = self.simple_problem.cells[0]
        surfaces = self.simple_problem.surfaces
        cell.surfaces = surfaces
        self.assertEqual(cell.surfaces, surfaces)

    def test_cell_complements_setter(self):
        cell = self.simple_problem.cells[0]
        complements = self.simple_problem.cells[1:]
        cell.complements = complements
        self.assertEqual(cell.complements, complements)

    def test_problem_cells_setter(self):
        problem = copy.copy(self.simple_problem)
        cells = self.simple_problem.cells[1:]
        problem.cells = cells
        self.assertEqual(problem.cells, cells)

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
        card = mcnpy.input_parser.mcnp_input.Card(BT.SURFACE, ["5", "SO", "5.0"])
        surf = mcnpy.surfaces.surface_builder.surface_builder(card)
        card = mcnpy.input_parser.mcnp_input.Card(BT.DATA, ["M1", "6000.70c", "1.0"])
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
            problem.mcnp_version = (5, 5, 3)
        problem.mcnp_version = (6, 2, 5)
        self.assertEqual(problem.mcnp_version, (6, 2, 5))

    def test_problem_duplicate_surface_remover(self):
        problem = mcnpy.read_input("tests/inputs/test_redundant_surf.imcnp")
        surfaces = problem.surfaces
        survivors = (
            surfaces[0:3]
            + surfaces[5:8]
            + [surfaces[9]]
            + surfaces[11:13]
            + [surfaces[13]]
            + [surfaces[-2]]
        )
        problem.remove_duplicate_surfaces(1e-4)
        self.assertEqual(problem.surfaces, survivors)
        cell_surf_answer = "-1 3 -6"
        self.assertIn(
            cell_surf_answer, problem.cells[1].format_for_mcnp_input((6, 2, 0))[1]
        )

    def test_surface_periodic(self):
        problem = mcnpy.read_input("tests/inputs/test_surfaces.imcnp")
        surf = problem.surfaces[0]
        periodic = problem.surfaces[1]
        self.assertEqual(surf.periodic_surface, periodic)
        self.assertIn("1 -2 SO", surf.format_for_mcnp_input((6, 2, 0))[0])
        surf.periodic_surface = problem.surfaces[2]
        self.assertEqual(surf.periodic_surface, problem.surfaces[2])
        del surf.periodic_surface
        self.assertIsNone(surf.periodic_surface)
        with self.assertRaises(AssertionError):
            surf.periodic_surface = 5

    def test_surface_transform(self):
        problem = mcnpy.read_input("tests/inputs/test_surfaces.imcnp")
        surf = problem.surfaces[0]
        transform = problem.data_cards[0]
        del surf.periodic_surface
        surf.transform = transform
        self.assertEqual(surf.transform, transform)
        self.assertIn("1 1 SO", surf.format_for_mcnp_input((6, 2, 0))[0])
        del surf.transform
        self.assertIsNone(surf.transform)

    def test_surface_broken_link(self):
        with self.assertRaises(mcnpy.errors.MalformedInputError):
            mcnpy.read_input("tests/inputs/test_broken_surf_link.imcnp")
        with self.assertRaises(mcnpy.errors.MalformedInputError):
            mcnpy.read_input("tests/inputs/test_broken_transform_link.imcnp")

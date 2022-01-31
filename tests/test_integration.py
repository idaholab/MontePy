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
        cell_order += [Card] * 4 + [Comment]
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
        cell_numbers = [1, 2, 3, 99]
        mats = self.simple_problem.materials
        mat_answer = [mats[0], mats[1], mats[2], None]
        surfs = self.simple_problem.surfaces
        surf_answer = [{surfs[0]}, {surfs[1]}, set(surfs), {surfs[2]}]
        for i, cell in enumerate(self.simple_problem.cells):
            self.assertEqual(cell.cell_number, cell_numbers[i])
            self.assertEqual(cell.material, mat_answer[i])
            surfaces = set(cell.surfaces)
            self.assertTrue(surfaces.union(surf_answer[i]) == surfaces)

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
            "MESSAGE: this is a message",
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
                self.assertEqual(cell, test_problem.cells[i])
            for i, surf in enumerate(self.simple_problem.surfaces):
                self.assertEqual(surf, test_problem.surfaces[i])
            for i, data in enumerate(self.simple_problem.data_cards):
                self.assertEqual(data, test_problem.data_cards[i])
        finally:
            if os.path.exists(out):
                os.remove(out)
         

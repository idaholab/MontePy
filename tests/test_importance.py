from unittest import TestCase
import mcnpy
from mcnpy.cell import Cell
from mcnpy.data_cards.importance import Importance
from mcnpy.errors import *
from mcnpy.input_parser import mcnp_input, block_type
import os


class TestImportance(TestCase):
    def test_importance_init_cell(self):
        # test_normal cell init
        in_str = "1 0 -1 IMP:N,P=1"
        card = mcnp_input.Card([in_str], block_type.BlockType.CELL)
        cell = Cell(card)
        self.assertEqual(cell.importance.neutron, 1.0)
        self.assertEqual(cell.importance.photon, 1.0)
        self.assertEqual(cell.importance.alpha_particle, 0.0)
        self.assertIsNone(cell.importance.all)
        self.assertTrue(cell.importance.in_cell_block)
        # test non-number imp
        in_str = "1 0 -1 IMP:N,P=h"
        card = mcnp_input.Card([in_str], block_type.BlockType.CELL)
        with self.assertRaises(ValueError):
            cell = Cell(card)
        # test negative imp
        in_str = "1 0 -1 IMP:N,P=-2"
        card = mcnp_input.Card([in_str], block_type.BlockType.CELL)
        with self.assertRaises(ValueError):
            cell = Cell(card)

    def test_importance_init_data(self):
        in_str = "IMP:N,P 1 0"
        card = mcnp_input.Card([in_str], block_type.BlockType.CELL)
        imp = Importance(card)
        self.assertEqual(imp.neutron, [1.0, 0.0])
        self.assertEqual(imp.photon, [1.0, 0.0])
        # test non-number imp
        in_str = "IMP:N,P 1 h"
        card = mcnp_input.Card([in_str], block_type.BlockType.CELL)
        with self.assertRaises(ValueError):
            imp = Importance(card)
        # test negative
        in_str = "IMP:N,P 1 -2"
        card = mcnp_input.Card([in_str], block_type.BlockType.CELL)
        with self.assertRaises(ValueError):
            imp = Importance(card)
        # test bad in_cell_block
        in_str = "IMP:N,P 1 2"
        card = mcnp_input.Card([in_str], block_type.BlockType.CELL)
        with self.assertRaises(TypeError):
            imp = Importance(card, in_cell_block=1)
        # test bad key
        in_str = "IMP:N,P 1 2"
        card = mcnp_input.Card([in_str], block_type.BlockType.CELL)
        with self.assertRaises(TypeError):
            imp = Importance(card, key=1)
        # test bad value
        in_str = "IMP:N,P 1 2"
        card = mcnp_input.Card([in_str], block_type.BlockType.CELL)
        with self.assertRaises(TypeError):
            imp = Importance(card, value=1)

    def test_importance_iter_getter_in(self):
        in_str = "1 0 -1 IMP:N,P=1"
        card = mcnp_input.Card([in_str], block_type.BlockType.CELL)
        cell = Cell(card)
        imp = cell.importance
        particles = [mcnpy.particle.Particle.NEUTRON, mcnpy.particle.Particle.PHOTON]
        for particle in imp:
            self.assertIn(particle, particles)
            self.assertAlmostEqual(imp[particle], 1.0)
        for particle in particles:
            self.assertIn(particle, imp)
        with self.assertRaises(TypeError):
            imp["hi"]

    def test_importance_all_setter(self):
        in_str = "1 0 -1 IMP:N,P=1"
        card = mcnp_input.Card([in_str], block_type.BlockType.CELL)
        cell = Cell(card)
        problem = mcnpy.mcnp_problem.MCNP_Problem("foo")
        problem.mode.add(mcnpy.particle.Particle.NEUTRON)
        problem.mode.add(mcnpy.particle.Particle.PHOTON)
        imp = cell.importance
        cell.link_to_problem(problem)
        imp.all = 2.0
        self.assertAlmostEqual(imp.neutron, 2.0)
        self.assertAlmostEqual(imp.photon, 2.0)
        # try wrong type
        with self.assertRaises(TypeError):
            imp.all = "h"
        # try negative type
        with self.assertRaises(ValueError):
            imp.all = -2.0

    def test_importance_setter(self):
        in_str = "1 0 -1 IMP:N,P=1"
        card = mcnp_input.Card([in_str], block_type.BlockType.CELL)
        cell = Cell(card)
        cell.importance.neutron = 2.5
        self.assertEqual(cell.importance.neutron, 2.5)
        problem = mcnpy.mcnp_problem.MCNP_Problem("foo")
        cell.link_to_problem(problem)
        # test problem mode enforcement
        with self.assertRaises(ValueError):
            cell.importance.photon = 1.0
        # test wrong type
        with self.assertRaises(TypeError):
            cell.importance.neutron = "h"
        # test negative
        with self.assertRaises(ValueError):
            cell.importance.neutron = -0.5

    def test_importance_deleter(self):
        in_str = "1 0 -1 IMP:N,P=1"
        card = mcnp_input.Card([in_str], block_type.BlockType.CELL)
        cell = Cell(card)
        del cell.importance.neutron
        self.assertAlmostEqual(cell.importance.neutron, 0.0)

    def test_importance_merge(self):
        in_str = "IMP:N,P 1 0"
        card = mcnp_input.Card([in_str], block_type.BlockType.CELL)
        imp1 = Importance(card)
        in_str = "IMP:E 0 0"
        card = mcnp_input.Card([in_str], block_type.BlockType.CELL)
        imp2 = Importance(card)
        imp1.merge(imp2)
        self.assertEqual(imp1.neutron, [1.0, 0.0])
        self.assertEqual(imp1.electron, [0.0, 0.0])
        # test bad type
        with self.assertRaises(TypeError):
            imp1.merge("hi")
        # test bad block type
        in_str = "1 0 -1 IMP:N,P=1"
        card = mcnp_input.Card([in_str], block_type.BlockType.CELL)
        cell = Cell(card)
        with self.assertRaises(ValueError):
            imp1.merge(cell.importance)
        in_str = "IMP:P 0 0"
        card = mcnp_input.Card([in_str], block_type.BlockType.CELL)
        imp2 = Importance(card)
        with self.assertRaises(MalformedInputError):
            imp1.merge(imp2)

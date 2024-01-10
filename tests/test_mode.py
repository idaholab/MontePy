# Copyright 2024, Battelle Energy Alliance, LLC All Rights Reserved.
from unittest import TestCase

import montepy
from montepy.data_inputs.mode import Mode
from montepy.input_parser.mcnp_input import Input
from montepy.input_parser.block_type import BlockType
from montepy.particle import Particle


class TestMode(TestCase):
    def test_mode_init(self):
        in_str = "mode n p"
        mode = Mode(Input([in_str], BlockType.CELL))
        self.assertEqual(len(mode), 2)
        self.assertIn(Particle.NEUTRON, mode)
        self.assertIn(Particle.PHOTON, mode.particles)
        # test bad input
        in_str = "kcode"
        with self.assertRaises(montepy.errors.MalformedInputError):
            mode = Mode(Input([in_str], BlockType.CELL))
        in_str = "mode 1"
        with self.assertRaises(TypeError):
            mode = Mode(Input([in_str], BlockType.CELL))
        mode = Mode()
        self.assertEqual(len(mode), 1)
        self.assertIn(Particle.NEUTRON, mode)

    def test_mode_add(self):
        mode = Mode()
        with self.assertRaises(TypeError):
            mode.add(5)
        with self.assertRaises(ValueError):
            mode.add("5")
        mode.add("p")
        self.assertIn(Particle.PHOTON, mode)
        mode.add(Particle.NEGATIVE_MUON)
        self.assertIn(Particle.NEGATIVE_MUON, mode)
        self.assertEqual(len(mode), 3)

    def test_mode_remove(self):
        mode = Mode()
        with self.assertRaises(TypeError):
            mode.remove(5)
        with self.assertRaises(ValueError):
            mode.remove("5")
        mode.remove("n")
        self.assertEqual(len(mode), 0)
        self.assertTrue(Particle.NEUTRON not in mode)
        mode.add("p")
        # force update of syntax tree
        output = mode.format_for_mcnp_input((6, 2, 0))
        mode.remove(Particle.PHOTON)
        self.assertEqual(len(mode), 0)
        self.assertTrue(Particle.PHOTON not in mode)
        output = mode.format_for_mcnp_input((6, 2, 0))
        self.assertNotIn("p", output)
        self.assertNotIn("P", output)

    def test_mode_iter(self):
        mode = Mode()
        mode.add("p")
        parts = [Particle.NEUTRON, Particle.PHOTON]
        i = 0
        for particle in mode:
            self.assertIn(particle, parts)
            i += 1
        self.assertEqual(i, 2)

    def test_mode_format_input(self):
        mode = Mode()
        mode.add("e")
        mode.add("p")
        output = mode.format_for_mcnp_input((6, 2, 0))
        print(output)
        self.assertEqual(len(output), 1)
        self.assertIn("MODE", output[0])
        self.assertIn("N", output[0])
        self.assertIn("P", output[0])
        self.assertIn("E", output[0])

    def test_set_mode(self):
        particles = {Particle.ELECTRON, Particle.PHOTON}
        mode = Mode()
        mode.set("e p")
        self.assertEqual(len(mode), 2)
        for part in particles:
            self.assertIn(part, mode)
        mode = Mode()
        mode.set(["e", "p"])
        self.assertEqual(len(mode), 2)
        for part in particles:
            self.assertIn(part, mode)
        mode = Mode()
        mode.set(particles)
        self.assertEqual(len(mode), 2)
        for part in particles:
            self.assertIn(part, mode)
        with self.assertRaises(TypeError):
            mode.set(5)
        with self.assertRaises(TypeError):
            mode.set([5])
        with self.assertRaises(ValueError):
            mode.set(["n", Particle.PHOTON])
        with self.assertRaises(ValueError):
            mode.set([Particle.PHOTON, "n"])

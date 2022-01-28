from unittest import TestCase

import numpy as np
import mcnpy
from mcnpy.data_cards.transform import Transform
from mcnpy.errors import MalformedInputError
from mcnpy.input_parser.block_type import BlockType
from mcnpy.input_parser.mcnp_input import Card


class testTransformClass(TestCase):
    def test_transform_init(self):
        # test wrong ID finder
        with self.assertRaises(AssertionError):
            card = Card(BlockType.DATA, ["M20"])
            Transform(card)
        # test that the minimum word requirement is set
        with self.assertRaises(AssertionError):
            card = Card(BlockType.DATA, ["TR5"])
            Transform(card)
        # test that the transform is a valid number
        with self.assertRaises(MalformedInputError):
            card = Card(BlockType.DATA, ["TR1foo"] + ["0.0"] * 3)
            Transform(card)

        # test vanilla case
        card = Card(BlockType.DATA, ["tr5"] + ["1.0"] * 3 + ["0.0"] * 9)
        transform = Transform(card)
        self.assertEqual(transform.transform_number, 5)
        self.assertEqual(transform.old_transform_number, 5)
        self.assertFalse(transform.is_in_degrees)
        self.assertTrue(transform.is_main_to_aux)
        self.assertEqual(len(transform.displacement_vector), 3)
        self.assertEqual(len(transform.rotation_matrix), 9)
        for component in transform.displacement_vector:
            self.assertEqual(component, 1.0)
        for component in transform.rotation_matrix:
            self.assertEqual(component, 0.0)
        # Test in degrees form
        card = Card(BlockType.DATA, ["*tr5"] + ["1.0"] * 3 + ["0.0"] * 9)
        transform = Transform(card)
        self.assertTrue(transform.is_in_degrees)
        # test bad displace
        card = Card(BlockType.DATA, ["tr5"] + ["de"] * 3)
        with self.assertRaises(MalformedInputError):
            Transform(card)
        # test bad rotation
        card = Card(BlockType.DATA, ["tr5"] + ["0.0"] * 3 + ["foo"])
        with self.assertRaises(MalformedInputError):
            Transform(card)

        # test main to aux
        card = Card(BlockType.DATA, ["tr5"] + ["0.0"] * 3 + ["0.0"] * 9 + ["-1"])
        transform = Transform(card)
        self.assertFalse(transform.is_main_to_aux)
        card = Card(BlockType.DATA, ["tr5"] + ["0.0"] * 3 + ["0.0"] * 9 + ["1"])
        transform = Transform(card)
        self.assertTrue(transform.is_main_to_aux)
        card = Card(BlockType.DATA, ["tr5"] + ["0.0"] * 3 + ["0.0"] * 9 + ["f"])
        with self.assertRaises(MalformedInputError):
            Transform(card)

    def test_transform_degrees_setter(self):
        card = Card(BlockType.DATA, ["tr5"] + ["0.0"] * 3 + ["0.0"] * 9 + ["-1"])
        transform = Transform(card)
        transform.is_in_degrees = False
        self.assertFalse(transform.is_in_degrees)
        with self.assertRaises(AssertionError):
            transform.is_in_degrees = 1

    def test_transform_number_setter(self):
        card = Card(BlockType.DATA, ["tr5"] + ["0.0"] * 3 + ["0.0"] * 9 + ["-1"])
        transform = Transform(card)
        transform.transform_number = 20
        self.assertEqual(transform.transform_number, 20)
        with self.assertRaises(AssertionError):
            transform.transform_number = "hi"

    def test_transform_displace_setter(self):
        card = Card(BlockType.DATA, ["tr5"] + ["0.0"] * 3 + ["0.0"] * 9 + ["-1"])
        transform = Transform(card)
        transform.displacement_vector = np.array([1.0, 1.0, 1.0])
        for component in transform.displacement_vector:
            self.assertEqual(component, 1.0)
        with self.assertRaises(AssertionError):
            transform.displacement_vector = [1, 2]
        with self.assertRaises(AssertionError):
            transform.displacement_vector = np.array([1.0])

    def test_tranform_rotation_setter(self):
        card = Card(BlockType.DATA, ["tr5"] + ["0.0"] * 3 + ["0.0"] * 9 + ["-1"])
        transform = Transform(card)
        transform.rotation_matrix = np.array([1.0] * 5)
        for component in transform.rotation_matrix:
            self.assertEqual(component, 1.0)
        with self.assertRaises(AssertionError):
            transform.rotation_matrix = [1, 2]
        with self.assertRaises(AssertionError):
            transform.rotation_matrix = np.array([1.0])

    def test_is_main_aux_setter(self):
        card = Card(BlockType.DATA, ["tr5"] + ["0.0"] * 3 + ["0.0"] * 9)
        transform = Transform(card)
        transform.is_main_to_aux = False
        self.assertFalse(transform.is_main_to_aux)
        with self.assertRaises(AssertionError):
            self.is_main_to_aux = "hi"

    def test_transform_str(self):
        card = Card(BlockType.DATA, ["tr5"] + ["0.0"] * 3 + ["0.0"] * 9 + ["-1"])
        transform = Transform(card)
        answer = """TRANSFORM: 5
DISPLACE: [0. 0. 0.]
ROTATE: [0. 0. 0. 0. 0. 0. 0. 0. 0.]
MAIN_TO_AUX: False
"""
        self.assertEqual(answer, str(transform))

    def test_transform_print_mcnp(self):
        card = Card(BlockType.DATA, ["tr5"] + ["0.0"] * 3 + ["0.0"] * 9 + ["-1"])
        transform = Transform(card)
        output = transform.format_for_mcnp_input((6.2, 0))
        answers = [
            "TR5 0.0 0.0 0.0",
            "     0.0 0.0 0.0",
            "     0.0 0.0 0.0",
            "     0.0 0.0 0.0",
            "     -1",
        ]
        self.assertEqual(len(output), len(answers))
        for i, line in enumerate(output):
            self.assertEqual(line, answers[i])
        card = Card(BlockType.DATA, ["*tr5"] + ["0.0"] * 3 + ["0.0"] * 9 + ["-1"])
        transform = Transform(card)
        output = transform.format_for_mcnp_input((6.2, 0))
        self.assertEqual(output[0], "*TR5 0.0 0.0 0.0")

    def test_transform_equivalent(self):
        card = Card(BlockType.DATA, ["tr5"] + ["0.0"] * 3 + ["0.0"] * 9 + ["-1"])
        base = Transform(card)
        self.assertTrue(base.equivalent(base, 1e-6))
        #test different degrees
        card = Card(BlockType.DATA, ["*tr5"] + ["0.0"] * 3 + ["0.0"] * 9 + ["-1"])
        compare = Transform(card)
        self.assertFalse(base.equivalent(compare, 1e-3))
        #test different main_aux
        card = Card(BlockType.DATA, ["tr5"] + ["0.0"] * 3 + ["0.0"] * 9)
        compare = Transform(card)
        self.assertFalse(base.equivalent(compare, 1e-3))
        #test different displace
        card = Card(BlockType.DATA, ["tr5"] + ["1.0"] * 3 +["0.0"] * 9 + ["-1"])
        compare = Transform(card)
        self.assertFalse(base.equivalent(compare, 1e-3))
        #test different rotation
        card = Card(BlockType.DATA, ["*tr5"] + ["0.0"] * 3 + ["1.0"] * 9 + ["-1"])
        compare = Transform(card)
        self.assertFalse(base.equivalent(compare, 1e-3))


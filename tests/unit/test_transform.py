# Copyright 2024, Battelle Energy Alliance, LLC All Rights Reserved.
import copy
from unittest import TestCase

import numpy as np
import montepy
from montepy.data_inputs.transform import Transform
from montepy.errors import MalformedInputError
from montepy.input_parser.block_type import BlockType
from montepy.input_parser.mcnp_input import Input


class testTransformClass(TestCase):
    def test_transform_init(self):
        # test wrong ID finder
        with self.assertRaises(MalformedInputError):
            card = Input(["M20"], BlockType.DATA)
            Transform(card)
        # test that the minimum word requirement is set
        with self.assertRaises(MalformedInputError):
            card = Input(["TR5"], BlockType.DATA)
            Transform(card)
        # test that the transform is a valid number
        with self.assertRaises(MalformedInputError):
            card = Input(["TR1foo 0.0 0.0 0.0"], BlockType.DATA)
            Transform(card)

        # test invalid displacement vector
        with self.assertRaises(MalformedInputError):
            card = Input(["TR1 0.0 0.0 hi"], BlockType.DATA)
            Transform(card)
        # test invalid matrix
        with self.assertRaises(MalformedInputError):
            card = Input(["TR1 0.0 0.0 0.0 0.0 0.0 0.0 0.0 hi"], BlockType.DATA)
            Transform(card)
        # test invalid main to aux
        with self.assertRaises(MalformedInputError):
            card = Input(
                ["TR1 0.0 0.0 0.0 0.0 0.0 0.0 0.0 0.0 0.0 0.0 0.0 0.0 2"],
                BlockType.DATA,
            )
            Transform(card)
        # test that the transform has a number
        with self.assertRaises(MalformedInputError):
            card = Input(["*TR 0.0 0.0 0.0"], BlockType.DATA)
            Transform(card)
        # test that the transform doesn't have a particle
        with self.assertRaises(MalformedInputError):
            card = Input(["TR5:n,p 0.0 0.0 0.0"], BlockType.DATA)
            Transform(card)

        # test vanilla case
        in_str = "tr5 " + "1.0 " * 3 + "0.0 " * 9
        card = Input([in_str], BlockType.DATA)
        transform = Transform(card)
        self.assertEqual(transform.number, 5)
        self.assertEqual(transform.old_number, 5)
        self.assertFalse(transform.is_in_degrees)
        self.assertTrue(transform.is_main_to_aux)
        self.assertEqual(len(transform.displacement_vector), 3)
        self.assertEqual(len(transform.rotation_matrix), 9)
        for component in transform.displacement_vector:
            self.assertEqual(component, 1.0)
        for component in transform.rotation_matrix:
            self.assertEqual(component, 0.0)
        # Test in degrees form
        in_str = "*tr5 " + "1.0 " * 3 + "0.0 " * 9
        card = Input([in_str], BlockType.DATA)
        transform = Transform(card)
        self.assertTrue(transform.is_in_degrees)
        # test bad displace
        in_str = "*tr5 " + "de " * 3
        card = Input([in_str], BlockType.DATA)
        with self.assertRaises(MalformedInputError):
            Transform(card)
        # test bad rotation
        in_str = "*tr5 " + "1.0 " * 3 + "foo "
        card = Input([in_str], BlockType.DATA)
        with self.assertRaises(MalformedInputError):
            Transform(card)

        # test main to aux
        in_str = "*tr5 " + "1.0 " * 3 + "0.0 " * 9 + " -1"
        card = Input([in_str], BlockType.DATA)
        transform = Transform(card)
        self.assertFalse(transform.is_main_to_aux)
        in_str = "*tr5 " + "1.0 " * 3 + "0.0 " * 9 + " 1"
        card = Input([in_str], BlockType.DATA)
        transform = Transform(card)
        self.assertTrue(transform.is_main_to_aux)
        in_str = "*tr5 " + "1.0 " * 3 + "0.0 " * 9 + " foo"
        card = Input([in_str], BlockType.DATA)
        with self.assertRaises(MalformedInputError):
            Transform(card)

        # test blank init
        transform = Transform()
        self.assertEqual(transform.number, -1)
        self.assertEqual(len(transform.displacement_vector), 0)
        self.assertEqual(len(transform.rotation_matrix), 0)
        self.assertTrue(not transform.is_in_degrees)
        self.assertTrue(transform.is_main_to_aux)

    def test_validate(self):
        transform = Transform()
        with self.assertRaises(montepy.errors.IllegalState):
            transform.validate()
        with self.assertRaises(montepy.errors.IllegalState):
            transform.format_for_mcnp_input((6, 2, 0))

    def test_transform_degrees_setter(self):
        in_str = "*tr5 " + "1.0 " * 3 + "0.0 " * 9 + " -1"
        card = Input([in_str], BlockType.DATA)
        transform = Transform(card)
        transform.is_in_degrees = False
        self.assertFalse(transform.is_in_degrees)
        with self.assertRaises(TypeError):
            transform.is_in_degrees = 1

    def test_transform_number_setter(self):
        in_str = "*tr5 " + "1.0 " * 3 + "0.0 " * 9 + " -1"
        card = Input([in_str], BlockType.DATA)
        transform = Transform(card)
        transform.number = 20
        self.assertEqual(transform.number, 20)
        with self.assertRaises(TypeError):
            transform.number = "hi"
        with self.assertRaises(ValueError):
            transform.number = -5

    def test_transform_displace_setter(self):
        in_str = "*tr5 " + "1.0 " * 3 + "0.0 " * 9 + " -1"
        card = Input([in_str], BlockType.DATA)
        transform = Transform(card)
        transform.displacement_vector = np.array([1.0, 1.0, 1.0])
        for component in transform.displacement_vector:
            self.assertEqual(component, 1.0)
        with self.assertRaises(TypeError):
            transform.displacement_vector = [1, 2]
        with self.assertRaises(ValueError):
            transform.displacement_vector = np.array([1.0])
        with self.assertRaises(ValueError):
            transform.displacement_vector = np.array([1.0] * 10)

    def test_tranform_rotation_setter(self):
        in_str = "*tr5 " + "1.0 " * 3 + "0.0 " * 9 + " -1"
        card = Input([in_str], BlockType.DATA)
        transform = Transform(card)
        transform.rotation_matrix = np.array([1.0] * 5)
        for component in transform.rotation_matrix:
            self.assertEqual(component, 1.0)
        with self.assertRaises(TypeError):
            transform.rotation_matrix = [1, 2]
        with self.assertRaises(ValueError):
            transform.rotation_matrix = np.array([1.0])
        with self.assertRaises(ValueError):
            transform.displacement_vector = np.array([1.0] * 10)

    def test_is_main_aux_setter(self):
        in_str = "*tr5 " + "1.0 " * 3 + "0.0 " * 9
        card = Input([in_str], BlockType.DATA)
        transform = Transform(card)
        transform.is_main_to_aux = False
        self.assertFalse(transform.is_main_to_aux)
        with self.assertRaises(TypeError):
            transform.is_main_to_aux = "hi"

    def test_transform_str(self):
        in_str = "*tr5 " + "0.0 " * 3 + "0.0 " * 9 + " -1"
        card = Input([in_str], BlockType.DATA)
        transform = Transform(card)
        answer = """TRANSFORM: 5
DISPLACE: [0. 0. 0.]
ROTATE: [0. 0. 0. 0. 0. 0. 0. 0. 0.]
MAIN_TO_AUX: False
"""
        self.assertEqual(answer, repr(transform))
        self.assertEqual("TRANSFORM: 5", str(transform))

    def test_transform_print_mcnp(self):
        in_str = "tr5 " + "0.0 " * 3 + "0.0 " * 9 + " -1"
        card = Input([in_str], BlockType.DATA)
        transform = Transform(card)
        output = transform.format_for_mcnp_input((6, 2, 0))
        answers = [in_str.replace("5", "2")]
        self.assertEqual(output[0], in_str)
        transform.number = 2
        output = transform.format_for_mcnp_input((6, 2, 0))
        self.assertEqual(len(output), len(answers))
        for i, line in enumerate(output):
            self.assertEqual(line, answers[i])
        in_str = "*tr5 " + "0.0 " * 3 + "0.0 " * 9 + " -1"
        answers = [in_str.replace("5", "2")]
        card = Input([in_str], BlockType.DATA)
        transform = Transform(card)
        transform.number = 2
        output = transform.format_for_mcnp_input((6, 2, 0))
        self.assertEqual(output, answers)

    def test_transform_equivalent(self):
        in_str = "tr5 " + "0.0 " * 3 + "0.0 " * 9 + " -1"
        card = Input([in_str], BlockType.DATA)
        base = Transform(card)
        self.assertTrue(base.equivalent(base, 1e-6))
        # test different degrees
        in_str = "*tr5 " + "0.0 " * 3 + "0.0 " * 9 + " -1"
        card = Input([in_str], BlockType.DATA)
        compare = Transform(card)
        self.assertFalse(base.equivalent(compare, 1e-3))
        # test different main_aux
        in_str = "tr5 " + "0.0 " * 3 + "0.0 " * 9
        card = Input([in_str], BlockType.DATA)
        compare = Transform(card)
        self.assertFalse(base.equivalent(compare, 1e-3))
        # test different displace
        in_str = "tr5 " + "1.0 " * 3 + "0.0 " * 9 + "-1"
        card = Input([in_str], BlockType.DATA)
        compare = Transform(card)
        self.assertFalse(base.equivalent(compare, 1e-3))
        # test different rotation
        in_str = "tr5 " + "0.0 " * 3 + "1.0 " * 9 + "-1"
        card = Input([in_str], BlockType.DATA)
        compare = Transform(card)
        self.assertFalse(base.equivalent(compare, 1e-3))
        # test different rotation
        in_str = "tr5 " + "0.0 " * 3
        card = Input([in_str], BlockType.DATA)
        compare = Transform(card)
        compare.is_main_to_aux = False
        self.assertFalse(base.equivalent(compare, 1e-3))

    def test_transform_update_values(self):
        in_str = "tr5 " + "0.0 " * 3 + "0.0 " * 9 + " -1"
        card = Input([in_str], BlockType.DATA)
        base = Transform(card)
        base._update_values()
        self.assertEqual(base._tree["classifier"].modifier.value, "")
        self.assertEqual(len(base.data), 13)
        # test with no rotation matrix start
        in_str = "tr5 " + "0.0 " * 3
        card = Input([in_str], BlockType.DATA)
        base = Transform(card)
        test = copy.deepcopy(base)
        test.rotation_matrix = np.ones(9)
        test._update_values()
        self.assertEqual(len(test.data), 12)
        self.assertEqual(test.data[-1].value, 1.0)
        test.is_main_to_aux = False
        test._update_values()
        self.assertEqual(len(test.data), 13)
        self.assertTrue(test.data[-1].is_negative)
        # test partial rotation matrix start
        in_str = "tr5 " + "0.0 " * 3 + "0.0 " * 5
        card = Input([in_str], BlockType.DATA)
        base = Transform(card)
        base.rotation_matrix = np.ones(9)
        base._update_values()
        self.assertEqual(len(base.data), 12)
        self.assertEqual(base.data[-1].value, 1.0)

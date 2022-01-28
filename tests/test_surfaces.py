from unittest import TestCase

import mcnpy

from mcnpy.errors import MalformedInputError
from mcnpy.input_parser.block_type import BlockType
from mcnpy.input_parser.mcnp_input import Card
from mcnpy.surfaces.surface import Surface
from mcnpy.surfaces.surface_type import SurfaceType


class testSurfaces(TestCase):
    def test_surface_init(self):
        card = Card(BlockType.SURFACE, ["1", "PZ", "0.0"])
        surf = Surface(card)
        self.assertEqual(surf.surface_number, 1)
        self.assertEqual(surf.old_surface_number, 1)
        self.assertEqual(len(surf.surface_constants), 1)
        self.assertEqual(surf.surface_constants[0], 0.0)
        self.assertEqual(surf.surface_type, SurfaceType.PZ)
        self.assertFalse(surf.is_reflecting)
        self.assertFalse(surf.is_white_boundary)
        self.assertIsNone(surf.old_transform_number)
        self.assertIsNone(surf.transform)
        self.assertIsNone(surf.old_periodic_surface)
        self.assertIsNone(surf.periodic_surface)
        # test reflective
        card = Card(BlockType.SURFACE, ["*1", "PZ", "0.0"])
        surf = Surface(card)
        self.assertTrue(surf.is_reflecting)
        # test white boundary
        card = Card(BlockType.SURFACE, ["+1", "PZ", "0.0"])
        surf = Surface(card)
        self.assertTrue(surf.is_white_boundary)
        # test negative surface
        with self.assertRaises(MalformedInputError):
            card = Card(BlockType.SURFACE, ["-1", "PZ", "0"])
            Surface(card)
        # test bad surface number
        with self.assertRaises(MalformedInputError):
            card = Card(BlockType.SURFACE, ["foo", "PZ", "0"])
            Surface(card)

        # test transform
        card = Card(BlockType.SURFACE, ["1", "5", "PZ", "0"])
        surf = Surface(card)
        self.assertEqual(surf.old_transform_number, 5)

        # test periodic surface
        card = Card(BlockType.SURFACE, ["1", "-5", "PZ", "0"])
        surf = Surface(card)
        self.assertEqual(surf.old_periodic_surface, 5)

        # test transform bad
        card = Card(BlockType.SURFACE, ["1", "5foo", "PZ", "0"])
        with self.assertRaises(MalformedInputError):
            Surface(card)
        card = Card(BlockType.SURFACE, ["+1", "PZ", "foo"])
        with self.assertRaises(MalformedInputError):
            Surface(card)

    def test_surface_is_reflecting_setter(self):
        card = Card(BlockType.SURFACE, ["1", "PZ", "0.0"])
        surf = Surface(card)
        surf.is_reflecting = True
        self.assertTrue(surf.is_reflecting)
        with self.assertRaises(AssertionError):
            surf.is_reflecting = 1

    def test_surface_is_white_bound_setter(self):
        card = Card(BlockType.SURFACE, ["1", "PZ", "0.0"])
        surf = Surface(card)
        surf.is_white_boundary = True
        self.assertTrue(surf.is_white_boundary)
        with self.assertRaises(AssertionError):
            surf.is_white_boundary = 1

    def test_surface_constants_setter(self):
        card = Card(BlockType.SURFACE, ["1", "PZ", "0.0"])
        surf = Surface(card)
        surf.surface_constants = [10.0]
        self.assertEqual(surf.surface_constants[0], 10.0)
        with self.assertRaises(AssertionError):
            surf.surface_constants = "foo"

    def test_surface_number_setter(self):
        card = Card(BlockType.SURFACE, ["1", "PZ", "0.0"])
        surf = Surface(card)
        surf.surface_number = 20
        self.assertEqual(surf.surface_number, 20)
        with self.assertRaises(AssertionError):
            surf.surface_number = "foo"
        with self.assertRaises(AssertionError):
            surf.surface_number = -5

    def test_surface_ordering(self):
        card = Card(BlockType.SURFACE, ["1", "PZ", "0.0"])
        surf1 = Surface(card)
        card = Card(BlockType.SURFACE, ["5", "PZ", "0.0"])
        surf2 = Surface(card)
        sort_list = sorted([surf2, surf1])
        self.assertEqual(sort_list[0], surf1)
        self.assertEqual(sort_list[1], surf2)

    def test_surface_format_for_mcnp(self):
        card = Card(BlockType.SURFACE, ["+1", "PZ", "0.0"])
        surf = Surface(card)
        answer = "+1 PZ 0"
        self.assertEqual(surf.format_for_mcnp_input((6.2, 0))[0], answer)
        card = Card(BlockType.SURFACE, ["*1", "PZ", "0.0"])
        surf = Surface(card)
        answer = "*1 PZ 0"
        self.assertEqual(surf.format_for_mcnp_input((6.2, 0))[0], answer)
        card = Card(BlockType.SURFACE, ["1", "PZ", "0.0"])
        surf = Surface(card)
        answer = "1 PZ 0"
        self.assertEqual(surf.format_for_mcnp_input((6.2, 0))[0], answer)

    def test_surface_str(self):
        card = Card(BlockType.SURFACE, ["+1", "PZ", "0.0"])
        surf = Surface(card)
        self.assertEqual(str(surf), "SURFACE: 1, PZ")

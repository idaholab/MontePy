from unittest import TestCase

import mcnpy

from mcnpy.errors import MalformedInputError
from mcnpy.input_parser.block_type import BlockType
from mcnpy.input_parser.mcnp_input import Card
from mcnpy.surfaces.axis_plane import AxisPlane
from mcnpy.surfaces.cylinder_on_axis import CylinderOnAxis
from mcnpy.surfaces.cylinder_par_axis import CylinderParAxis
from mcnpy.surfaces.general_plane import GeneralPlane
from mcnpy.surfaces.surface import Surface
from mcnpy.surfaces.surface_builder import surface_builder
from mcnpy.surfaces.surface_type import SurfaceType


class testSurfaces(TestCase):
    def test_surface_init(self):
        in_str = "1 PZ 0.0"
        card = Card([in_str], BlockType.SURFACE)
        surf = Surface(card)
        self.assertEqual(surf.number, 1)
        self.assertEqual(surf.old_number, 1)
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
        in_str = "*1 PZ 0.0"
        card = Card([in_str], BlockType.SURFACE)
        surf = Surface(card)
        self.assertTrue(surf.is_reflecting)
        # test white boundary
        in_str = "+1 PZ 0.0"
        card = Card([in_str], BlockType.SURFACE)
        surf = Surface(card)
        self.assertTrue(surf.is_white_boundary)
        # test negative surface
        with self.assertRaises(MalformedInputError):
            in_str = "-1 PZ 0.0"
            card = Card([in_str], BlockType.SURFACE)
            Surface(card)
        # test bad surface number
        with self.assertRaises(MalformedInputError):
            in_str = "foo PZ 0.0"
            card = Card([in_str], BlockType.SURFACE)
            Surface(card)

        # test bad surface type
        with self.assertRaises(MalformedInputError):
            in_str = "1 INL 0.0"
            card = Card([in_str], BlockType.SURFACE)
            Surface(card)

        # test transform
        in_str = "1 5 PZ 0"
        card = Card([in_str], BlockType.SURFACE)
        surf = Surface(card)
        self.assertEqual(surf.old_transform_number, 5)

        # test periodic surface
        in_str = "1 -5 PZ 0"
        card = Card([in_str], BlockType.SURFACE)
        surf = Surface(card)
        self.assertEqual(surf.old_periodic_surface, 5)

        # test transform bad
        in_str = "1 5foo PZ 0"
        card = Card([in_str], BlockType.SURFACE)
        with self.assertRaises(MalformedInputError):
            Surface(card)
        in_str = "+1 PZ foo"
        card = Card([in_str], BlockType.SURFACE)
        with self.assertRaises(MalformedInputError):
            Surface(card)

    def test_surface_is_reflecting_setter(self):
        in_str = "1 PZ 0.0"
        card = Card([in_str], BlockType.SURFACE)
        surf = Surface(card)
        surf.is_reflecting = True
        self.assertTrue(surf.is_reflecting)
        with self.assertRaises(TypeError):
            surf.is_reflecting = 1

    def test_surface_is_white_bound_setter(self):
        in_str = "1 PZ 0.0"
        card = Card([in_str], BlockType.SURFACE)
        surf = Surface(card)
        surf.is_white_boundary = True
        self.assertTrue(surf.is_white_boundary)
        with self.assertRaises(TypeError):
            surf.is_white_boundary = 1

    def test_surface_constants_setter(self):
        in_str = "1 PZ 0.0"
        card = Card([in_str], BlockType.SURFACE)
        surf = Surface(card)
        surf.surface_constants = [10.0]
        self.assertEqual(surf.surface_constants[0], 10.0)
        with self.assertRaises(TypeError):
            surf.surface_constants = "foo"
        with self.assertRaises(TypeError):
            surf.surface_constants = [1, "foo"]

    def test_surface_number_setter(self):
        in_str = "1 PZ 0.0"
        card = Card([in_str], BlockType.SURFACE)
        surf = Surface(card)
        surf.number = 20
        self.assertEqual(surf.number, 20)
        with self.assertRaises(TypeError):
            surf.number = "foo"
        with self.assertRaises(ValueError):
            surf.number = -5

    def test_surface_ordering(self):
        in_str = "1 PZ 0.0"
        card = Card([in_str], BlockType.SURFACE)
        surf1 = Surface(card)
        in_str = "5 PZ 0.0"
        card = Card([in_str], BlockType.SURFACE)
        surf2 = Surface(card)
        sort_list = sorted([surf2, surf1])
        self.assertEqual(sort_list[0], surf1)
        self.assertEqual(sort_list[1], surf2)

    def test_surface_format_for_mcnp(self):
        in_str = "+1 PZ 0.0"
        card = Card([in_str], BlockType.SURFACE)
        surf = Surface(card)
        surf.number = 2
        answer = "+2 PZ 0"
        self.assertEqual(surf.format_for_mcnp_input((6, 2, 0))[0], answer)
        in_str = "*1 PZ 0.0"
        card = Card([in_str], BlockType.SURFACE)
        surf = Surface(card)
        surf.number = 2
        answer = "*2 PZ 0"
        self.assertEqual(surf.format_for_mcnp_input((6, 2, 0))[0], answer)
        in_str = "1 PZ 0.0"
        card = Card([in_str], BlockType.SURFACE)
        surf = Surface(card)
        surf.number = 2
        answer = "2 PZ 0"
        self.assertEqual(surf.format_for_mcnp_input((6, 2, 0))[0], answer)

    def test_surface_str(self):
        in_str = "+1 PZ 0.0"
        card = Card([in_str], BlockType.SURFACE)
        surf = Surface(card)
        self.assertEqual(str(surf), "SURFACE: 1, PZ")
        self.assertEqual(
            repr(surf),
            "SURFACE: 1, PZ, periodic surface: None, transform: None, constants: [0.0]",
        )

    def test_surface_builder(self):
        testers = [
            ("1 PZ 0.0", AxisPlane),
            ("2 Cx 10.0", CylinderOnAxis),
            ("3 C/Z 4 3 5", CylinderParAxis),
            ("6 p 1 2 3 4", GeneralPlane),
            ("7 so 5", Surface),
            ("10 C/x 25 0 -5", CylinderParAxis),
            ("11 c/Y 25 0 -5", CylinderParAxis),
            ("12 CY 3", CylinderOnAxis),
            ("13 cz 0", CylinderOnAxis),
            ("14 px 1.e-3", AxisPlane),
            ("15 PY .1", AxisPlane),
        ]
        for in_str, surf_plane in testers:
            card = Card([in_str], BlockType.SURFACE)
            self.assertIsInstance(surface_builder(card), surf_plane)

    def test_axis_plane_init(self):
        bad_inputs = ["1 P 0.0", "1 PZ 0.0 10.0"]
        for bad_input in bad_inputs:
            with self.assertRaises(ValueError):
                surf = mcnpy.surfaces.axis_plane.AxisPlane(
                    Card([bad_input], BlockType.SURFACE)
                )

    def test_cylinder_on_axis_init(self):
        bad_inputs = ["1 P 0.0", "1 CZ 0.0 10.0"]
        for bad_input in bad_inputs:
            with self.assertRaises(ValueError):
                surf = mcnpy.surfaces.cylinder_on_axis.CylinderOnAxis(
                    Card([bad_input], BlockType.SURFACE)
                )

    def test_cylinder_par_axis_init(self):
        bad_inputs = ["1 P 0.0", "1 C/Z 0.0"]
        for bad_input in bad_inputs:
            with self.assertRaises(ValueError):
                surf = mcnpy.surfaces.cylinder_par_axis.CylinderParAxis(
                    Card([bad_input], BlockType.SURFACE)
                )

    def test_gen_plane_init(self):
        bad_inputs = ["1 PZ 0.0", "1 P 0.0"]
        for bad_input in bad_inputs:
            with self.assertRaises(ValueError):
                surf = mcnpy.surfaces.general_plane.GeneralPlane(
                    Card([bad_input], BlockType.SURFACE)
                )

    def test_axis_plane_location_setter(self):
        in_str = "1 PZ 0.0"
        surf = surface_builder(Card([in_str], BlockType.SURFACE))
        self.assertEqual(surf.location, 0.0)
        surf.location = 10.0
        self.assertEqual(surf.location, 10.0)
        with self.assertRaises(TypeError):
            surf.location = "hi"

    def test_cylinder_axis_radius_setter(self):
        in_str = "1 CZ 5.0"
        surf = surface_builder(Card([in_str], BlockType.SURFACE))
        self.assertEqual(surf.radius, 5.0)
        surf.radius = 3.0
        self.assertEqual(surf.radius, 3.0)
        with self.assertRaises(TypeError):
            surf.radius = "foo"
        with self.assertRaises(ValueError):
            surf.radius = -5.0

    def test_cylinder_radius_setter(self):
        in_str = "1 c/Z 3.0 4.0 5"
        surf = surface_builder(Card([in_str], BlockType.SURFACE))
        self.assertEqual(surf.radius, 5.0)
        surf.radius = 3.0
        self.assertEqual(surf.radius, 3.0)
        with self.assertRaises(TypeError):
            surf.radius = "foo"
        with self.assertRaises(ValueError):
            surf.radius = -5.0

    def test_cylinder_location_setter(self):
        in_str = "1 c/Z 3.0 4.0 5"
        surf = surface_builder(Card([in_str], BlockType.SURFACE))
        self.assertEqual(surf.coordinates, [3.0, 4.0])
        surf.coordinates = [1, 2]
        self.assertEqual(surf.coordinates, [1, 2])
        # test wrong type
        with self.assertRaises(TypeError):
            surf.coordinates = "fo"
        # test length issues
        with self.assertRaises(ValueError):
            surf.coordinates = [3, 4, 5]

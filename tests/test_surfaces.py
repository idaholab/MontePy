# Copyright 2024-2025, Battelle Energy Alliance, LLC All Rights Reserved.
import io
from unittest import TestCase
from pathlib import Path
import pytest

import montepy
from montepy.errors import MalformedInputError, SurfaceConstantsWarning
from montepy.input_parser.block_type import BlockType
from montepy.input_parser.mcnp_input import Input
from montepy.surfaces.axis_plane import AxisPlane
from montepy.surfaces.cylinder_on_axis import CylinderOnAxis
from montepy.surfaces.cylinder_par_axis import CylinderParAxis
from montepy.surfaces.general_plane import GeneralPlane
from montepy.surfaces.surface import Surface
from montepy.surfaces.surface_builder import surface_builder
from montepy.surfaces.surface_type import SurfaceType


class testSurfaces(TestCase):
    def test_surface_init(self):
        surf = Surface("1 PZ 0.0")
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
        card = Input([in_str], BlockType.SURFACE)
        surf = Surface(card)
        self.assertTrue(surf.is_reflecting)
        # test white boundary
        in_str = "+1 PZ 0.0"
        card = Input([in_str], BlockType.SURFACE)
        surf = Surface(card)
        self.assertTrue(surf.is_white_boundary)
        # test negative surface
        with self.assertRaises(MalformedInputError):
            in_str = "-1 PZ 0.0"
            card = Input([in_str], BlockType.SURFACE)
            Surface(card)
        # test bad surface number
        with self.assertRaises(MalformedInputError):
            in_str = "foo PZ 0.0"
            card = Input([in_str], BlockType.SURFACE)
            Surface(card)

        # test bad surface type
        with self.assertRaises(MalformedInputError):
            in_str = "1 INL 0.0"
            card = Input([in_str], BlockType.SURFACE)
            Surface(card)

        # test transform
        in_str = "1 5 PZ 0"
        card = Input([in_str], BlockType.SURFACE)
        surf = Surface(card)
        self.assertEqual(surf.old_transform_number, 5)

        # test periodic surface
        in_str = "1 -5 PZ 0"
        card = Input([in_str], BlockType.SURFACE)
        surf = Surface(card)
        self.assertEqual(surf.old_periodic_surface, 5)

        # test transform bad
        in_str = "1 5foo PZ 0"
        card = Input([in_str], BlockType.SURFACE)
        with self.assertRaises(MalformedInputError):
            Surface(card)
        in_str = "+1 PZ foo"
        card = Input([in_str], BlockType.SURFACE)
        with self.assertRaises(MalformedInputError):
            Surface(card)
        surf = Surface(number=5)
        assert surf.number == 5

    def test_validator(self):
        surf = Surface()
        # TODO is IllegalState or defaults values more desirable?
        with self.assertRaises(montepy.errors.IllegalState):
            surf.validate()
        with self.assertRaises(montepy.errors.IllegalState):
            surf.format_for_mcnp_input((6, 2, 0))
        surf.number = 1
        with self.assertRaises(montepy.errors.IllegalState):
            surf.validate()
        # cylinder on axis
        surf = CylinderOnAxis()
        with self.assertRaises(montepy.errors.IllegalState):
            surf.validate()
        with self.assertRaises(montepy.errors.IllegalState):
            surf.format_for_mcnp_input((6, 2, 0))
        surf._surface_type = SurfaceType.CX
        with self.assertRaises(montepy.errors.IllegalState):
            surf.validate()
        # cylinder par axis
        surf = CylinderParAxis()
        with self.assertRaises(montepy.errors.IllegalState):
            surf.validate()
        with self.assertRaises(montepy.errors.IllegalState):
            surf.format_for_mcnp_input((6, 2, 0))
        surf._surface_type = SurfaceType.C_X
        with self.assertRaises(montepy.errors.IllegalState):
            surf.validate()
        surf.radius = 5.0
        with self.assertRaises(montepy.errors.IllegalState):
            surf.validate()
        # axis plane
        surf = AxisPlane()
        with self.assertRaises(montepy.errors.IllegalState):
            surf.validate()
        with self.assertRaises(montepy.errors.IllegalState):
            surf.format_for_mcnp_input((6, 2, 0))
        surf._surface_type = SurfaceType.PX
        with self.assertRaises(montepy.errors.IllegalState):
            surf.validate()
        surf.number = 1
        surf.location = 0.0
        # ensure that this doesn't raise an error
        surf.validate()
        # general plane
        surf = GeneralPlane()
        with self.assertRaises(montepy.errors.IllegalState):
            surf.validate()
        with self.assertRaises(montepy.errors.IllegalState):
            surf.format_for_mcnp_input((6, 2, 0))
        surf._surface_type = SurfaceType.P
        with self.assertRaises(montepy.errors.IllegalState):
            surf.validate()

    def test_surface_constants_setter(self):
        in_str = "1 PZ 0.0"
        card = Input([in_str], BlockType.SURFACE)
        surf = Surface(card)
        surf.surface_constants = [10.0]
        self.assertEqual(surf.surface_constants[0], 10.0)
        with self.assertRaises(TypeError):
            surf.surface_constants = "foo"
        with self.assertRaises(ValueError):
            surf.surface_constants = [1, "foo"]

    def test_surface_number_setter(self):
        in_str = "1 PZ 0.0"
        card = Input([in_str], BlockType.SURFACE)
        surf = Surface(card)
        surf.number = 20
        self.assertEqual(surf.number, 20)
        with self.assertRaises(TypeError):
            surf.number = "foo"
        with self.assertRaises(ValueError):
            surf.number = -5

    def test_surface_surface_type_setter(self):
        surf = montepy.surfaces.parse_surface("1 PZ 0.0")
        with pytest.raises(ValueError):
            surf.surface_type = "CX"
        with pytest.raises(ValueError):
            surf.surface_type = SurfaceType.CX

    def test_surface_ordering(self):
        in_str = "1 PZ 0.0"
        card = Input([in_str], BlockType.SURFACE)
        surf1 = Surface(card)
        in_str = "5 PZ 0.0"
        card = Input([in_str], BlockType.SURFACE)
        surf2 = Surface(card)
        sort_list = sorted([surf2, surf1])
        self.assertEqual(sort_list[0], surf1)
        self.assertEqual(sort_list[1], surf2)

    def test_surface_format_for_mcnp(self):
        in_str = "+1 PZ 0.0"
        card = Input([in_str], BlockType.SURFACE)
        surf = Surface(card)
        surf.number = 2
        answer = "+2 PZ 0.0"
        self.assertEqual(surf.format_for_mcnp_input((6, 2, 0))[0], answer)
        in_str = "*1 PZ 0.0"
        card = Input([in_str], BlockType.SURFACE)
        surf = Surface(card)
        surf.number = 2
        answer = "*2 PZ 0.0"
        self.assertEqual(surf.format_for_mcnp_input((6, 2, 0))[0], answer)
        # test input mimicry
        in_str = "1 PZ 0"
        card = Input([in_str], BlockType.SURFACE)
        surf = Surface(card)
        surf.number = 2
        answer = "2 PZ 0"
        self.assertEqual(surf.format_for_mcnp_input((6, 2, 0))[0], answer)

    def test_surface_str(self):
        in_str = "+1 PZ 0.0"
        card = Input([in_str], BlockType.SURFACE)
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
            card = Input([in_str], BlockType.SURFACE)
            self.assertIsInstance(surface_builder(card), surf_plane)

    def test_axis_plane_init(self):
        bad_inputs = ["1 P 0.0", "1 PZ 0.0 10.0"]
        for bad_input in bad_inputs:
            with self.assertRaises(ValueError):
                surf = montepy.surfaces.axis_plane.AxisPlane(
                    Input([bad_input], BlockType.SURFACE)
                )
        surf = montepy.surfaces.axis_plane.AxisPlane(number=5)
        assert surf.number == 5

    def test_cylinder_on_axis_init(self):
        bad_inputs = ["1 P 0.0", "1 CZ 0.0 10.0"]
        for bad_input in bad_inputs:
            with self.assertRaises(ValueError):
                surf = montepy.surfaces.cylinder_on_axis.CylinderOnAxis(
                    Input([bad_input], BlockType.SURFACE)
                )
        surf = montepy.surfaces.cylinder_on_axis.CylinderOnAxis(number=5)
        assert surf.number == 5

    def test_cylinder_par_axis_init(self):
        bad_inputs = ["1 P 0.0", "1 C/Z 0.0"]
        for bad_input in bad_inputs:
            with self.assertRaises(ValueError):
                surf = montepy.surfaces.cylinder_par_axis.CylinderParAxis(
                    Input([bad_input], BlockType.SURFACE)
                )
        surf = montepy.surfaces.cylinder_par_axis.CylinderParAxis(number=5)
        assert surf.number == 5

    def test_gen_plane_init(self):
        bad_inputs = ["1 PZ 0.0", "1 P 0.0"]
        for bad_input in bad_inputs:
            with self.assertRaises(ValueError):
                surf = montepy.surfaces.general_plane.GeneralPlane(
                    Input([bad_input], BlockType.SURFACE)
                )
        surf = montepy.surfaces.general_plane.GeneralPlane(number=5)
        assert surf.number == 5

    def test_axis_plane_location_setter(self):
        in_str = "1 PZ 0.0"
        surf = surface_builder(Input([in_str], BlockType.SURFACE))
        self.assertEqual(surf.location, 0.0)
        surf.location = 10.0
        self.assertEqual(surf.location, 10.0)
        with self.assertRaises(TypeError):
            surf.location = "hi"

    def test_general_plane_constants(self):
        error_inputs = ["16 P 0. 0. 0. 0. 0. 1. 0."]
        warn_inputs = ["17 p 0. 0. 0. 0. 0. 1. 0. 1. 1. 0. 1. 0."]
        for error_input in error_inputs:
            with self.assertRaises(ValueError):
                surf = montepy.surfaces.general_plane.GeneralPlane(error_input)
        for warn_input in warn_inputs:
            with self.assertRaises(SurfaceConstantsWarning):
                surf = montepy.surfaces.general_plane.GeneralPlane(warn_input)

    def test_cylinder_axis_radius_setter(self):
        in_str = "1 CZ 5.0"
        surf = surface_builder(Input([in_str], BlockType.SURFACE))
        self.assertEqual(surf.radius, 5.0)
        surf.radius = 3.0
        self.assertEqual(surf.radius, 3.0)
        with self.assertRaises(TypeError):
            surf.radius = "foo"
        with self.assertRaises(ValueError):
            surf.radius = -5.0

    def test_cylinder_radius_setter(self):
        in_str = "1 c/Z 3.0 4.0 5"
        surf = surface_builder(Input([in_str], BlockType.SURFACE))
        self.assertEqual(surf.radius, 5.0)
        surf.radius = 3.0
        self.assertEqual(surf.radius, 3.0)
        with self.assertRaises(TypeError):
            surf.radius = "foo"
        with self.assertRaises(ValueError):
            surf.radius = -5.0

    def test_cylinder_location_setter(self):
        in_str = "1 c/Z 3.0 4.0 5"
        surf = surface_builder(Input([in_str], BlockType.SURFACE))
        self.assertEqual(surf.coordinates, (3.0, 4.0))
        surf.coordinates = [1, 2]
        self.assertEqual(surf.coordinates, (1, 2))
        # test wrong type
        with self.assertRaises(TypeError):
            surf.coordinates = "fo"
        # test length issues
        with self.assertRaises(ValueError):
            surf.coordinates = [3, 4, 5]


@pytest.mark.filterwarnings("ignore")
@pytest.mark.parametrize(
    "cls, surf_type, params",
    [
        (CylinderOnAxis, SurfaceType.CZ, {"radius": 0.5}),
        (
            CylinderParAxis,
            SurfaceType.C_X,
            {"coordinates": (0.2, 0.3), "radius": 1.0, "is_white_boundary": True},
        ),
        (AxisPlane, SurfaceType.PZ, {"location": 10.0, "is_reflecting": True}),
        (
            AxisPlane,
            SurfaceType.PZ,
            {"location": 0.5, "periodic_surface": surface_builder("1 PZ 1.0")},
        ),
        (
            CylinderOnAxis,
            SurfaceType.CX,
            {
                "radius": 0.5,
                "transform": montepy.data_inputs.data_parser.parse_data("TR1 0 0 10.0"),
            },
        ),
    ],
)
def test_scratch_surface_generation(cls, surf_type, params: dict):
    surf = cls(number=5)
    surf.surface_type = surf_type
    for attr_name, value in params.items():
        setattr(surf, attr_name, value)
    verify_export(surf)


def test_unset_transform():
    surf = surface_builder("1 10 PZ 0.0")
    transform = montepy.data_inputs.data_parser.parse_data("TR10 0 0 5")
    surf.update_pointers([], [transform])
    del surf.transform
    verify_export(surf)


def test_unset_periodic():
    surf = surface_builder("1 -10 PZ 0.0")
    surf2 = surface_builder("10 PZ 10.0")
    surf.update_pointers(montepy.Surfaces([surf2]), [])
    del surf.periodic_surface
    verify_export(surf)


def verify_export(surf):
    output = surf.format_for_mcnp_input((6, 3, 0))
    print("Surface output", output)
    new_surf = Surface("\n".join(output))
    verify_equiv_surf(surf, new_surf)


def verify_equiv_surf(surf, new_surf):
    assert surf.number == new_surf.number, "Surface number not preserved."
    assert len(surf.surface_constants) == len(
        new_surf.surface_constants
    ), "number of surface constants not kept."
    for old_const, new_const in zip(surf.surface_constants, new_surf.surface_constants):
        assert old_const == pytest.approx(new_const)
    assert surf.is_reflecting == new_surf.is_reflecting
    assert surf.is_white_boundary == new_surf.is_white_boundary
    if surf.periodic_surface:
        assert surf.periodic_surface.number == new_surf.old_periodic_surface
    else:
        assert new_surf.old_periodic_surface == None
    if surf.transform:
        assert surf.transform.number == new_surf.old_transform_number
    else:
        assert new_surf.old_transform_number == None


def verify_prob_export(problem, surf):
    with io.StringIO() as fh:
        problem.write_problem(fh)
        fh.seek(0)
        new_problem = montepy.read_input(fh)
    new_surf = new_problem.surfaces[surf.number]
    verify_equiv_surf(surf, new_surf)


@pytest.mark.parametrize(
    "surf_str", ["1 PZ 0.0", "1 SO 1.0", "1 CZ 9.0", "4 C/z 5.0 0 3"]
)
def test_surface_clone(surf_str):
    prob = montepy.MCNP_Problem("")
    surf = surface_builder(surf_str)
    prob.surfaces.append(surf)
    new_surf = surf.clone()
    assert surf.surface_type == new_surf.surface_type
    assert surf.surface_constants == new_surf.surface_constants


@pytest.fixture
def simple_problem(scope="module"):
    return montepy.read_input(Path("tests") / "inputs" / "test.imcnp")


@pytest.fixture
def cp_simple_problem(simple_problem):
    return simple_problem.clone()


@pytest.mark.parametrize(
    "in_str, expected",
    [("1 PZ 0.0", True), ("*1 PZ 0.0", False), ("    *1 PZ 0.0", False)],
)
def test_surface_is_reflecting_setter(cp_simple_problem, in_str, expected):
    surf = Surface(in_str)
    surf.is_reflecting = expected
    assert surf.is_reflecting == expected
    cp_simple_problem.surfaces.append(surf)
    verify_prob_export(cp_simple_problem, surf)
    with pytest.raises(TypeError):
        surf.is_reflecting = 1


@pytest.mark.parametrize(
    "in_str, expected",
    [("1 PZ 0.0", True), ("+1 PZ 0.0", False), ("    +1 PZ 0.0", False)],
)
def test_surface_is_white_bound_setter(cp_simple_problem, in_str, expected):
    surf = Surface(in_str)
    surf.is_white_boundary = expected
    assert surf.is_white_boundary == expected
    cp_simple_problem.surfaces.append(surf)
    verify_prob_export(cp_simple_problem, surf)
    with pytest.raises(TypeError):
        surf.is_white_boundary = 1

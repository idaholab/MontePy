# Copyright 2024-2025, Battelle Energy Alliance, LLC All Rights Reserved.
import io
from pathlib import Path
import pytest

import montepy
from montepy.exceptions import MalformedInputError, SurfaceConstantsWarning
from montepy.input_parser.block_type import BlockType
from montepy.input_parser.mcnp_input import Input
from montepy.surfaces.axis_plane import AxisPlane
from montepy.surfaces.cylinder_on_axis import CylinderOnAxis
from montepy.surfaces.cylinder_par_axis import CylinderParAxis
from montepy.surfaces.general_plane import GeneralPlane
from montepy.surfaces.general_sphere import GeneralSphere
from montepy.surfaces.sphere_at_origin import SphereAtOrigin
from montepy.surfaces.sphere_on_axis import SphereOnAxis
from montepy.surfaces.surface import Surface
from montepy.surfaces.surface_builder import surface_builder
from montepy.surfaces.surface_type import SurfaceType


def test_surface_init():
    # Test with string
    surf = Surface("1 PZ 0.0")
    assert surf.number == 1
    assert surf.old_number == 1
    assert len(surf.surface_constants) == 1
    assert surf.surface_constants[0] == 0.0
    assert surf.surface_type == SurfaceType.PZ
    assert not surf.is_reflecting
    assert not surf.is_white_boundary
    assert surf.old_transform_number is None
    assert surf.transform is None
    assert surf.old_periodic_surface is None
    assert surf.periodic_surface is None
    # Test with Input object
    surf2 = Surface(Input(["1 PZ 0.0"], BlockType.SURFACE))
    assert surf2.number == 1
    # test reflective
    in_str = "*1 PZ 0.0"
    assert Surface(in_str).is_reflecting
    assert Surface(Input([in_str], BlockType.SURFACE)).is_reflecting
    # test white boundary
    in_str = "+1 PZ 0.0"
    assert Surface(in_str).is_white_boundary
    assert Surface(Input([in_str], BlockType.SURFACE)).is_white_boundary
    # test negative surface
    with pytest.raises(MalformedInputError):
        Surface("-1 PZ 0.0")
    with pytest.raises(MalformedInputError):
        Surface(Input(["-1 PZ 0.0"], BlockType.SURFACE))
    # test bad surface number
    with pytest.raises(MalformedInputError):
        Surface("foo PZ 0.0")
    with pytest.raises(MalformedInputError):
        Surface(Input(["foo PZ 0.0"], BlockType.SURFACE))
    # test bad surface type
    with pytest.raises(MalformedInputError):
        Surface("1 INL 0.0")
    with pytest.raises(MalformedInputError):
        Surface(Input(["1 INL 0.0"], BlockType.SURFACE))


def test_surface_transform_and_periodic():
    # test transform
    in_str = "1 5 PZ 0"
    surf = Surface(in_str)
    assert surf.old_transform_number == 5

    # test periodic surface
    in_str = "1 -5 PZ 0"
    surf = Surface(in_str)
    assert surf.old_periodic_surface == 5


def test_surface_transform_bad():
    in_str = "1 5foo PZ 0"
    with pytest.raises(MalformedInputError):
        Surface(in_str)
    with pytest.raises(MalformedInputError):
        Surface(Input([in_str], BlockType.SURFACE))
    in_str = "+1 PZ foo"
    with pytest.raises(MalformedInputError):
        Surface(in_str)
    with pytest.raises(MalformedInputError):
        Surface(Input([in_str], BlockType.SURFACE))
    surf = Surface(number=5)
    assert surf.number == 5
    # test surface_type setter
    surf = Surface(surface_type="cx")
    assert surf.surface_type == SurfaceType.CX
    surf = Surface(surface_type=SurfaceType.CX)
    assert surf.surface_type == SurfaceType.CX
    with pytest.raises(TypeError):
        Surface(surface_type=5)
    with pytest.raises(ValueError):
        AxisPlane(surface_type="Cx")
    with pytest.raises(ValueError):
        CylinderOnAxis(surface_type="px")
    with pytest.raises(ValueError):
        CylinderParAxis(surface_type="px")


def test_validator():
    surf = Surface()
    # TODO is IllegalState or defaults values more desirable?
    with pytest.raises(montepy.exceptions.IllegalState):
        surf.validate()
    with pytest.raises(montepy.exceptions.IllegalState):
        surf.format_for_mcnp_input((6, 2, 0))
    surf.number = 1
    with pytest.raises(montepy.exceptions.IllegalState):
        surf.validate()
    # cylinder on axis
    surf = CylinderOnAxis(number=5)
    with pytest.raises(montepy.exceptions.IllegalState):
        surf.validate()
    with pytest.raises(montepy.exceptions.IllegalState):
        surf.format_for_mcnp_input((6, 2, 0))
    surf._surface_type = SurfaceType.CX
    with pytest.raises(montepy.exceptions.IllegalState):
        surf.validate()
    # cylinder par axis
    surf = CylinderParAxis(number=5)
    with pytest.raises(montepy.exceptions.IllegalState):
        surf.validate()
    with pytest.raises(montepy.exceptions.IllegalState):
        surf.format_for_mcnp_input((6, 2, 0))
    surf._surface_type = SurfaceType.C_X
    with pytest.raises(montepy.exceptions.IllegalState):
        surf.validate()
    surf.radius = 5.0
    with pytest.raises(montepy.exceptions.IllegalState):
        surf.validate()
    # axis plane
    surf = AxisPlane(number=5)
    with pytest.raises(montepy.exceptions.IllegalState):
        surf.validate()
    with pytest.raises(montepy.exceptions.IllegalState):
        surf.format_for_mcnp_input((6, 2, 0))
    surf._surface_type = SurfaceType.PX
    with pytest.raises(montepy.exceptions.IllegalState):
        surf.validate()
    surf.number = 1
    surf.location = 0.0
    # ensure that this doesn't raise an error
    surf.validate()
    # general plane
    surf = GeneralPlane(number=2)
    with pytest.raises(montepy.exceptions.IllegalState):
        surf.validate()
    with pytest.raises(montepy.exceptions.IllegalState):
        surf.format_for_mcnp_input((6, 2, 0))
    surf._surface_type = SurfaceType.P
    with pytest.raises(montepy.exceptions.IllegalState):
        surf.validate()


def test_surface_constants_setter():
    in_str = "1 PZ 0.0"
    surf = Surface(in_str)
    surf.surface_constants = [10.0]
    assert surf.surface_constants[0] == 10.0
    with pytest.raises(TypeError):
        surf.surface_constants = "foo"
    with pytest.raises(ValueError):
        surf.surface_constants = [1, "foo"]


def test_surface_number_setter():
    in_str = "1 PZ 0.0"
    surf = Surface(in_str)
    surf.number = 20
    assert surf.number == 20
    with pytest.raises(TypeError):
        surf.number = "foo"
    with pytest.raises(ValueError):
        surf.number = -5


def test_surface_surface_type_setter():
    surf = montepy.surfaces.parse_surface("1 PZ 0.0")
    with pytest.raises(ValueError):
        surf.surface_type = "CX"
    with pytest.raises(ValueError):
        surf.surface_type = SurfaceType.CX

    surf = montepy.surfaces.parse_surface("1 PZ 0.0")
    with pytest.raises(ValueError):
        surf.surface_type = "CX"
    with pytest.raises(ValueError):
        surf.surface_type = SurfaceType.CX


def test_surface_constants_setter():
    in_str = "1 PZ 0.0"
    input_obj = Input([in_str], BlockType.SURFACE)
    surf = Surface(input_obj)
    surf.surface_constants = [10.0]
    assert surf.surface_constants[0] == 10.0
    with pytest.raises(TypeError):
        surf.surface_constants = "foo"
    with pytest.raises(ValueError):
        surf.surface_constants = [1, "foo"]


def test_surface_number_setter():
    in_str = "1 PZ 0.0"
    input_obj = Input([in_str], BlockType.SURFACE)
    surf = Surface(input_obj)
    surf.number = 20
    assert surf.number == 20
    with pytest.raises(TypeError):
        surf.number = "foo"
    with pytest.raises(ValueError):
        surf.number = -5


def test_surface_ordering():
    surf1 = Surface("1 PZ 0.0")
    surf2 = Surface("5 PZ 0.0")
    sort_list = sorted([surf2, surf1])
    assert sort_list[0] == surf1
    assert sort_list[1] == surf2


def test_surface_format_for_mcnp():
    surf = Surface("+1 PZ 0.0")
    surf.number = 2
    answer = "+2 PZ 0.0"
    assert surf.format_for_mcnp_input((6, 2, 0))[0] == answer
    surf = Surface("*1 PZ 0.0")
    surf.number = 2
    answer = "*2 PZ 0.0"
    assert surf.format_for_mcnp_input((6, 2, 0))[0] == answer
    # test input mimicry
    surf = Surface("1 PZ 0")
    surf.number = 2
    answer = "2 PZ 0"
    assert surf.format_for_mcnp_input((6, 2, 0))[0] == answer


def test_surface_str():
    surf_white = Surface("+1 PZ 0.0")
    assert str(surf_white) == "SURFACE: 1, PZ"
    assert (
        repr(surf_white)
        == "SURFACE: 1, PZ, periodic surface: None, transform: None, constants: [0.0], Boundary: White"
    )

    surf_ref = Surface("*1 PZ 0.0")
    assert str(surf_ref) == "SURFACE: 1, PZ"
    assert (
        repr(surf_ref)
        == "SURFACE: 1, PZ, periodic surface: None, transform: None, constants: [0.0], Boundary: Reflective"
    )

    surf_ref.is_reflecting = False
    surf_ref.is_white_boundary = False
    assert str(surf_ref) == "SURFACE: 1, PZ"
    assert (
        repr(surf_ref)
        == "SURFACE: 1, PZ, periodic surface: None, transform: None, constants: [0.0], Boundary: None"
    )


def test_surface_builder():
    testers = [
        ("1 PZ 0.0", AxisPlane),
        ("2 Cx 10.0", CylinderOnAxis),
        ("3 C/Z 4 3 5", CylinderParAxis),
        ("6 p 1 2 3 4", GeneralPlane),
        ("10 C/x 25 0 -5", CylinderParAxis),
        ("11 c/Y 25 0 -5", CylinderParAxis),
        ("12 CY 3", CylinderOnAxis),
        ("13 cz 0", CylinderOnAxis),
        ("14 px 1.e-3", AxisPlane),
        ("15 PY .1", AxisPlane),
        ("16 S -1 2+0 -3.0 1", GeneralSphere),
        ("17 1 so 1.e-1", SphereAtOrigin),
        ("18 sx -0.2 +1", SphereOnAxis),
        ("19 sY -0.2 2", SphereOnAxis),
        ("20 Sz -0.2 3.0", SphereOnAxis),
    ]
    for in_str, surf_plane in testers:
        assert isinstance(surface_builder(in_str), surf_plane)


def test_axis_plane_init():
    bad_inputs = ["1 P 0.0", "1 PZ 0.0 10.0"]
    for bad_input in bad_inputs:
        with pytest.raises(ValueError):
            montepy.surfaces.axis_plane.AxisPlane(bad_input)
        with pytest.raises(ValueError):
            montepy.surfaces.axis_plane.AxisPlane(Input([bad_input], BlockType.SURFACE))
    surf = montepy.surfaces.axis_plane.AxisPlane(number=5)
    assert surf.number == 5


def test_cylinder_on_axis_init():
    bad_inputs = ["1 P 0.0", "1 CZ 0.0 10.0"]
    for bad_input in bad_inputs:
        with pytest.raises(ValueError):
            montepy.surfaces.cylinder_on_axis.CylinderOnAxis(bad_input)
        with pytest.raises(ValueError):
            montepy.surfaces.cylinder_on_axis.CylinderOnAxis(bad_input)
    surf = montepy.surfaces.cylinder_on_axis.CylinderOnAxis(number=5)
    assert surf.number == 5


def test_cylinder_par_axis_init():
    bad_inputs = ["1 P 0.0", "1 C/Z 0.0"]
    for bad_input in bad_inputs:
        with pytest.raises(ValueError):
            montepy.surfaces.cylinder_par_axis.CylinderParAxis(bad_input)
        with pytest.raises(ValueError):
            montepy.surfaces.cylinder_par_axis.CylinderParAxis(
                Input([bad_input], BlockType.SURFACE)
            )
    surf = montepy.surfaces.cylinder_par_axis.CylinderParAxis(number=5)
    assert surf.number == 5


def test_gen_plane_init():
    bad_inputs = ["1 PZ 0.0", "1 P 0.0"]
    for bad_input in bad_inputs:
        with pytest.raises(ValueError):
            montepy.surfaces.general_plane.GeneralPlane(bad_input)
        with pytest.raises(ValueError):
            montepy.surfaces.general_plane.GeneralPlane(
                Input([bad_input], BlockType.SURFACE)
            )
    surf = montepy.surfaces.general_plane.GeneralPlane(number=5)
    assert surf.number == 5


def test_axis_plane_location_setter():
    surf = surface_builder("1 PZ 0.0")
    assert surf.location == 0.0
    surf.location = 10.0
    assert surf.location == 10.0
    with pytest.raises(TypeError):
        surf.location = "hi"


def test_general_plane_constants():
    error_inputs = ["16 P 0. 0. 0. 0. 0. 1. 0."]
    warn_inputs = ["17 p 0. 0. 0. 0. 0. 1. 0. 1. 1. 0. 1. 0."]
    for error_input in error_inputs:
        with pytest.raises(ValueError):
            montepy.surfaces.general_plane.GeneralPlane(error_input)
    for warn_input in warn_inputs:
        with pytest.raises(SurfaceConstantsWarning):
            montepy.surfaces.general_plane.GeneralPlane(warn_input)


def test_cylinder_axis_radius_setter():
    surf = surface_builder("1 CZ 5.0")
    assert surf.radius == 5.0
    surf.radius = 3.0
    assert surf.radius == 3.0
    with pytest.raises(TypeError):
        surf.radius = "foo"
    with pytest.raises(ValueError):
        surf.radius = -5.0


def test_cylinder_radius_setter():
    surf = surface_builder("1 c/Z 3.0 4.0 5")
    assert surf.radius == 5.0
    surf.radius = 3.0
    assert surf.radius == 3.0
    with pytest.raises(TypeError):
        surf.radius = "foo"
    with pytest.raises(ValueError):
        surf.radius = -5.0


def test_cylinder_location_setter():
    surf = surface_builder("1 c/Z 3.0 4.0 5")
    assert surf.coordinates == (3.0, 4.0)
    surf.coordinates = [1, 2]
    assert surf.coordinates == (1, 2)
    # test wrong type
    with pytest.raises(TypeError):
        surf.coordinates = "fo"
    # test length issues
    with pytest.raises(ValueError):
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

# Copyright 2024-2025, Battelle Energy Alliance, LLC All Rights Reserved.
import io
from pathlib import Path
import pytest

import montepy
from montepy.exceptions import (
    MalformedInputError,
    SurfaceConstantsWarning,
    IllegalState,
)
from montepy.input_parser.block_type import BlockType
from montepy.input_parser.mcnp_input import Input
from montepy.surfaces.axis_plane import AxisPlane
from montepy.surfaces.cylinder_on_axis import CylinderOnAxis
from montepy.surfaces.cylinder_par_axis import CylinderParAxis
from montepy.surfaces.general_plane import GeneralPlane
from montepy.surfaces.general_sphere import GeneralSphere
from montepy.surfaces.sphere_at_origin import SphereAtOrigin
from montepy.surfaces.sphere_on_axis import SphereOnAxis
from montepy.surfaces.surface import (
    ArbitraryPolyhedron,
    AxisAlignedQuadric,
    Box,
    ConeOnAxis,
    ConeParAxis,
    Ellipsoid,
    GeneralQuadric,
    RectangularParallelepiped,
    RightCircularCylinder,
    RightEllipticalCylinder,
    RightHexagonalPrism,
    SphereMacrobody,
    Surface,
    Torus,
    TruncatedRightCone,
    Wedge,
    XCone,
    XConeParAxis,
    XCylinder,
    XCylinderParAxis,
    XPlane,
    XSphere,
    XTorus,
    YCone,
    YConeParAxis,
    YCylinder,
    YCylinderParAxis,
    YPlane,
    YSphere,
    YTorus,
    ZCone,
    ZConeParAxis,
    ZCylinder,
    ZCylinderParAxis,
    ZPlane,
    ZSphere,
    ZTorus,
)
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
    with pytest.raises(ValueError):
        SphereOnAxis(surface_type="SO")


def test_validator():
    vers = (6, 3, 0)
    surf = Surface()
    # TODO is IllegalState or defaults values more desirable?
    with pytest.raises(IllegalState):
        surf.validate()
    with pytest.raises(IllegalState):
        surf.format_for_mcnp_input(vers)
    surf.number = 1
    with pytest.raises(IllegalState):
        surf.validate()
    # cylinder on axis
    surf = CylinderOnAxis(number=5)
    with pytest.raises(IllegalState):
        surf.validate()
    with pytest.raises(IllegalState):
        surf.format_for_mcnp_input(vers)
    surf._surface_type = SurfaceType.CX
    with pytest.raises(IllegalState):
        surf.validate()
    # cylinder par axis
    surf = CylinderParAxis(number=5)
    with pytest.raises(IllegalState):
        surf.validate()
    with pytest.raises(IllegalState):
        surf.format_for_mcnp_input(vers)
    surf._surface_type = SurfaceType.C_X
    with pytest.raises(IllegalState):
        surf.validate()
    surf.radius = 5.0
    with pytest.raises(IllegalState):
        surf.validate()
    # axis plane
    surf = AxisPlane(number=5)
    with pytest.raises(IllegalState):
        surf.validate()
    with pytest.raises(IllegalState):
        surf.format_for_mcnp_input(vers)
    surf._surface_type = SurfaceType.PX
    with pytest.raises(IllegalState):
        surf.validate()
    surf.number = 1
    surf.location = 0.0
    # ensure that this doesn't raise an error
    surf.validate()
    # general plane
    surf = GeneralPlane(number=2)
    with pytest.raises(IllegalState):
        surf.validate()
    with pytest.raises(IllegalState):
        surf.format_for_mcnp_input(vers)
    surf._surface_type = SurfaceType.P
    with pytest.raises(IllegalState):
        surf.validate()
    # general sphere
    surf = GeneralSphere(number=3)
    with pytest.raises(IllegalState):
        surf.validate()
    surf.surface_type = SurfaceType.S
    with pytest.raises(IllegalState):
        surf.validate()
    surf.radius = 1.0
    with pytest.raises(IllegalState):
        surf.validate()
    with pytest.raises(IllegalState):
        surf.format_for_mcnp_input(vers)
    # sphere at origin
    surf = SphereAtOrigin(number=4)
    with pytest.raises(IllegalState):
        surf.validate()
    surf.surface_type = SurfaceType.SO
    with pytest.raises(IllegalState):
        surf.format_for_mcnp_input(vers)
    # sphere on axis
    surf = SphereOnAxis(number=5)
    with pytest.raises(IllegalState):
        surf.validate()
    surf.surface_type = SurfaceType.SZ
    with pytest.raises(IllegalState):
        surf.validate()
    surf.radius = 1.0
    with pytest.raises(IllegalState):
        surf.validate()
    with pytest.raises(IllegalState):
        surf.format_for_mcnp_input(vers)


def test_surface_constants_setter():
    in_str = "1 PZ 0.0"
    input_obj = Input([in_str], BlockType.SURFACE)
    for arg in (in_str, input_obj):
        surf = Surface(arg)
        surf.surface_constants = [10.0]
        assert surf.surface_constants[0] == 10.0
        with pytest.raises(TypeError):
            surf.surface_constants = "foo"
        with pytest.raises(ValueError):
            surf.surface_constants = [1, "foo"]


def test_surface_number_setter():
    in_str = "1 PZ 0.0"
    input_obj = Input([in_str], BlockType.SURFACE)
    for arg in (in_str, input_obj):
        surf = Surface(arg)
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
            CylinderOnAxis(bad_input)
        with pytest.raises(ValueError):
            CylinderOnAxis(bad_input)
    surf = CylinderOnAxis(number=5)
    assert surf.number == 5


def test_cylinder_par_axis_init():
    bad_inputs = ["1 P 0.0", "1 C/Z 0.0"]
    for bad_input in bad_inputs:
        with pytest.raises(ValueError):
            CylinderParAxis(bad_input)
        with pytest.raises(ValueError):
            CylinderParAxis(Input([bad_input], BlockType.SURFACE))
    surf = CylinderParAxis(number=5)
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


def test_gen_sphere_init():
    bad_input = "1 S 0.0"
    with pytest.raises(ValueError):
        GeneralSphere(bad_input)
    with pytest.raises(ValueError):
        GeneralSphere(Input([bad_input], BlockType.SURFACE))
    surf = GeneralSphere(number=5)
    assert surf.number == 5


def test_axis_sphere_init():
    bad_input = "1 SZ 0.0"
    with pytest.raises(ValueError):
        SphereOnAxis(bad_input)
    with pytest.raises(ValueError):
        SphereOnAxis(Input([bad_input], BlockType.SURFACE))
    surf = SphereOnAxis(number=5)
    assert surf.number == 5


def test_origin_sphere_init():
    bad_input = "1 SO 0.0 0.1 1.0"
    with pytest.raises(ValueError):
        SphereAtOrigin(bad_input)
    with pytest.raises(ValueError):
        SphereAtOrigin(Input([bad_input], BlockType.SURFACE))
    surf = SphereAtOrigin(number=5)
    assert surf.number == 5


def test_axis_plane_location_setter():
    surf = surface_builder("1 PZ 0.0")
    assert surf.location == 0.0
    surf.location = 10.0
    assert surf.location == 10.0
    with pytest.raises(TypeError):
        surf.location = "hi"


def test_sphere_radius_setter():
    for sphere_string in (
        "1 S  0.0 -1.0 2.0 5.0",
        "1 SX 0.0          5.0",
        "1 SO              5.0",
    ):
        surf = surface_builder(sphere_string)
        assert surf.radius == 5.0
        surf.radius = 3.0
        assert surf.radius == 3.0
        with pytest.raises(TypeError):
            surf.radius = "foo"
        with pytest.raises(ValueError):
            surf.radius = -5.0


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


def test_sphere_coordinate_setter():
    surf = surface_builder("1 S 3.0 4.0 5 6e0")
    assert surf.coordinates == (3.0, 4.0, 5)
    surf.coordinates = [1, 2, 3]
    assert surf.coordinates == (1, 2, 3)
    # test wrong type
    with pytest.raises(TypeError):
        surf.coordinates = 6
    with pytest.raises(TypeError):
        surf.coordinates = (6, 7, "eight")
    # test length issues
    with pytest.raises(ValueError):
        surf.coordinates = [6, 7]


def test_sphere_location_setter():
    surf = surface_builder("1 SX 3.0 6e0")
    assert surf.location == 3.0
    surf.location = 4.0
    assert surf.location == 4.0
    # test length issues
    with pytest.raises(TypeError):
        surf.location = "over there"


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
        (XCylinder, SurfaceType.CX, {"radius": 0.5}),
        (YCylinder, SurfaceType.CY, {"radius": 0.5}),
        (ZCylinder, SurfaceType.CZ, {"radius": 0.5}),
        (XConeParAxis, SurfaceType.K_X, {"apex": (1.0, 2.0, 3.0), "t_squared": 0.25}),
        (YConeParAxis, SurfaceType.K_Y, {"apex": (1.0, 2.0, 3.0), "t_squared": 0.25}),
        (ZConeParAxis, SurfaceType.K_Z, {"apex": (1.0, 2.0, 3.0), "t_squared": 0.25}),
        (
            XTorus,
            SurfaceType.TX,
            {"center": (0.0, 0.0, 0.0), "major_radius": 5.0, "minor_radii": [2.0, 2.0]},
        ),
        (
            YTorus,
            SurfaceType.TY,
            {"center": (0.0, 0.0, 0.0), "major_radius": 5.0, "minor_radii": [2.0, 2.0]},
        ),
        (
            ZTorus,
            SurfaceType.TZ,
            {"center": (0.0, 0.0, 0.0), "major_radius": 5.0, "minor_radii": [2.0, 2.0]},
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
        assert new_surf.old_periodic_surface is None
    if surf.transform:
        assert surf.transform.number == new_surf.old_transform_number
    else:
        assert new_surf.old_transform_number is None


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


@pytest.mark.parametrize(
    "in_str,expected",
    [
        ("1 so 0.0", "1 so 0.0"),
        ("1 sO 0.0", "1 sO 0.0"),
        ("1 So 0.0", "1 So 0.0"),
        ("1 SO 0.0", "1 SO 0.0"),
        ("1 pz 0.0", "1 pz 0.0"),
        ("1 PZ 0.0", "1 PZ 0.0"),
        ("1 Pz 0.0", "1 Pz 0.0"),
    ],
)
def test_surface_preserves_mnemonic_case(in_str, expected):
    """Surface mnemonics should be written with the original case (issue #522)."""
    surf = Surface(in_str)
    assert surf.mcnp_str() == expected


# ---------------------------------------------------------------------------
# Tests for all new surface classes generated by _SurfaceClassFactory
# ---------------------------------------------------------------------------

# fmt: off
@pytest.mark.parametrize("surf_str, expected_cls", [
    # axis-specific dispatch
    ("1 PX 1.0",                  XPlane),
    ("1 PY 1.0",                  YPlane),
    ("1 PZ 1.0",                  ZPlane),
    ("1 CX 1.0",                  XCylinder),
    ("1 CY 1.0",                  YCylinder),
    ("1 CZ 1.0",                  ZCylinder),
    ("1 C/X 1.0 2.0 3.0",        XCylinderParAxis),
    ("1 C/Y 1.0 2.0 3.0",        YCylinderParAxis),
    ("1 C/Z 1.0 2.0 3.0",        ZCylinderParAxis),
    ("1 SX 1.0 2.0",              XSphere),
    ("1 SY 1.0 2.0",              YSphere),
    ("1 SZ 1.0 2.0",              ZSphere),
    ("1 KX 1.0 0.25",             XCone),
    ("1 KY 1.0 0.25",             YCone),
    ("1 KZ 1.0 0.25",             ZCone),
    ("1 K/X 1.0 2.0 3.0 0.25",   XConeParAxis),
    ("1 K/Y 1.0 2.0 3.0 0.25",   YConeParAxis),
    ("1 K/Z 1.0 2.0 3.0 0.25",   ZConeParAxis),
    ("1 TX 0 0 0 5 2 2",          XTorus),
    ("1 TY 0 0 0 5 2 2",          YTorus),
    ("1 TZ 0 0 0 5 2 2",          ZTorus),
    # generic grouped dispatch
    ("1 SO 1.0",                  SphereAtOrigin),
    ("1 S 1 2 3 4",               GeneralSphere),
    ("1 P 1 0 0 5",               GeneralPlane),
    ("1 SQ 1 1 1 0 0 0 -4 0 0 0", AxisAlignedQuadric),
    ("1 GQ 1 1 1 0 0 0 0 0 0 -4", GeneralQuadric),
    ("1 BOX 0 0 0 1 0 0 0 1 0 0 0 1", Box),
    ("1 RPP -1 1 -1 1 -1 1",      RectangularParallelepiped),
    ("1 SPH 0 0 0 1",              SphereMacrobody),
    ("1 RCC 0 0 0 0 0 1 1",       RightCircularCylinder),
    ("1 REC 0 0 0 0 0 1 1 0 0 0 0.5 0", RightEllipticalCylinder),
    ("1 TRC 0 0 0 0 0 1 2 1",     TruncatedRightCone),
    ("1 ELL -1 0 0 1 0 0 5",      Ellipsoid),
    ("1 WED 0 0 0 1 0 0 0 1 0 0 0 1", Wedge),
])
def test_surface_dispatch(surf_str, expected_cls):
    """surface_builder returns the correct specific class for every surface type."""
    surf = surface_builder(surf_str)
    assert isinstance(surf, expected_cls), (
        f"Expected {expected_cls.__name__}, got {type(surf).__name__}"
    )


# Scalar property tests: (surf_str, prop, expected_val, new_val, rejects_negative)
# rejects_negative=True means the property has a positive-value validator.
_SCALAR_PROPS = [
    # XPlane — location and x are the same node
    ("1 PX 1.0",  "location", 1.0, 2.0,  False),
    ("1 PX 1.0",  "x",        1.0, 2.0,  False),
    # YPlane
    ("1 PY 2.0",  "location", 2.0, 3.0,  False),
    ("1 PY 2.0",  "y",        2.0, 3.0,  False),
    # ZPlane
    ("1 PZ 3.0",  "location", 3.0, 4.0,  False),
    ("1 PZ 3.0",  "z",        3.0, 4.0,  False),
    # AxisPlane (d alias)
    ("1 PZ 3.0",  "d",        3.0, 4.0,  False),
    # GeneralPlane coefficients
    ("1 P 1.0 0.0 0.0 5.0", "A", 1.0, 2.0, False),
    ("1 P 1.0 0.0 0.0 5.0", "B", 0.0, 1.0, False),
    ("1 P 1.0 0.0 0.0 5.0", "C", 0.0, 1.0, False),
    ("1 P 1.0 0.0 0.0 5.0", "D", 5.0, 3.0, False),
    # SphereAtOrigin
    ("1 SO 2.0",  "radius",   2.0, 3.0,  True),
    # GeneralSphere
    ("1 S 1.0 2.0 3.0 4.0", "x",      1.0, 5.0, False),
    ("1 S 1.0 2.0 3.0 4.0", "y",      2.0, 6.0, False),
    ("1 S 1.0 2.0 3.0 4.0", "z",      3.0, 7.0, False),
    ("1 S 1.0 2.0 3.0 4.0", "radius", 4.0, 1.0, True),
    # XSphere — location and x share node
    ("1 SX 5.0 2.0", "location", 5.0, 6.0, False),
    ("1 SX 5.0 2.0", "x",        5.0, 6.0, False),
    ("1 SX 5.0 2.0", "radius",   2.0, 3.0, True),
    # YSphere
    ("1 SY 5.0 2.0", "location", 5.0, 6.0, False),
    ("1 SY 5.0 2.0", "y",        5.0, 6.0, False),
    ("1 SY 5.0 2.0", "radius",   2.0, 3.0, True),
    # ZSphere
    ("1 SZ 5.0 2.0", "location", 5.0, 6.0, False),
    ("1 SZ 5.0 2.0", "z",        5.0, 6.0, False),
    ("1 SZ 5.0 2.0", "radius",   2.0, 3.0, True),
    # XCylinder / YCylinder / ZCylinder
    ("1 CX 3.0", "radius", 3.0, 5.0, True),
    ("1 CY 3.0", "radius", 3.0, 5.0, True),
    ("1 CZ 3.0", "radius", 3.0, 5.0, True),
    # XCylinderParAxis — y, z map to coordinates[0], coordinates[1]
    ("1 C/X 1.0 2.0 3.0", "y",      1.0, 4.0, False),
    ("1 C/X 1.0 2.0 3.0", "z",      2.0, 5.0, False),
    ("1 C/X 1.0 2.0 3.0", "radius", 3.0, 6.0, True),
    # YCylinderParAxis
    ("1 C/Y 1.0 2.0 3.0", "x",      1.0, 4.0, False),
    ("1 C/Y 1.0 2.0 3.0", "z",      2.0, 5.0, False),
    ("1 C/Y 1.0 2.0 3.0", "radius", 3.0, 6.0, True),
    # ZCylinderParAxis
    ("1 C/Z 1.0 2.0 3.0", "x",      1.0, 4.0, False),
    ("1 C/Z 1.0 2.0 3.0", "y",      2.0, 5.0, False),
    ("1 C/Z 1.0 2.0 3.0", "radius", 3.0, 6.0, True),
    # XCone — apex and x share node
    ("1 KX 5.0 0.25", "apex",      5.0,  6.0,  False),
    ("1 KX 5.0 0.25", "x",         5.0,  6.0,  False),
    ("1 KX 5.0 0.25", "t_squared", 0.25, 0.5,  False),
    # YCone
    ("1 KY 5.0 0.25", "apex",      5.0,  6.0,  False),
    ("1 KY 5.0 0.25", "y",         5.0,  6.0,  False),
    ("1 KY 5.0 0.25", "t_squared", 0.25, 0.5,  False),
    # ZCone
    ("1 KZ 5.0 0.25", "apex",      5.0,  6.0,  False),
    ("1 KZ 5.0 0.25", "z",         5.0,  6.0,  False),
    ("1 KZ 5.0 0.25", "t_squared", 0.25, 0.5,  False),
    # XConeParAxis (inherits x,y,z,t_squared from ConeParAxis spec)
    ("1 K/X 1.0 2.0 3.0 0.25", "x",         1.0,  4.0,  False),
    ("1 K/X 1.0 2.0 3.0 0.25", "y",         2.0,  5.0,  False),
    ("1 K/X 1.0 2.0 3.0 0.25", "z",         3.0,  6.0,  False),
    ("1 K/X 1.0 2.0 3.0 0.25", "t_squared", 0.25, 0.5,  False),
    # YConeParAxis
    ("1 K/Y 1.0 2.0 3.0 0.25", "x",         1.0,  4.0,  False),
    ("1 K/Y 1.0 2.0 3.0 0.25", "y",         2.0,  5.0,  False),
    ("1 K/Y 1.0 2.0 3.0 0.25", "z",         3.0,  6.0,  False),
    ("1 K/Y 1.0 2.0 3.0 0.25", "t_squared", 0.25, 0.5,  False),
    # ZConeParAxis
    ("1 K/Z 1.0 2.0 3.0 0.25", "x",         1.0,  4.0,  False),
    ("1 K/Z 1.0 2.0 3.0 0.25", "y",         2.0,  5.0,  False),
    ("1 K/Z 1.0 2.0 3.0 0.25", "z",         3.0,  6.0,  False),
    ("1 K/Z 1.0 2.0 3.0 0.25", "t_squared", 0.25, 0.5,  False),
    # AxisAlignedQuadric
    ("1 SQ 1 1 1 0 0 0 -4 0 0 0", "A", 1.0,  2.0,  False),
    ("1 SQ 1 1 1 0 0 0 -4 0 0 0", "B", 1.0,  2.0,  False),
    ("1 SQ 1 1 1 0 0 0 -4 0 0 0", "C", 1.0,  2.0,  False),
    ("1 SQ 1 1 1 0 0 0 -4 0 0 0", "D", 0.0,  1.0,  False),
    ("1 SQ 1 1 1 0 0 0 -4 0 0 0", "E", 0.0,  1.0,  False),
    ("1 SQ 1 1 1 0 0 0 -4 0 0 0", "F", 0.0,  1.0,  False),
    ("1 SQ 1 1 1 0 0 0 -4 0 0 0", "G", -4.0, -1.0, False),
    ("1 SQ 1 1 1 0 0 0 -4 0 0 0", "x", 0.0,  1.0,  False),
    ("1 SQ 1 1 1 0 0 0 -4 0 0 0", "y", 0.0,  2.0,  False),
    ("1 SQ 1 1 1 0 0 0 -4 0 0 0", "z", 0.0,  3.0,  False),
    # GeneralQuadric
    ("1 GQ 1 1 1 0 0 0 0 0 0 -4", "A", 1.0,  2.0,  False),
    ("1 GQ 1 1 1 0 0 0 0 0 0 -4", "B", 1.0,  2.0,  False),
    ("1 GQ 1 1 1 0 0 0 0 0 0 -4", "C", 1.0,  2.0,  False),
    ("1 GQ 1 1 1 0 0 0 0 0 0 -4", "D", 0.0,  1.0,  False),
    ("1 GQ 1 1 1 0 0 0 0 0 0 -4", "E", 0.0,  1.0,  False),
    ("1 GQ 1 1 1 0 0 0 0 0 0 -4", "F", 0.0,  1.0,  False),
    ("1 GQ 1 1 1 0 0 0 0 0 0 -4", "G", 0.0,  1.0,  False),
    ("1 GQ 1 1 1 0 0 0 0 0 0 -4", "H", 0.0,  1.0,  False),
    ("1 GQ 1 1 1 0 0 0 0 0 0 -4", "J", 0.0,  1.0,  False),
    ("1 GQ 1 1 1 0 0 0 0 0 0 -4", "K", -4.0, -1.0, False),
    # XTorus — x/y/z, major_radius, minor_radius_1/2, minor_radius
    ("1 TX 0 0 0 5 2 2", "x",             0.0, 1.0, False),
    ("1 TX 0 0 0 5 2 2", "y",             0.0, 2.0, False),
    ("1 TX 0 0 0 5 2 2", "z",             0.0, 3.0, False),
    ("1 TX 0 0 0 5 2 2", "major_radius",  5.0, 6.0, True),
    ("1 TX 0 0 0 5 2 2", "minor_radius_1", 2.0, 1.0, True),
    ("1 TX 0 0 0 5 2 2", "minor_radius_2", 2.0, 1.0, True),
    ("1 TX 0 0 0 5 2 2", "minor_radius",  2.0, 3.0, True),
    # YTorus / ZTorus — spot check major_radius
    ("1 TY 0 0 0 5 2 2", "major_radius",  5.0, 6.0, True),
    ("1 TZ 0 0 0 5 2 2", "major_radius",  5.0, 6.0, True),
    # RPP scalars
    ("1 RPP -1 1 -2 2 -3 3", "x_min", -1.0, -5.0, False),
    ("1 RPP -1 1 -2 2 -3 3", "x_max",  1.0,  5.0, False),
    ("1 RPP -1 1 -2 2 -3 3", "y_min", -2.0, -5.0, False),
    ("1 RPP -1 1 -2 2 -3 3", "y_max",  2.0,  5.0, False),
    ("1 RPP -1 1 -2 2 -3 3", "z_min", -3.0, -5.0, False),
    ("1 RPP -1 1 -2 2 -3 3", "z_max",  3.0,  5.0, False),
    # SPH scalars
    ("1 SPH 1 2 3 4", "x",      1.0, 5.0, False),
    ("1 SPH 1 2 3 4", "y",      2.0, 6.0, False),
    ("1 SPH 1 2 3 4", "z",      3.0, 7.0, False),
    ("1 SPH 1 2 3 4", "radius", 4.0, 2.0, True),
    # RCC scalars
    ("1 RCC 1 2 3 0 0 1 1.5", "x",      1.0, 5.0, False),
    ("1 RCC 1 2 3 0 0 1 1.5", "y",      2.0, 6.0, False),
    ("1 RCC 1 2 3 0 0 1 1.5", "z",      3.0, 7.0, False),
    ("1 RCC 1 2 3 0 0 1 1.5", "radius", 1.5, 2.0, True),
    # RHP scalars
    ("1 RHP 0 0 0 0 0 1 1 0 0 -0.5 0.866 0 -0.5 -0.866 0", "x", 0.0, 1.0, False),
    ("1 RHP 0 0 0 0 0 1 1 0 0 -0.5 0.866 0 -0.5 -0.866 0", "y", 0.0, 2.0, False),
    ("1 RHP 0 0 0 0 0 1 1 0 0 -0.5 0.866 0 -0.5 -0.866 0", "z", 0.0, 3.0, False),
    # REC scalars
    ("1 REC 0 0 0 0 0 1 1 0 0 0 0.5 0", "x", 0.0, 1.0, False),
    ("1 REC 0 0 0 0 0 1 1 0 0 0 0.5 0", "y", 0.0, 2.0, False),
    ("1 REC 0 0 0 0 0 1 1 0 0 0 0.5 0", "z", 0.0, 3.0, False),
    # TRC scalars
    ("1 TRC 0 0 0 0 0 1 2 1", "x",           0.0, 1.0, False),
    ("1 TRC 0 0 0 0 0 1 2 1", "y",           0.0, 2.0, False),
    ("1 TRC 0 0 0 0 0 1 2 1", "z",           0.0, 3.0, False),
    ("1 TRC 0 0 0 0 0 1 2 1", "base_radius", 2.0, 3.0, True),
    ("1 TRC 0 0 0 0 0 1 2 1", "top_radius",  1.0, 0.5, True),
    # ELL scalar
    ("1 ELL -1 0 0 1 0 0 5", "semi_major_axis", 5.0, 6.0, False),
    # ARB facet scalars
    ("1 ARB 0 0 0 1 0 0 1 1 0 0 1 0 0 0 1 1 0 1 1 1 1 0 1 1 1234 1265 2376 3487 4158 5678",
     "facet_1", 1234.0, 1235.0, False),
    ("1 ARB 0 0 0 1 0 0 1 1 0 0 1 0 0 0 1 1 0 1 1 1 1 0 1 1 1234 1265 2376 3487 4158 5678",
     "facet_6", 5678.0, 5679.0, False),
]
# fmt: on


@pytest.mark.parametrize(
    "surf_str, prop, expected, new_val, rejects_negative", _SCALAR_PROPS
)
def test_surface_scalar_prop(surf_str, prop, expected, new_val, rejects_negative):
    surf = surface_builder(surf_str)
    assert getattr(surf, prop) == pytest.approx(
        expected
    ), f"{type(surf).__name__}.{prop}: expected {expected}"
    setattr(surf, prop, new_val)
    assert getattr(surf, prop) == pytest.approx(
        new_val
    ), f"{type(surf).__name__}.{prop}: value not updated after set"
    with pytest.raises(TypeError):
        setattr(surf, prop, "bad")
    if rejects_negative:
        with pytest.raises(ValueError):
            setattr(surf, prop, -1.0)


# fmt: off
# Tuple property tests: (surf_str, prop, expected_tuple, new_tuple)
_TUPLE_PROPS = [
    # GeneralPlane normal
    ("1 P 1 0 0 5",  "normal",      (1.0, 0.0, 0.0), [2.0, 1.0, 0.0]),
    # GeneralSphere center / coordinates
    ("1 S 1 2 3 4",  "center",      (1.0, 2.0, 3.0), [4.0, 5.0, 6.0]),
    ("1 S 1 2 3 4",  "coordinates", (1.0, 2.0, 3.0), [4.0, 5.0, 6.0]),
    # XCylinderParAxis — coordinates shares storage with y/z
    ("1 C/X 1 2 3",  "coordinates", (1.0, 2.0),       [3.0, 4.0]),
    # YCylinderParAxis
    ("1 C/Y 1 2 3",  "coordinates", (1.0, 2.0),       [3.0, 4.0]),
    # ZCylinderParAxis
    ("1 C/Z 1 2 3",  "coordinates", (1.0, 2.0),       [3.0, 4.0]),
    # ConeParAxis apex tuple
    ("1 K/X 1 2 3 0.25", "apex",    (1.0, 2.0, 3.0), [4.0, 5.0, 6.0]),
    ("1 K/Y 1 2 3 0.25", "apex",    (1.0, 2.0, 3.0), [4.0, 5.0, 6.0]),
    ("1 K/Z 1 2 3 0.25", "apex",    (1.0, 2.0, 3.0), [4.0, 5.0, 6.0]),
    # AxisAlignedQuadric center
    ("1 SQ 1 1 1 0 0 0 -4 1 2 3", "center", (1.0, 2.0, 3.0), [4.0, 5.0, 6.0]),
    # Torus center and minor_radii
    ("1 TX 1 2 3 5 2 2", "center",      (1.0, 2.0, 3.0), [4.0, 5.0, 6.0]),
    ("1 TX 0 0 0 5 2 2", "minor_radii", (2.0, 2.0),       [1.0, 1.0]),
    # Box tuples
    ("1 BOX 0 0 0 1 0 0 0 1 0 0 0 1", "corner", (0.0, 0.0, 0.0), [1.0, 1.0, 1.0]),
    ("1 BOX 0 0 0 1 0 0 0 1 0 0 0 1", "edge_1", (1.0, 0.0, 0.0), [2.0, 0.0, 0.0]),
    ("1 BOX 0 0 0 1 0 0 0 1 0 0 0 1", "edge_2", (0.0, 1.0, 0.0), [0.0, 2.0, 0.0]),
    ("1 BOX 0 0 0 1 0 0 0 1 0 0 0 1", "edge_3", (0.0, 0.0, 1.0), [0.0, 0.0, 2.0]),
    # RPP bounds tuples
    ("1 RPP -1 1 -2 2 -3 3", "x_bounds", (-1.0, 1.0), [-2.0, 2.0]),
    ("1 RPP -1 1 -2 2 -3 3", "y_bounds", (-2.0, 2.0), [-3.0, 3.0]),
    ("1 RPP -1 1 -2 2 -3 3", "z_bounds", (-3.0, 3.0), [-4.0, 4.0]),
    # SphereMacrobody center
    ("1 SPH 1 2 3 4",  "center",        (1.0, 2.0, 3.0), [4.0, 5.0, 6.0]),
    # RCC tuples
    ("1 RCC 1 2 3 0 0 1 1.5", "center",        (1.0, 2.0, 3.0), [4.0, 5.0, 6.0]),
    ("1 RCC 1 2 3 0 0 1 1.5", "height_vector", (0.0, 0.0, 1.0), [0.0, 1.0, 0.0]),
    # RHP tuples
    ("1 RHP 0 0 0 0 0 1 1 0 0 -0.5 0.866 0 -0.5 -0.866 0",
     "center",        (0.0, 0.0, 0.0), [1.0, 1.0, 1.0]),
    ("1 RHP 0 0 0 0 0 1 1 0 0 -0.5 0.866 0 -0.5 -0.866 0",
     "height_vector", (0.0, 0.0, 1.0), [0.0, 1.0, 0.0]),
    ("1 RHP 0 0 0 0 0 1 1 0 0 -0.5 0.866 0 -0.5 -0.866 0",
     "facet_vector_1", (1.0, 0.0, 0.0), [2.0, 0.0, 0.0]),
    # REC tuples
    ("1 REC 0 0 0 0 0 1 1 0 0 0 0.5 0", "center",         (0.0, 0.0, 0.0), [1.0, 1.0, 1.0]),
    ("1 REC 0 0 0 0 0 1 1 0 0 0 0.5 0", "height_vector",  (0.0, 0.0, 1.0), [0.0, 1.0, 0.0]),
    ("1 REC 0 0 0 0 0 1 1 0 0 0 0.5 0", "semi_major_axis", (1.0, 0.0, 0.0), [2.0, 0.0, 0.0]),
    ("1 REC 0 0 0 0 0 1 1 0 0 0 0.5 0", "semi_minor_axis", (0.0, 0.5, 0.0), [0.0, 1.0, 0.0]),
    # TRC tuples
    ("1 TRC 0 0 0 0 0 1 2 1", "center",        (0.0, 0.0, 0.0), [1.0, 1.0, 1.0]),
    ("1 TRC 0 0 0 0 0 1 2 1", "height_vector", (0.0, 0.0, 1.0), [0.0, 1.0, 0.0]),
    # ELL tuples
    ("1 ELL -1 0 0 1 0 0 5", "focus_1", (-1.0, 0.0, 0.0), [0.0, -1.0, 0.0]),
    ("1 ELL -1 0 0 1 0 0 5", "focus_2", ( 1.0, 0.0, 0.0), [0.0,  1.0, 0.0]),
    # Wedge tuples
    ("1 WED 0 0 0 1 0 0 0 1 0 0 0 1", "corner",        (0.0, 0.0, 0.0), [1.0, 1.0, 1.0]),
    ("1 WED 0 0 0 1 0 0 0 1 0 0 0 1", "edge_1",        (1.0, 0.0, 0.0), [2.0, 0.0, 0.0]),
    ("1 WED 0 0 0 1 0 0 0 1 0 0 0 1", "edge_2",        (0.0, 1.0, 0.0), [0.0, 2.0, 0.0]),
    ("1 WED 0 0 0 1 0 0 0 1 0 0 0 1", "height_vector", (0.0, 0.0, 1.0), [0.0, 0.0, 2.0]),
    # ARB vertex tuples
    ("1 ARB 0 0 0 1 0 0 1 1 0 0 1 0 0 0 1 1 0 1 1 1 1 0 1 1 1234 1265 2376 3487 4158 5678",
     "vertex_1", (0.0, 0.0, 0.0), [1.0, 1.0, 1.0]),
    ("1 ARB 0 0 0 1 0 0 1 1 0 0 1 0 0 0 1 1 0 1 1 1 1 0 1 1 1234 1265 2376 3487 4158 5678",
     "vertex_8", (0.0, 1.0, 1.0), [1.0, 2.0, 2.0]),
]
# fmt: on


@pytest.mark.parametrize("surf_str, prop, expected, new_val", _TUPLE_PROPS)
def test_surface_tuple_prop(surf_str, prop, expected, new_val):
    surf = surface_builder(surf_str)
    actual = getattr(surf, prop)
    assert len(actual) == len(
        expected
    ), f"{type(surf).__name__}.{prop}: length mismatch"
    for a, e in zip(actual, expected):
        assert a == pytest.approx(
            e
        ), f"{type(surf).__name__}.{prop}: expected {expected}, got {actual}"
    setattr(surf, prop, new_val)
    updated = getattr(surf, prop)
    for a, e in zip(updated, new_val):
        assert a == pytest.approx(
            e
        ), f"{type(surf).__name__}.{prop}: value not updated after set"
    # wrong type for an element
    with pytest.raises(TypeError):
        setattr(surf, prop, ["bad"] * len(new_val))
    # wrong length
    with pytest.raises(ValueError):
        setattr(surf, prop, new_val + [0.0])


def test_torus_minor_radius_mismatch():
    """minor_radius getter raises ValueError when the two minor radii differ."""
    surf = surface_builder("1 TX 0 0 0 5 2 3")
    with pytest.raises(ValueError):
        _ = surf.minor_radius


def test_torus_minor_radius_setter_syncs_both():
    """Setting minor_radius updates both minor_radius_1 and minor_radius_2."""
    surf = surface_builder("1 TX 0 0 0 5 2 2")
    surf.minor_radius = 1.5
    assert surf.minor_radius_1 == pytest.approx(1.5)
    assert surf.minor_radius_2 == pytest.approx(1.5)
    assert surf.minor_radius == pytest.approx(1.5)


def test_torus_minor_radii_rejects_negative():
    surf = surface_builder("1 TX 0 0 0 5 2 2")
    with pytest.raises(ValueError):
        surf.minor_radii = [2.0, -1.0]


def test_axis_specific_overlapping_nodes():
    """Setting the axis-named prop and the generic prop both update the same node."""
    # ZPlane: location and z share the same ValueNode
    surf = surface_builder("1 PZ 5.0")
    surf.z = 10.0
    assert surf.location == pytest.approx(10.0)
    surf.location = 20.0
    assert surf.z == pytest.approx(20.0)

    # XSphere: x and location share the same ValueNode
    surf = surface_builder("1 SX 3.0 1.0")
    surf.x = 7.0
    assert surf.location == pytest.approx(7.0)

    # XCylinderParAxis: y/z share coordinates[0]/[1]
    surf = surface_builder("1 C/X 1.0 2.0 3.0")
    surf.y = 9.0
    assert surf.coordinates[0] == pytest.approx(9.0)
    surf.z = 8.0
    assert surf.coordinates[1] == pytest.approx(8.0)


def test_simple_problem_parses_all_surface_types(simple_problem):
    """test.imcnp round-trip: every new surface number is present and parseable."""
    expected = set(range(2000, 2036))
    actual = set(simple_problem.surfaces.numbers)
    assert expected.issubset(actual), f"Missing surface numbers: {expected - actual}"


@pytest.mark.parametrize(
    "surf_str, absent_idx",
    [
        ("1 KZ 0.0 1.0", 2),
        ("1 K/Z 0.0 0.0 0.0 0.25", 4),
    ],
)
def test_cone_sign_absent(surf_str, absent_idx):
    """sign returns None when the optional nappe flag is not present."""
    surf = surface_builder(surf_str)
    assert surf.sign is None


@pytest.mark.parametrize(
    "surf_str, expected_sign",
    [
        ("1 KZ 0.0 1.0 1", 1),
        ("1 KZ 0.0 1.0 -1", -1),
        ("1 K/Z 0.0 0.0 0.0 0.25 1", 1),
        ("1 K/Z 0.0 0.0 0.0 0.25 -1", -1),
    ],
)
def test_cone_sign_present(surf_str, expected_sign):
    """sign reads +1 or -1 from input when the nappe flag is given."""
    surf = surface_builder(surf_str)
    assert surf.sign == expected_sign


@pytest.mark.filterwarnings("ignore")
@pytest.mark.parametrize(
    "surf_str",
    [
        "1 KZ 0.0 1.0",
        "1 K/Z 0.0 0.0 0.0 0.25",
    ],
)
def test_cone_sign_setter_and_round_trip(surf_str):
    """Setting sign appends the nappe flag and survives an export/re-parse round-trip."""
    surf = surface_builder(surf_str)
    surf.sign = 1
    assert surf.sign == 1
    verify_export(surf)

    surf.sign = -1
    assert surf.sign == -1
    verify_export(surf)


@pytest.mark.parametrize(
    "surf_str",
    [
        "1 KZ 0.0 1.0",
        "1 K/Z 0.0 0.0 0.0 0.25",
    ],
)
def test_cone_sign_setter_none_clears(surf_str):
    """Setting sign to None removes the nappe flag."""
    surf = surface_builder(surf_str)
    surf.sign = 1
    assert surf.sign == 1
    surf.sign = None
    assert surf.sign is None
    verify_export(surf)


@pytest.mark.parametrize(
    "surf_str",
    [
        "1 KZ 0.0 1.0 1",
        "1 K/Z 0.0 0.0 0.0 0.25 1",
    ],
)
def test_cone_sign_deleter(surf_str):
    """Deleting sign removes the nappe flag and round-trip survives."""
    surf = surface_builder(surf_str)
    assert surf.sign is not None
    del surf.sign
    assert surf.sign is None
    verify_export(surf)


@pytest.mark.parametrize(
    "surf_str",
    [
        "1 KZ 0.0 1.0",
        "1 K/Z 0.0 0.0 0.0 0.25",
    ],
)
def test_cone_sign_invalid_raises(surf_str):
    """sign setter rejects values other than +1 or -1."""
    surf = surface_builder(surf_str)
    with pytest.raises(ValueError):
        surf.sign = 2
    with pytest.raises(ValueError):
        surf.sign = 0


@pytest.mark.parametrize(
    "surf_str",
    [
        "1 KZ 0.0 1.0 0.0 0.0",  # ConeOnAxis: 4 params (needs 2 or 3)
        "1 K/Z 0.0 0.0 0.0 0.25 1 1",  # ConeParAxis: 6 params (needs 4 or 5)
    ],
)
def test_cone_enforce_constants_wrong_count(surf_str):
    """Cones with the wrong number of surface constants raise ValueError."""
    with pytest.raises(ValueError):
        surface_builder(surf_str)


@pytest.mark.parametrize(
    "cls, surf_type",
    [
        (ConeOnAxis, SurfaceType.KZ),
        (ConeParAxis, SurfaceType.K_Z),
    ],
)
def test_cone_validate_apex_none(cls, surf_type):
    """validate() raises IllegalState when apex is not set."""
    surf = cls(number=5)
    surf.surface_type = surf_type
    with pytest.raises(IllegalState):
        surf.validate()


@pytest.mark.parametrize(
    "cls, surf_type, apex_val",
    [
        (ConeOnAxis, SurfaceType.KZ, 0.0),
        (ConeParAxis, SurfaceType.K_Z, [0.0, 0.0, 0.0]),
    ],
)
def test_cone_validate_t_squared_none(cls, surf_type, apex_val):
    """validate() raises IllegalState when apex is set but t_squared is not."""
    surf = cls(number=5)
    surf.surface_type = surf_type
    surf.apex = apex_val
    with pytest.raises(IllegalState):
        surf.validate()


@pytest.mark.parametrize(
    "cls, surf_type, extra_count",
    [
        (ConeOnAxis, SurfaceType.KZ, 2),  # 0+2=2, then add 2 more → 4, not in {2,3}
        (ConeParAxis, SurfaceType.K_Z, 2),  # 0+2=2, then add 2 more → 4, not in {4,5}
    ],
)
def test_cone_enforce_constants_illegal_state(cls, surf_type, extra_count):
    """validate() raises IllegalState when _surface_constants has wrong count."""
    surf = cls(number=5)
    surf.surface_type = surf_type
    for _ in range(extra_count):
        node = surf._generate_default_node(float, 0.0)
        surf._surface_constants.append(node)
        surf._tree["data"].append(node)
    with pytest.raises(IllegalState):
        surf.validate()

# Copyright 2024, Battelle Energy Alliance, LLC All Rights Reserved.
import pytest

import montepy

from montepy.data_inputs.element import Element
from montepy.data_inputs.isotope import Isotope, Library
from montepy.data_inputs.material import Material
from montepy.data_inputs.material_component import MaterialComponent
from montepy.data_inputs.thermal_scattering import ThermalScatteringLaw
from montepy.errors import MalformedInputError, UnknownElement
from montepy.input_parser.block_type import BlockType
from montepy.input_parser.mcnp_input import Input


# test material
def test_material_parameter_parsing():
    for line in ["M20 1001.80c 1.0 gas=0", "M20 1001.80c 1.0 gas = 0 nlib = 00c"]:
        input = Input([line], BlockType.CELL)
        material = Material(input)


def test_material_validator():
    material = Material()
    with pytest.raises(montepy.errors.IllegalState):
        material.validate()
    with pytest.raises(montepy.errors.IllegalState):
        material.format_for_mcnp_input((6, 2, 0))


def test_material_setter():
    in_str = "M20 1001.80c 0.5 8016.80c 0.5"
    input_card = Input([in_str], BlockType.DATA)
    material = Material(input_card)
    material.number = 30
    assert material.number == 30
    with pytest.raises(TypeError):
        material.number = "foo"
    with pytest.raises(ValueError):
        material.number = -5


def test_material_str():
    in_str = "M20 1001.80c 0.5 8016.80c 0.4 94239.80c 0.1"
    input_card = Input([in_str], BlockType.DATA)
    material = Material(input_card)
    answers = """\
MATERIAL: 20 fractions: atom
 H-1     (80c) 0.5
 O-16    (80c) 0.4
Pu-239   (80c) 0.1
"""
    output = repr(material)
    print(output)
    assert output == answers
    output = str(material)
    assert output == "MATERIAL: 20, ['hydrogen', 'oxygen', 'plutonium']"


def test_material_sort():
    in_str = "M20 1001.80c 0.5 8016.80c 0.5"
    input_card = Input([in_str], BlockType.DATA)
    material1 = Material(input_card)
    in_str = "M30 1001.80c 0.5 8016.80c 0.5"
    input_card = Input([in_str], BlockType.DATA)
    material2 = Material(input_card)
    sort_list = sorted([material2, material1])
    answers = [material1, material2]
    for i, mat in enumerate(sort_list):
        assert mat == answers[i]


def test_material_format_mcnp():
    in_strs = ["M20 1001.80c 0.5", "     8016.80c         0.5"]
    input_card = Input(in_strs, BlockType.DATA)
    material = Material(input_card)
    material.number = 25
    answers = ["M25 1001.80c 0.5", "     8016.80c         0.5"]
    output = material.format_for_mcnp_input((6, 2, 0))
    assert output == answers


@pytest.mark.parametrize(
    "isotope, conc, error",
    [
        ("1001.80c", -0.1, ValueError),
        ("1001.80c", "hi", TypeError),
        ("hi", 1.0, ValueError),
    ],
)
def test_material_comp_init(isotope, conc, error):
    with pytest.raises(error):
        MaterialComponent(Isotope(isotope), conc)


def test_material_comp_fraction_setter():
    comp = MaterialComponent(Isotope("1001.80c"), 0.1)
    comp.fraction = 5.0
    assert comp.fraction == pytest.approx(5.0)
    with pytest.raises(ValueError):
        comp.fraction = -1.0
    with pytest.raises(TypeError):
        comp.fraction = "hi"


def test_material_comp_fraction_str():
    comp = MaterialComponent(Isotope("1001.80c"), 0.1)
    str(comp)
    repr(comp)


def test_material_update_format():
    in_str = "M20 1001.80c 0.5 8016.80c 0.5"
    input_card = Input([in_str], BlockType.DATA)
    material = Material(input_card)
    assert material.format_for_mcnp_input((6, 2, 0)) == [in_str]
    material.number = 5
    print(material.format_for_mcnp_input((6, 2, 0)))
    assert "8016" in material.format_for_mcnp_input((6, 2, 0))[0]
    # addition
    isotope = Isotope("2004.80c")
    material.material_components[isotope] = MaterialComponent(isotope, 0.1)
    print(material.format_for_mcnp_input((6, 2, 0)))
    assert "2004" in material.format_for_mcnp_input((6, 2, 0))[0]
    # update
    isotope = list(material.material_components.keys())[-1]
    print(material.material_components.keys())
    material.material_components[isotope].fraction = 0.7
    print(material.format_for_mcnp_input((6, 2, 0)))
    assert "0.7" in material.format_for_mcnp_input((6, 2, 0))[0]
    material.material_components[isotope] = MaterialComponent(isotope, 0.6)
    print(material.format_for_mcnp_input((6, 2, 0)))
    assert "0.6" in material.format_for_mcnp_input((6, 2, 0))[0]
    # delete
    del material.material_components[isotope]
    print(material.format_for_mcnp_input((6, 2, 0)))
    assert "8016" in material.format_for_mcnp_input((6, 2, 0))[0]


@pytest.mark.parametrize(
    "libraries, slicer, answers",
    [
        (["00c", "04c"], slice("00c", None), [True, True]),
        (["00c", "04c", "80c"], slice("00c", "10c"), [True, True, False]),
        (["00c", "04c", "80c"], slice("10c"), [True, True, False]),
        (["00c", "04p"], slice("00c", None), [True, False]),
    ],
)
def test_material_library_slicer(libraries, slicer, answers):
    assert Material._match_library_slice(libraries, slicer) == answers


@pytest.mark.parametrize(
    "line, mat_number, is_atom, fractions",
    [
        ("M20 1001.80c 0.5 8016.710nc 0.5", 20, True, [0.5, 0.5]),
        ("m1 1001 0.33 8016 0.666667", 1, True, [0.33, 0.666667]),
        ("M20 1001 0.5 8016 0.5", 20, True, [0.5, 0.5]),
        ("M20 1001.80c -0.5 8016.80c -0.5", 20, False, [0.5, 0.5]),
        ("M20 1001.80c -0.5 8016.710nc -0.5", 20, False, [0.5, 0.5]),
        ("M20 1001.80c 0.5 8016.80c 0.5 Gas=1", 20, True, [0.5, 0.5]),
        (
            "m1      8016.71c  2.6999999-02 8017.71c  9.9999998-01 plib=84p",
            1,
            True,
            [2.6999999e-2, 9.9999998e-01],
        ),
    ],
)
def test_material_init(line, mat_number, is_atom, fractions):
    input = Input([line], BlockType.DATA)
    material = Material(input)
    assert material.number == mat_number
    assert material.old_number == mat_number
    assert material.is_atom_fraction == is_atom
    for component, gold in zip(material.material_components.values(), fractions):
        assert component.fraction == pytest.approx(gold)
    if "gas" in line:
        assert material.parameters["gas"]["data"][0].value == pytest.approx(1.0)


@pytest.mark.parametrize(
    "line", ["Mfoo", "M-20", "M20 1001.80c foo", "M20 1001.80c 0.5 8016.80c -0.5"]
)
def test_bad_init(line):
    # test invalid material number
    input = Input([line], BlockType.DATA)
    with pytest.raises(MalformedInputError):
        Material(input)


# test isotope
def test_isotope_init():
    isotope = Isotope("1001.80c")
    assert isotope.ZAID == "1001"
    assert isotope.Z == 1
    assert isotope.A == 1
    assert isotope.element.Z == 1
    assert isotope.library == "80c"
    with pytest.raises(ValueError):
        Isotope("1001.80c.5")
    with pytest.raises(ValueError):
        Isotope("hi.80c")


def test_isotope_metastable_init():
    isotope = Isotope("13426.02c")
    assert isotope.ZAID == "13426"
    assert isotope.Z == 13
    assert isotope.A == 26
    assert isotope.is_metastable
    assert isotope.meta_state == 1
    isotope = Isotope("92635.02c")
    assert isotope.A == 235
    assert isotope.meta_state == 1
    isotope = Isotope("92935.02c")
    assert isotope.A == 235
    assert isotope.meta_state == 4
    assert isotope.mcnp_str() == "92935.02c"
    edge_cases = [
        ("4412", 4, 12, 1),
        ("4413", 4, 13, 1),
        ("4414", 4, 14, 1),
        ("36569", 36, 69, 2),
        ("77764", 77, 164, 3),
    ]
    for ZA, Z_ans, A_ans, isomer_ans in edge_cases:
        isotope = Isotope(ZA + ".80c")
        assert isotope.Z == Z_ans
        assert isotope.A == A_ans
        assert isotope.meta_state == isomer_ans
    with pytest.raises(ValueError):
        isotope = Isotope("13826.02c")


def test_isotope_get_base_zaid():
    isotope = Isotope("92635.02c")
    assert isotope.get_base_zaid() == 92235


def test_isotope_library_setter():
    isotope = Isotope("1001.80c")
    isotope.library = "70c"
    assert isotope.library == "70c"
    with pytest.raises(TypeError):
        isotope.library = 1


def test_isotope_str():
    isotope = Isotope("1001.80c")
    assert isotope.mcnp_str() == "1001.80c"
    assert isotope.nuclide_str() == "H-1.80c"
    assert repr(isotope) == "Isotope('H-1.80c')"
    assert str(isotope) == " H-1     (80c)"
    isotope = Isotope("94239.80c")
    assert isotope.nuclide_str() == "Pu-239.80c"
    assert isotope.mcnp_str() == "94239.80c"
    assert repr(isotope) == "Isotope('Pu-239.80c')"
    isotope = Isotope("92635.80c")
    assert isotope.nuclide_str() == "U-235m1.80c"
    assert isotope.mcnp_str() == "92635.80c"
    assert str(isotope) == " U-235m1 (80c)"
    assert repr(isotope) == "Isotope('U-235m1.80c')"
    # stupid legacy stupidity #486
    isotope = Isotope("95642")
    assert isotope.nuclide_str() == "Am-242"
    assert isotope.mcnp_str() == "95642"
    assert repr(isotope) == "Isotope('Am-242')"
    isotope = Isotope("95242")
    assert isotope.nuclide_str() == "Am-242m1"
    assert isotope.mcnp_str() == "95242"
    assert repr(isotope) == "Isotope('Am-242m1')"


@pytest.mark.parametrize(
    "input, Z, A, meta, library",
    [
        (1001, 1, 1, 0, ""),
        ("1001.80c", 1, 1, 0, "80c"),
        ("h1", 1, 1, 0, ""),
        ("h-1", 1, 1, 0, ""),
        ("h", 1, 0, 0, ""),
        ("hydrogen-1", 1, 1, 0, ""),
        ("hydrogen", 1, 0, 0, ""),
        ("hydrogen1", 1, 1, 0, ""),
        ("hydrogen1m3", 1, 1, 3, ""),
        ("hydrogen1m3.80c", 1, 1, 3, "80c"),
        ("92635m2.710nc", 92, 235, 3, "710nc"),
        (Isotope("1001.80c"), 1, 1, 0, "80c"),
        ((92, 235, 1, "80c"), 92, 235, 1, "80c"),
        ((Element(92), 235, 1, "80c"), 92, 235, 1, "80c"),
        ((Element(92), 235), 92, 235, 0, ""),
        (("U", 235), 92, 235, 0, ""),
        ((92, 235), 92, 235, 0, ""),
        (("uRanium", 235), 92, 235, 0, ""),
        ((Element(92),), 92, 0, 0, ""),
    ],
)
def test_fancy_names(input, Z, A, meta, library):
    isotope = Isotope.get_from_fancy_name(input)
    assert isotope.A == A
    assert isotope.Z == Z
    assert isotope.meta_state == meta
    assert isotope.library == Library(library)


@pytest.fixture
def big_material():
    components = [
        "h1.00c",
        "h1.04c",
        "h1.80c",
        "h1.04p",
        "h2",
        "h3",
        "th232",
        "th232.701nc",
        "U235",
        "U235.80c",
        "U235m1.80c",
        "u238",
        "am242",
        "am242m1",
        "Pu239",
    ]
    mat = Material()
    mat.number = 1
    for component in components:
        mat[component] = 0.05
    return mat


@pytest.mark.parametrize(
    "index",
    [
        1001,
        "1001.00c",
        "h1",
        "h-1",
        "h",
        "hydrogen-1",
        "hydrogen",
        "hydrogen1",
        "hydrogen1m3",
        "hydrogen1m3.00c",
        "Th232.710nc",
        "92635",
        (Isotope("1001.80c"),),
        (92, 235, 1, "80c"),
        (Element(92), 235, 1, "80c"),
        (Element(92), 235),
        ("U", 235),
        (92, 235),
        ("uRanium", 235),
        (Element(92)),
    ],
)
def test_material_access(big_material, index):
    big_material[index]
    # TODO actually test


def test_thermal_scattering_init():
    # test wrong input type assertion
    input_card = Input(["M20"], BlockType.DATA)
    with pytest.raises(MalformedInputError):
        ThermalScatteringLaw(input_card)

    input_card = Input(["Mt20 grph.20t"], BlockType.DATA)
    card = ThermalScatteringLaw(input_card)
    assert card.old_number == 20
    assert card.thermal_scattering_laws == ["grph.20t"]

    input_card = Input(["Mtfoo"], BlockType.DATA)
    with pytest.raises(MalformedInputError):
        ThermalScatteringLaw(input_card)
    input_card = Input(["Mt-20"], BlockType.DATA)
    with pytest.raises(MalformedInputError):
        ThermalScatteringLaw(input_card)
    in_str = "M20 1001.80c 0.5 8016.80c 0.5"
    input_card = Input([in_str], BlockType.DATA)
    material = Material(input_card)
    card = ThermalScatteringLaw(material=material)
    assert card.parent_material == material


def test_thermal_scattering_particle_parser():
    # replicate issue #121
    input_card = Input(["Mt20 h-h2o.40t"], BlockType.DATA)
    card = ThermalScatteringLaw(input_card)
    assert card.old_number == 20
    assert card.thermal_scattering_laws == ["h-h2o.40t"]


def test_thermal_scatter_validate():
    thermal = ThermalScatteringLaw()
    with pytest.raises(montepy.errors.IllegalState):
        thermal.validate()
    with pytest.raises(montepy.errors.IllegalState):
        thermal.format_for_mcnp_input((6, 2, 0))
    material = Material()
    material.number = 1
    thermal._old_number = montepy.input_parser.syntax_node.ValueNode("1", int)
    thermal.update_pointers([material])
    with pytest.raises(montepy.errors.IllegalState):
        thermal.validate()
    thermal._old_number = montepy.input_parser.syntax_node.ValueNode("2", int)
    with pytest.raises(montepy.errors.MalformedInputError):
        thermal.update_pointers([material])


def test_thermal_scattering_add():
    in_str = "Mt20 grph.20t"
    input_card = Input([in_str], BlockType.DATA)
    card = ThermalScatteringLaw(input_card)
    card.add_scattering_law("grph.21t")
    assert len(card.thermal_scattering_laws) == 2
    assert card.thermal_scattering_laws == ["grph.20t", "grph.21t"]
    card.thermal_scattering_laws = ["grph.22t"]
    assert card.thermal_scattering_laws == ["grph.22t"]


def test_thermal_scattering_setter():
    in_str = "Mt20 grph.20t"
    input_card = Input([in_str], BlockType.DATA)
    card = ThermalScatteringLaw(input_card)
    laws = ["grph.21t"]
    card.thermal_scattering_laws = laws
    assert card.thermal_scattering_laws == laws
    with pytest.raises(TypeError):
        card.thermal_scattering_laws = 5
    with pytest.raises(TypeError):
        card.thermal_scattering_laws = [5]


def test_thermal_scattering_material_add():
    in_str = "M20 1001.80c 1.0"
    input_card = Input([in_str], BlockType.DATA)
    card = Material(input_card)
    card.add_thermal_scattering("grph.21t")
    assert len(card.thermal_scattering.thermal_scattering_laws) == 1
    assert card.thermal_scattering.thermal_scattering_laws == ["grph.21t"]
    card.thermal_scattering.thermal_scattering_laws = ["grph.22t"]
    assert card.thermal_scattering.thermal_scattering_laws == ["grph.22t"]
    with pytest.raises(TypeError):
        card.add_thermal_scattering(5)


def test_thermal_scattering_format_mcnp():
    in_str = "Mt20 grph.20t"
    input_card = Input([in_str], BlockType.DATA)
    card = ThermalScatteringLaw(input_card)
    in_str = "M20 1001.80c 0.5 8016.80c 0.5"
    input_card = Input([in_str], BlockType.DATA)
    material = Material(input_card)
    material.update_pointers([card])
    material.thermal_scattering.thermal_scattering_laws = ["grph.20t"]
    assert card.format_for_mcnp_input((6, 2, 0)) == ["Mt20 grph.20t "]


def test_thermal_str():
    in_str = "Mt20 grph.20t"
    input_card = Input([in_str], BlockType.DATA)
    card = ThermalScatteringLaw(input_card)
    assert str(card) == "THERMAL SCATTER: ['grph.20t']"
    assert (
        repr(card)
        == "THERMAL SCATTER: material: None, old_num: 20, scatter: ['grph.20t']"
    )


# test element
def test_element_init():
    for Z in range(1, 119):
        element = Element(Z)
        assert element.Z == Z
        # Test to ensure there are no missing elements
        name = element.name
        symbol = element.symbol

    with pytest.raises(UnknownElement):
        Element(119)

    spot_check = {
        1: ("H", "hydrogen"),
        40: ("Zr", "zirconium"),
        92: ("U", "uranium"),
        94: ("Pu", "plutonium"),
        29: ("Cu", "copper"),
        13: ("Al", "aluminum"),
    }
    for z, (symbol, name) in spot_check.items():
        element = Element(z)
        assert z == element.Z
        assert symbol == element.symbol
        assert name == element.name


def test_element_str():
    element = Element(1)
    assert str(element) == "hydrogen"
    assert repr(element) == "Z=1, symbol=H, name=hydrogen"


def test_get_by_symbol():
    element = Element.get_by_symbol("Hg")
    assert element.name == "mercury"
    with pytest.raises(UnknownElement):
        Element.get_by_symbol("Hi")


def test_get_by_name():
    element = Element.get_by_name("mercury")
    assert element.symbol == "Hg"
    with pytest.raises(UnknownElement):
        Element.get_by_name("hudrogen")


# particle
def test_particle_str():
    part = montepy.Particle("N")
    assert str(part) == "neutron"

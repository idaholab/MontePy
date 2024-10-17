# Copyright 2024, Battelle Energy Alliance, LLC All Rights Reserved.
from hypothesis import given, strategies as st
import pytest
from hypothesis import assume, given, note, strategies as st

import montepy

from montepy.data_inputs.element import Element
from montepy.data_inputs.nuclide import Nucleus, Nuclide, Library
from montepy.data_inputs.material import Material
from montepy.data_inputs.material_component import MaterialComponent
from montepy.data_inputs.thermal_scattering import ThermalScatteringLaw
from montepy.errors import MalformedInputError, UnknownElement
from montepy.input_parser.block_type import BlockType
from montepy.input_parser.mcnp_input import Input


# test material
def test_material_parameter_parsing():
    for line in [
        "M20 1001.80c 1.0 gas=0",
        "M20 1001.80c 1.0 gas = 0 nlib = 00c",
        "M120 nlib=80c 1001 1.0",
    ]:
        input = Input([line], BlockType.DATA)
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
    print(output)
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


def test_material_comp_init():
    with pytest.raises(DeprecationWarning):
        MaterialComponent(Nuclide("1001"), 0.1)


def test_mat_comp_init_warn():
    with pytest.raises(DeprecationWarning):
        MaterialComponent(Nuclide("1001.80c"), 0.1)


def test_material_update_format():
    # TODO update this
    pass
    """
    in_str = "M20 1001.80c 0.5 8016.80c 0.5"
    input_card = Input([in_str], BlockType.DATA)
    material = Material(input_card)
    assert material.format_for_mcnp_input((6, 2, 0)) == [in_str]
    material.number = 5
    print(material.format_for_mcnp_input((6, 2, 0)))
    assert "8016" in material.format_for_mcnp_input((6, 2, 0))[0]
    # addition
    isotope = Nuclide("2004.80c", suppress_warning=True)
    with pytest.deprecated_call():
        material.material_components[isotope] = MaterialComponent(isotope, 0.1, True)
        print(material.format_for_mcnp_input((6, 2, 0)))
        assert "2004" in material.format_for_mcnp_input((6, 2, 0))[0]
        # update
        isotope = list(material.material_components.keys())[-1]
        print(material.material_components.keys())
        material.material_components[isotope].fraction = 0.7
        print(material.format_for_mcnp_input((6, 2, 0)))
        assert "0.7" in material.format_for_mcnp_input((6, 2, 0))[0]
        material.material_components[isotope] = MaterialComponent(isotope, 0.6, True)
        print(material.format_for_mcnp_input((6, 2, 0)))
        assert "0.6" in material.format_for_mcnp_input((6, 2, 0))[0]
        # delete
        del material.material_components[isotope]
        print(material.format_for_mcnp_input((6, 2, 0)))
        assert "8016" in material.format_for_mcnp_input((6, 2, 0))[0]
    """


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
        *[
            (f"M20 1001.80c 0.5 8016.80c 0.5 {part}={lib}", 20, True, [0.5, 0.5])
            for part, lib in [
                ("nlib", "80c"),
                ("nlib", "701nc"),
                ("estep", 1),
                ("pnlib", "710nc"),
                ("slib", "80c"),
            ]
        ],
    ],
)
def test_material_init(line, mat_number, is_atom, fractions):
    input = Input([line], BlockType.DATA)
    material = Material(input)
    assert material.number == mat_number
    assert material.old_number == mat_number
    assert material.is_atom_fraction == is_atom
    for component, gold in zip(material, fractions):
        assert component[1] == pytest.approx(gold)
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
    isotope = Nuclide("1001.80c")
    assert isotope.ZAID == 1001
    assert isotope.Z == 1
    assert isotope.A == 1
    assert isotope.element.Z == 1
    assert isotope.library == "80c"
    with pytest.raises(ValueError):
        Nuclide("1001.80c.5")
    with pytest.raises(ValueError):
        Nuclide("hi.80c")


@pytest.mark.filterwarnings("ignore")
@given(st.integers(), st.integers())
def test_mat_clone(start_num, step):
    input = Input(["m1 1001.80c 0.3 8016.80c 0.67"], BlockType.DATA)
    mat = Material(input)
    problem = montepy.MCNP_Problem("foo")
    for prob in {None, problem}:
        mat.link_to_problem(prob)
        if prob is not None:
            problem.materials.append(mat)
        if start_num <= 0 or step <= 0:
            with pytest.raises(ValueError):
                mat.clone(start_num, step)
            return
        new_mat = mat.clone(start_num, step)
        assert new_mat is not mat
        for (iso, fraction), (gold_iso, gold_fraction) in zip(new_mat, mat):
            assert iso is not gold_iso
            assert iso.ZAID == gold_iso.ZAID
            assert fraction == pytest.approx(gold_fraction)
        assert new_mat._number is new_mat._tree["classifier"].number
        output = new_mat.format_for_mcnp_input((6, 3, 0))
        input = Input(output, BlockType.DATA)
        newer_mat = Material(input)
        assert newer_mat.number == new_mat.number


@pytest.mark.parametrize(
    "args, error",
    [
        (("c", 1), TypeError),
        ((1, "d"), TypeError),
        ((-1, 1), ValueError),
        ((0, 1), ValueError),
        ((1, 0), ValueError),
        ((1, -1), ValueError),
    ],
)
def test_cell_clone_bad(args, error):
    input = Input(["m1 1001.80c 0.3 8016.80c 0.67"], BlockType.CELL)
    mat = Material(input)
    with pytest.raises(error):
        mat.clone(*args)


def test_isotope_metastable_init():
    isotope = Nuclide("13426.02c")
    assert isotope.ZAID == 13426
    assert isotope.Z == 13
    assert isotope.A == 26
    assert isotope.is_metastable
    assert isotope.meta_state == 1
    isotope = Nuclide("92635.02c")
    assert isotope.A == 235
    assert isotope.meta_state == 1
    isotope = Nuclide("92935.02c")
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
        isotope = Nuclide(ZA + ".80c")
        assert isotope.Z == Z_ans
        assert isotope.A == A_ans
        assert isotope.meta_state == isomer_ans
    with pytest.raises(ValueError):
        isotope = Nuclide("13826.02c")


def test_isotope_get_base_zaid():
    isotope = Nuclide("92635.02c")
    assert isotope.get_base_zaid() == 92235


def test_isotope_library_setter():
    isotope = Nuclide("1001.80c")
    isotope.library = "70c"
    assert isotope.library == "70c"
    with pytest.raises(TypeError):
        isotope.library = 1


def test_isotope_str():
    isotope = Nuclide("1001.80c")
    assert isotope.mcnp_str() == "1001.80c"
    assert isotope.nuclide_str() == "H-1.80c"
    assert repr(isotope) == "Nuclide('H-1.80c')"
    assert str(isotope) == " H-1     (80c)"
    isotope = Nuclide("94239.80c")
    assert isotope.nuclide_str() == "Pu-239.80c"
    assert isotope.mcnp_str() == "94239.80c"
    assert repr(isotope) == "Nuclide('Pu-239.80c')"
    isotope = Nuclide("92635.80c")
    assert isotope.nuclide_str() == "U-235m1.80c"
    assert isotope.mcnp_str() == "92635.80c"
    assert str(isotope) == " U-235m1 (80c)"
    assert repr(isotope) == "Nuclide('U-235m1.80c')"
    # stupid legacy stupidity #486
    isotope = Nuclide("95642")
    assert isotope.nuclide_str() == "Am-242"
    assert isotope.mcnp_str() == "95642"
    assert repr(isotope) == "Nuclide('Am-242')"
    isotope = Nuclide("95242")
    assert isotope.nuclide_str() == "Am-242m1"
    assert isotope.mcnp_str() == "95242"
    assert repr(isotope) == "Nuclide('Am-242m1')"


@pytest.mark.parametrize(
    "input, Z, A, meta, library",
    [
        (1001, 1, 1, 0, ""),
        ("1001.80c", 1, 1, 0, "80c"),
        ("h1", 1, 1, 0, ""),
        ("h-1", 1, 1, 0, ""),
        ("h-1.80c", 1, 1, 0, "80c"),
        ("h", 1, 0, 0, ""),
        ("92635m2.710nc", 92, 235, 3, "710nc"),
    ],
)
def test_fancy_names(input, Z, A, meta, library):
    isotope = Nuclide(input)
    assert isotope.A == A
    assert isotope.Z == Z
    assert isotope.meta_state == meta
    assert isotope.library == Library(library)


@given(
    st.integers(1, 118),
    st.floats(2.1, 2.7),
    st.integers(0, 4),
    st.integers(0, 1000),
    st.characters(min_codepoint=97, max_codepoint=122),
    st.booleans(),
)
def test_fancy_names_pbt(
    Z, A_multiplier, meta, library_base, library_extension, hyphen
):
    # avoid Am-242 metastable legacy
    A = int(Z * A_multiplier)
    element = Element(Z)
    assume(not (Z == 95 and A == 242))
    # ignore H-*m* as it's nonsense
    assume(not (Z == 1 and meta > 0))
    for lim_Z, lim_A in Nucleus._BOUNDING_CURVE:
        if Z <= lim_Z:
            break
    assume(A <= lim_A)
    library = f"{library_base:02}{library_extension}"
    inputs = [
        f"{Z* 1000 + A}{f'm{meta}' if meta > 0 else ''}.{library}",
        f"{Z* 1000 + A}{f'm{meta}' if meta > 0 else ''}",
        f"{element.symbol}{'-' if hyphen else ''}{A}{f'm{meta}' if meta > 0 else ''}.{library}",
        f"{element.symbol}{'-' if hyphen else ''}{A}{f'm{meta}' if meta > 0 else ''}",
    ]

    if meta:
        inputs.append(f"{Z* 1000 + A + 300 + 100 * meta}.{library}")
    note(inputs)
    for input in inputs:
        note(input)
        isotope = Nuclide(input)
        assert isotope.A == A
        assert isotope.Z == Z
        assert isotope.meta_state == meta
        if library in input:
            assert isotope.library == Library(library)
        else:
            assert isotope.library == Library("")


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
        mat.add_nuclide(component, 0.05)
    return mat


@pytest.mark.parametrize(
    "index",
    [
        (1),  # TODO property testing
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
        with self.assertRaises(montepy.errors.IllegalState):
            thermal.validate()
        thermal._old_number = montepy.input_parser.syntax_node.ValueNode("2", int)
        with self.assertRaises(montepy.errors.MalformedInputError):
            thermal.update_pointers([material])

    def test_thermal_scattering_add(self):
        in_str = "Mt20 grph.20t"
        input_card = Input([in_str], BlockType.DATA)
        card = ThermalScatteringLaw(input_card)
        card.add_scattering_law("grph.21t")
        self.assertEqual(len(card.thermal_scattering_laws), 2)
        self.assertEqual(card.thermal_scattering_laws, ["grph.20t", "grph.21t"])
        card.thermal_scattering_laws = ["grph.22t"]
        self.assertEqual(card.thermal_scattering_laws, ["grph.22t"])

    def test_thermal_scattering_setter(self):
        in_str = "Mt20 grph.20t"
        input_card = Input([in_str], BlockType.DATA)
        card = ThermalScatteringLaw(input_card)
        laws = ["grph.21t"]
        card.thermal_scattering_laws = laws
        self.assertEqual(card.thermal_scattering_laws, laws)
        with self.assertRaises(TypeError):
            card.thermal_scattering_laws = 5
        with self.assertRaises(TypeError):
            card.thermal_scattering_laws = [5]

    def test_thermal_scattering_material_add(self):
        in_str = "M20 1001.80c 1.0"
        input_card = Input([in_str], BlockType.DATA)
        card = Material(input_card)
        card.add_thermal_scattering("grph.21t")
        self.assertEqual(len(card.thermal_scattering.thermal_scattering_laws), 1)
        self.assertEqual(card.thermal_scattering.thermal_scattering_laws, ["grph.21t"])
        card.thermal_scattering_laws = ["grph.22t"]
        self.assertEqual(card.thermal_scattering_laws, ["grph.22t"])
        with self.assertRaises(TypeError):
            card.add_thermal_scattering(5)

    def test_thermal_scattering_format_mcnp(self):
        in_str = "Mt20 grph.20t"
        input_card = Input([in_str], BlockType.DATA)
        card = ThermalScatteringLaw(input_card)
        in_str = "M20 1001.80c 0.5 8016.80c 0.5"
        input_card = Input([in_str], BlockType.DATA)
        material = Material(input_card)
        material.thermal_scattering = card
        card._parent_material = material
        material.thermal_scattering.thermal_scattering_laws = ["grph.20t"]
        self.assertEqual(card.format_for_mcnp_input((6, 2, 0)), ["Mt20 grph.20t "])

    def test_thermal_str(self):
        in_str = "Mt20 grph.20t"
        input_card = Input([in_str], BlockType.DATA)
        card = ThermalScatteringLaw(input_card)
        self.assertEqual(str(card), "THERMAL SCATTER: ['grph.20t']")
        self.assertEqual(
            repr(card),
            "THERMAL SCATTER: material: None, old_num: 20, scatter: ['grph.20t']",
        )


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
    material.thermal_scattering = card
    card._parent_material = material
    material.thermal_scattering.thermal_scattering_laws = ["grph.20t"]
    card.format_for_mcnp_input((6, 2, 0)) == ["Mt20 grph.20t "]


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

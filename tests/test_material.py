# Copyright 2024, Battelle Energy Alliance, LLC All Rights Reserved.
from hypothesis import given, strategies as st
from unittest import TestCase
import pytest

import montepy

from montepy.data_inputs.element import Element
from montepy.data_inputs.isotope import Isotope
from montepy.data_inputs.material import Material
from montepy.data_inputs.material_component import MaterialComponent
from montepy.data_inputs.thermal_scattering import ThermalScatteringLaw
from montepy.errors import MalformedInputError, UnknownElement
from montepy.input_parser.block_type import BlockType
from montepy.input_parser.mcnp_input import Input


class testMaterialClass(TestCase):
    def test_material_parameter_parsing(self):
        for line in ["M20 1001.80c 1.0 gas=0", "M20 1001.80c 1.0 gas = 0 nlib = 00c"]:
            input = Input([line], BlockType.CELL)
            material = Material(input)

    def test_material_validator(self):
        material = Material()
        with self.assertRaises(montepy.errors.IllegalState):
            material.validate()
        with self.assertRaises(montepy.errors.IllegalState):
            material.format_for_mcnp_input((6, 2, 0))

    def test_material_setter(self):
        in_str = "M20 1001.80c 0.5 8016.80c 0.5"
        input_card = Input([in_str], BlockType.DATA)
        material = Material(input_card)
        material.number = 30
        self.assertEqual(material.number, 30)
        with self.assertRaises(TypeError):
            material.number = "foo"
        with self.assertRaises(ValueError):
            material.number = -5

    def test_material_str(self):
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

    def test_material_sort(self):
        in_str = "M20 1001.80c 0.5 8016.80c 0.5"
        input_card = Input([in_str], BlockType.DATA)
        material1 = Material(input_card)
        in_str = "M30 1001.80c 0.5 8016.80c 0.5"
        input_card = Input([in_str], BlockType.DATA)
        material2 = Material(input_card)
        sort_list = sorted([material2, material1])
        answers = [material1, material2]
        for i, mat in enumerate(sort_list):
            self.assertEqual(mat, answers[i])


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
        MaterialComponent(Isotope(isotope, suppress_warning=True), conc, True)


def test_mat_comp_init_warn():
    with pytest.warns(DeprecationWarning):
        MaterialComponent(Isotope("1001.80c", suppress_warning=True), 0.1)


def test_material_comp_fraction_setter():
    comp = MaterialComponent(Isotope("1001.80c", suppress_warning=True), 0.1, True)
    comp.fraction = 5.0
    assert comp.fraction == pytest.approx(5.0)
    with pytest.raises(ValueError):
        comp.fraction = -1.0
    with pytest.raises(TypeError):
        comp.fraction = "hi"


def test_material_comp_fraction_str():
    comp = MaterialComponent(Isotope("1001.80c", suppress_warning=True), 0.1, True)
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
    isotope = Isotope("2004.80c", suppress_warning=True)
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
    with pytest.deprecated_call():
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
        for (iso, fraction), (gold_iso, gold_fraction) in zip(
            new_mat.material_components.items(), mat.material_components.items()
        ):
            assert iso is not gold_iso
            assert iso.ZAID == gold_iso.ZAID
            assert fraction.fraction == pytest.approx(gold_fraction.fraction)
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


class TestIsotope(TestCase):
    def test_isotope_init(self):
        with pytest.warns(FutureWarning):
            isotope = Isotope("1001.80c")
        self.assertEqual(isotope.ZAID, "1001")
        self.assertEqual(isotope.Z, 1)
        self.assertEqual(isotope.A, 1)
        self.assertEqual(isotope.element.Z, 1)
        self.assertEqual(isotope.library, "80c")
        with self.assertRaises(ValueError):
            Isotope("1001.80c.5", suppress_warning=True)
        with self.assertRaises(ValueError):
            Isotope("hi.80c", suppress_warning=True)

    def test_isotope_metastable_init(self):
        isotope = Isotope("13426.02c", suppress_warning=True)
        self.assertEqual(isotope.ZAID, "13426")
        self.assertEqual(isotope.Z, 13)
        self.assertEqual(isotope.A, 26)
        self.assertTrue(isotope.is_metastable)
        self.assertEqual(isotope.meta_state, 1)
        isotope = Isotope("92635.02c", suppress_warning=True)
        self.assertEqual(isotope.A, 235)
        self.assertEqual(isotope.meta_state, 1)
        isotope = Isotope("92935.02c", suppress_warning=True)
        self.assertEqual(isotope.A, 235)
        self.assertEqual(isotope.meta_state, 4)
        self.assertEqual(isotope.mcnp_str(), "92935.02c")
        edge_cases = [
            ("4412", 4, 12, 1),
            ("4413", 4, 13, 1),
            ("4414", 4, 14, 1),
            ("36569", 36, 69, 2),
            ("77764", 77, 164, 3),
        ]
        for ZA, Z_ans, A_ans, isomer_ans in edge_cases:
            isotope = Isotope(ZA + ".80c", suppress_warning=True)
            self.assertEqual(isotope.Z, Z_ans)
            self.assertEqual(isotope.A, A_ans)
            self.assertEqual(isotope.meta_state, isomer_ans)
        with self.assertRaises(ValueError):
            isotope = Isotope("13826.02c", suppress_warning=True)

    def test_isotope_get_base_zaid(self):
        isotope = Isotope("92635.02c", suppress_warning=True)
        self.assertEqual(isotope.get_base_zaid(), 92235)

    def test_isotope_library_setter(self):
        isotope = Isotope("1001.80c", suppress_warning=True)
        isotope.library = "70c"
        self.assertEqual(isotope.library, "70c")
        with self.assertRaises(TypeError):
            isotope.library = 1

    def test_isotope_str(self):
        isotope = Isotope("1001.80c", suppress_warning=True)
        assert isotope.mcnp_str() == "1001.80c"
        assert isotope.nuclide_str() == "H-1.80c"
        assert repr(isotope) == "Isotope('H-1.80c')"
        assert str(isotope) == " H-1     (80c)"
        isotope = Isotope("94239.80c", suppress_warning=True)
        assert isotope.nuclide_str() == "Pu-239.80c"
        assert isotope.mcnp_str() == "94239.80c"
        assert repr(isotope) == "Isotope('Pu-239.80c')"
        isotope = Isotope("92635.80c", suppress_warning=True)
        assert isotope.nuclide_str() == "U-235m1.80c"
        assert isotope.mcnp_str() == "92635.80c"
        assert str(isotope) == " U-235m1 (80c)"
        assert repr(isotope) == "Isotope('U-235m1.80c')"
        # stupid legacy stupidity #486
        isotope = Isotope("95642", suppress_warning=True)
        assert isotope.nuclide_str() == "Am-242"
        assert isotope.mcnp_str() == "95642"
        assert repr(isotope) == "Isotope('Am-242')"
        isotope = Isotope("95242", suppress_warning=True)
        assert isotope.nuclide_str() == "Am-242m1"
        assert isotope.mcnp_str() == "95242"
        assert repr(isotope) == "Isotope('Am-242m1')"


class TestThermalScattering(TestCase):
    def test_thermal_scattering_init(self):
        # test wrong input type assertion
        input_card = Input(["M20"], BlockType.DATA)
        with self.assertRaises(MalformedInputError):
            ThermalScatteringLaw(input_card)

        input_card = Input(["Mt20 grph.20t"], BlockType.DATA)
        card = ThermalScatteringLaw(input_card)
        self.assertEqual(card.old_number, 20)
        self.assertEqual(card.thermal_scattering_laws, ["grph.20t"])

        input_card = Input(["Mtfoo"], BlockType.DATA)
        with self.assertRaises(MalformedInputError):
            ThermalScatteringLaw(input_card)
        input_card = Input(["Mt-20"], BlockType.DATA)
        with self.assertRaises(MalformedInputError):
            ThermalScatteringLaw(input_card)
        in_str = "M20 1001.80c 0.5 8016.80c 0.5"
        input_card = Input([in_str], BlockType.DATA)
        material = Material(input_card)
        card = ThermalScatteringLaw(material=material)
        self.assertEqual(card.parent_material, material)

    def test_thermal_scattering_particle_parser(self):
        # replicate issue #121
        input_card = Input(["Mt20 h-h2o.40t"], BlockType.DATA)
        card = ThermalScatteringLaw(input_card)
        self.assertEqual(card.old_number, 20)
        self.assertEqual(card.thermal_scattering_laws, ["h-h2o.40t"])

    def test_thermal_scatter_validate(self):
        thermal = ThermalScatteringLaw()
        with self.assertRaises(montepy.errors.IllegalState):
            thermal.validate()
        with self.assertRaises(montepy.errors.IllegalState):
            thermal.format_for_mcnp_input((6, 2, 0))
        material = Material()
        material.number = 1
        thermal._old_number = montepy.input_parser.syntax_node.ValueNode("1", int)
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


class TestElement(TestCase):
    def test_element_init(self):
        for Z in range(1, 119):
            element = Element(Z)
            self.assertEqual(element.Z, Z)
            # Test to ensure there are no missing elements
            name = element.name
            symbol = element.symbol

        with self.assertRaises(UnknownElement):
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
            self.assertEqual(z, element.Z)
            self.assertEqual(symbol, element.symbol)
            self.assertEqual(name, element.name)

    def test_element_str(self):
        element = Element(1)
        self.assertEqual(str(element), "hydrogen")
        self.assertEqual(repr(element), "Z=1, symbol=H, name=hydrogen")

    def test_get_by_symbol(self):
        element = Element.get_by_symbol("Hg")
        self.assertEqual(element.name, "mercury")
        with self.assertRaises(UnknownElement):
            Element.get_by_symbol("Hi")

    def test_get_by_name(self):
        element = Element.get_by_name("mercury")
        self.assertEqual(element.symbol, "Hg")
        with self.assertRaises(UnknownElement):
            Element.get_by_name("hudrogen")


class TestParticle(TestCase):
    def test_particle_str(self):
        part = montepy.Particle("N")
        self.assertEqual(str(part), "neutron")

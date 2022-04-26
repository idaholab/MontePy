from unittest import TestCase

import mcnpy

from mcnpy.data_cards.isotope import Isotope
from mcnpy.data_cards.material import Material
from mcnpy.data_cards.material_component import MaterialComponent
from mcnpy.data_cards.thermal_scattering import ThermalScatteringLaw
from mcnpy.errors import MalformedInputError
from mcnpy.input_parser.block_type import BlockType
from mcnpy.input_parser.mcnp_input import Card, Comment


class testMaterialClass(TestCase):
    def test_material_init(self):
        # test invalid material number
        input_card = Card(["Mfoo"], BlockType.DATA, ["Mfoo"])
        with self.assertRaises(MalformedInputError):
            Material(input_card, None)
        input_card = Card(["M-20"], BlockType.DATA, ["M-20"])
        with self.assertRaises(MalformedInputError):
            Material(input_card, None)

        in_str = "M20 1001.80c 0.5 8016.80c 0.5"
        input_card = Card([in_str], BlockType.DATA, in_str.split())
        material = Material(input_card, None)
        self.assertEqual(material.number, 20)
        self.assertEqual(material.old_number, 20)
        self.assertTrue(material.is_atom_fraction)
        for component in material.material_components:
            self.assertEqual(material.material_components[component].fraction, 0.5)

        in_str = "M20 1001.80c -0.5 8016.80c -0.5"
        input_card = Card([in_str], BlockType.DATA, in_str.split())
        material = Material(input_card, None)
        self.assertFalse(material.is_atom_fraction)
        for component in material.material_components:
            self.assertEqual(material.material_components[component].fraction, 0.5)

        # test bad fraction
        in_str = "M20 1001.80c foo"
        input_card = Card([in_str], BlockType.DATA, in_str.split())
        with self.assertRaises(MalformedInputError):
            material = Material(input_card, None)
        # test mismatch fraction
        in_str = "M20 1001.80c 0.5 8016.80c -0.5"
        input_card = Card([in_str], BlockType.DATA, in_str.split())
        with self.assertRaises(MalformedInputError):
            material = Material(input_card, None)
        # test parameters
        in_str = "M20 1001.80c 0.5 8016.80c 0.5 Gas=1"
        input_card = Card([in_str], BlockType.DATA, in_str.split())
        material = Material(input_card, None)

        self.assertEqual(material.parameter_string, "Gas=1 ")

    def test_material_setter(self):
        in_str = "M20 1001.80c 0.5 8016.80c 0.5"
        input_card = Card([in_str], BlockType.DATA, in_str.split())
        material = Material(input_card, None)
        material.number = 30
        self.assertEqual(material.number, 30)
        with self.assertRaises(AssertionError):
            material.number = "foo"

    def test_material_str(self):
        in_str = "M20 1001.80c 0.5 8016.80c 0.5"
        input_card = Card([in_str], BlockType.DATA, in_str.split())
        material = Material(input_card, None)
        answers = """MATERIAL: 20 fractions: atom
1001.80c 0.5
8016.80c 0.5
"""
        output = str(material)
        self.assertEqual(output, answers)

    def test_material_sort(self):
        in_str = "M20 1001.80c 0.5 8016.80c 0.5"
        input_card = Card([in_str], BlockType.DATA, in_str.split())
        material1 = Material(input_card, None)
        in_str = "M30 1001.80c 0.5 8016.80c 0.5"
        input_card = Card([in_str], BlockType.DATA, in_str.split())
        material2 = Material(input_card, None)
        sort_list = sorted([material2, material1])
        answers = [material1, material2]
        for i, mat in enumerate(sort_list):
            self.assertEqual(mat, answers[i])

    def test_material_format_mcnp(self):
        in_str = "M20 1001.80c 0.5 8016.80c 0.5"
        input_card = Card([in_str], BlockType.DATA, in_str.split())
        material = Material(input_card, None)
        material.material_number = 25
        answers = ["m25       1001.80c         0.5", "           8016.80c         0.5"]
        output = material.format_for_mcnp_input((6, 2, 0))
        self.assertEqual(len(answers), len(output))
        for i, line in enumerate(output):
            self.assertEqual(line, answers[i])

    def test_material_comp_init(self):
        # test fraction test
        with self.assertRaises(AssertionError):
            MaterialComponent(Isotope("1001.80c"), -0.1)

        # test bad fraction
        with self.assertRaises(AssertionError):
            MaterialComponent(Isotope("1001.80c"), "hi")

    def test_isotope_init(self):
        isotope = Isotope("1001.80c")
        self.assertEqual(isotope.ZAID, "1001")
        self.assertEqual(isotope.library, "80c")

        with self.assertRaises(AssertionError):
            Isotope("1001.80c.5")

        with self.assertRaises(MalformedInputError):
            Isotope("1001")

    def test_isotope_library_setter(self):
        isotope = Isotope("1001.80c")
        isotope.library = "70c"
        self.assertEqual(isotope.library, "70c")
        with self.assertRaises(AssertionError):
            isotope.library = 1

    def test_thermal_scattering_init(self):
        # test wrong card type assertion
        input_card = Card(["M20"], BlockType.DATA, ["M20"])
        with self.assertRaises(AssertionError):
            ThermalScatteringLaw(input_card)

        input_card = Card(["Mt20 grph.20t"], BlockType.DATA, ["Mt20", "grph.20t"])
        card = ThermalScatteringLaw(input_card)
        self.assertEqual(card.old_number, 20)
        self.assertEqual(card.thermal_scattering_laws, ["grph.20t"])

        input_card = Card(["Mtfoo"], BlockType.DATA, ["Mtfoo"])
        with self.assertRaises(MalformedInputError):
            ThermalScatteringLaw(input_card, None)
        input_card = Card(["Mt-20"], BlockType.DATA, ["Mt-20"])
        with self.assertRaises(MalformedInputError):
            ThermalScatteringLaw(input_card, None)
        in_str = "M20 1001.80c 0.5 8016.80c 0.5"
        input_card = Card([in_str], BlockType.DATA, in_str.split())
        material = Material(input_card, None)
        comment = Comment(["c foo"], ["foo"])
        card = ThermalScatteringLaw(comment=comment, material=material)
        self.assertEqual(card.parent_material, material)

    def test_thermal_scattering_add(self):
        in_str = "Mt20 grph.20t"
        input_card = Card([in_str], BlockType.DATA, in_str.split())
        card = ThermalScatteringLaw(input_card)
        card.add_scattering_law("grph.21t")
        self.assertEqual(len(card.thermal_scattering_laws), 2)
        self.assertEqual(card.thermal_scattering_laws, ["grph.20t", "grph.21t"])
        card.thermal_scattering_laws = ["grph.22t"]
        self.assertEqual(card.thermal_scattering_laws, ["grph.22t"])

    def test_thermal_scattering_format_mcnp(self):
        in_str = "Mt20 grph.20t"
        input_card = Card([in_str], BlockType.DATA, in_str.split())
        card = ThermalScatteringLaw(input_card)
        in_str = "M20 1001.80c 0.5 8016.80c 0.5"
        input_card = Card([in_str], BlockType.DATA, in_str.split())
        material = Material(input_card, None)
        material.update_pointers([card])
        material.thermal_scattering.thermal_scattering_laws = ["grph.20t"]
        self.assertEqual(card.format_for_mcnp_input((6, 2, 0)), ["MT20 grph.20t"])

    def test_material_card_pass_through(self):
        in_str = "M20 1001.80c 0.5 8016.80c 0.5"
        input_card = Card([in_str], BlockType.DATA, in_str.split())
        material = Material(input_card, None)
        self.assertEqual(material.format_for_mcnp_input((6, 2, 0)), [in_str])
        # TODO
        material.material_number = 5
        self.assertNotIn("8016", material.format_for_mcnp_input((6, 2, 0)))

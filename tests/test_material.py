# Copyright 2024, Battelle Energy Alliance, LLC All Rights Reserved.
from hypothesis import given, strategies as st
import pytest
from hypothesis import assume, given, note, strategies as st

import montepy

from montepy.data_inputs.element import Element
from montepy.data_inputs.nuclide import Nucleus, Nuclide, Library
from montepy.data_inputs.material import Material, _DefaultLibraries as DL
from montepy.data_inputs.material_component import MaterialComponent
from montepy.data_inputs.thermal_scattering import ThermalScatteringLaw
from montepy.errors import MalformedInputError, UnknownElement
from montepy.input_parser.block_type import BlockType
from montepy.input_parser.mcnp_input import Input
from montepy.particle import LibraryType


# test material
class TestMaterial:
    @pytest.fixture
    def big_material(_):
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

    @pytest.fixture
    def big_mat_lib(_, big_material):
        mat = big_material
        mat.default_libraries["nlib"] = "00c"
        mat.default_libraries["plib"] = "80p"
        return mat

    @pytest.fixture
    def prob_default(_):
        prob = montepy.MCNP_Problem("hi")
        prob.materials.default_libraries["alib"] = "24a"
        return prob

    @pytest.mark.parametrize(
        "isotope_str, lib_type, lib_str",
        [
            ("H-1.80c", "nlib", "80c"),
            ("H-1.80c", "plib", "80p"),
            ("H-1.80c", "hlib", None),
            ("H-1.80c", "alib", "24a"),
        ],
    )
    def test_mat_get_nuclide_library(
        _, big_mat_lib, prob_default, isotope_str, lib_type, lib_str
    ):
        nuclide = Nuclide(isotope_str)
        if lib_str:
            lib = Library(lib_str)
            big_mat_lib.link_to_problem(prob_default)
        else:
            lib = None
        assert big_mat_lib.get_nuclide_library(nuclide, lib_type) == lib
        assert (
            big_mat_lib.get_nuclide_library(nuclide, LibraryType(lib_type.upper()))
            == lib
        )
        if lib is None:
            big_mat_lib.link_to_problem(prob_default)
            assert big_mat_lib.get_nuclide_library(nuclide, lib_type) == lib

    def test_mat_get_nuclide_library_bad(_, big_mat_lib):
        with pytest.raises(TypeError):
            big_mat_lib.get_nuclide_library(5, "nlib")
        with pytest.raises(TypeError):
            big_mat_lib.get_nuclide_library("1001.80c", 5)

    def test_material_parameter_parsing(_):
        for line in [
            "M20 1001.80c 1.0 gas=0",
            "M20 1001.80c 1.0 gas = 0 nlib = 00c",
            "M120 nlib=80c 1001 1.0",
        ]:
            input = Input([line], BlockType.DATA)
            material = Material(input)

    def test_material_validator(_):
        material = Material()
        with pytest.raises(montepy.errors.IllegalState):
            material.validate()
        with pytest.raises(montepy.errors.IllegalState):
            material.format_for_mcnp_input((6, 2, 0))

    def test_material_number_setter(_):
        in_str = "M20 1001.80c 0.5 8016.80c 0.5"
        input_card = Input([in_str], BlockType.DATA)
        material = Material(input_card)
        material.number = 30
        assert material.number == 30
        with pytest.raises(TypeError):
            material.number = "foo"
        with pytest.raises(ValueError):
            material.number = -5
        _.verify_export(material)

    def test_material_getter_iter(_, big_material):
        for i, (nuclide, frac) in enumerate(big_material):
            gotten = big_material[i]
            assert gotten[0] == nuclide
            assert gotten[1] == pytest.approx(frac)
        comp_0, comp_1 = big_material[0:2]
        assert comp_0 == big_material[0]
        assert comp_1 == big_material[1]
        _, comp_1 = big_material[0:4:3]
        assert comp_1 == big_material[3]
        with pytest.raises(TypeError):
            big_material["hi"]

    def test_material_setter(_, big_material):
        big_material[2] = (Nuclide("1001.80c"), 1.0)
        assert big_material[2][0] == Nuclide("1001.80c")
        assert big_material[2][1] == pytest.approx(1.0)
        with pytest.raises(TypeError):
            big_material["hi"] = 5
        with pytest.raises(TypeError):
            big_material[2] = 5
        with pytest.raises(ValueError):
            big_material[2] = (5,)
        with pytest.raises(TypeError):
            big_material[2] = (5, 1.0)
        with pytest.raises(TypeError):
            big_material[2] = (Nuclide("1001.80c"), "hi")
        with pytest.raises(ValueError):
            big_material[2] = (Nuclide("1001.80c"), -1.0)
        _.verify_export(big_material)

    def test_material_deleter(_, big_material):
        old_comp = big_material[6]
        del big_material[6]
        assert old_comp[0] not in big_material
        old_comps = big_material[0:2]
        del big_material[0:2]
        for nuc, _f in old_comps:
            assert nuc not in big_material
        with pytest.raises(TypeError):
            del big_material["hi"]
        pu_comp = big_material[-1]
        del big_material[-1]
        assert pu_comp[0] not in big_material
        _.verify_export(big_material)

    def test_material_values(_, big_material):
        # test iter
        for value in big_material.values:
            assert value == pytest.approx(0.05)
        assert len(list(big_material.values)) == len(big_material)
        # test getter setter
        for i, comp in enumerate(big_material):
            assert big_material.values[i] == pytest.approx(comp[1])
            big_material.values[i] = 1.0
            assert big_material[i][1] == pytest.approx(1.0)
        with pytest.raises(TypeError):
            big_material.values["hi"]
        with pytest.raises(IndexError):
            big_material.values[len(big_material) + 1]
        with pytest.raises(TypeError):
            big_material.values[0] = "hi"
        with pytest.raises(ValueError):
            big_material.values[0] = -1.0
        _.verify_export(big_material)

    def test_material_nuclides(_, big_material):
        # test iter
        for nuclide, comp in zip(big_material.nuclides, big_material):
            assert nuclide == comp[0]
            # test getter setter
        for i, comp in enumerate(big_material):
            assert big_material.nuclides[i] == comp[0]
            big_material.nuclides[i] = Nuclide("1001.80c")
            assert big_material[i][0] == Nuclide("1001.80c")
        with pytest.raises(TypeError):
            big_material.nuclides["hi"]
        with pytest.raises(IndexError):
            big_material.nuclides[len(big_material) + 1]
        with pytest.raises(TypeError):
            big_material.nuclides[0] = "hi"
        _.verify_export(big_material)

    @given(st.integers(1, 99), st.floats(1.9, 2.3), st.floats(0, 20, allow_nan=False))
    def test_material_append(_, Z, a_multiplier, fraction):
        mat = Material()
        mat.number = 5
        A = int(Z * a_multiplier)
        zaid = Z * 1000 + A
        nuclide = Nuclide(zaid)
        mat.append((nuclide, fraction))
        assert mat[0][0] == nuclide
        assert mat[0][1] == pytest.approx(fraction)
        _.verify_export(mat)

    def test_material_append_bad(_):
        mat = Material()
        with pytest.raises(TypeError):
            mat.append(5)
        with pytest.raises(ValueError):
            mat.append((1, 2, 3))
        with pytest.raises(TypeError):
            mat.append(("hi", 1))
        with pytest.raises(TypeError):
            mat.append((Nuclide("1001.80c"), "hi"))
        with pytest.raises(ValueError):
            mat.append((Nuclide("1001.80c"), -1.0))

    @pytest.mark.parametrize(
        "content, is_in",
        [
            ("1001.80c", True),
            (Element(1), True),
            (Nucleus(Element(1), 1), True),
            (Element(43), False),
            ("B-10.00c", False),
            (Nucleus(Element(5), 10), False),
        ],
    )
    def test_material_contains(_, big_material, content, is_in):
        assert is_in == (content in big_material), "Contains didn't work properly"
        with pytest.raises(TypeError):
            5 in big_material

    def test_material_str(_):
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

    def test_material_sort(_):
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

    def test_material_format_mcnp(_):
        in_strs = ["M20 1001.80c 0.5", "     8016.80c         0.5"]
        input_card = Input(in_strs, BlockType.DATA)
        material = Material(input_card)
        material.number = 25
        answers = ["M25 1001.80c 0.5", "     8016.80c         0.5"]
        output = material.format_for_mcnp_input((6, 2, 0))
        assert output == answers

    def test_material_comp_init(_):
        with pytest.raises(DeprecationWarning):
            MaterialComponent(Nuclide("1001"), 0.1)

    def test_mat_comp_init_warn(_):
        with pytest.raises(DeprecationWarning):
            MaterialComponent(Nuclide("1001.80c"), 0.1)

    def test_material_update_format(_):
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
    def test_material_library_slicer(_, libraries, slicer, answers):
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
    def test_material_init(_, line, mat_number, is_atom, fractions):
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
    def test_bad_init(_, line):
        # test invalid material number
        input = Input([line], BlockType.DATA)
        with pytest.raises(MalformedInputError):
            Material(input)

    @pytest.mark.filterwarnings("ignore")
    @given(st.integers(), st.integers())
    def test_mat_clone(_, start_num, step):
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
    def test_mat_clone_bad(_, args, error):
        input = Input(["m1 1001.80c 0.3 8016.80c 0.67"], BlockType.CELL)
        mat = Material(input)
        with pytest.raises(error):
            mat.clone(*args)

    @pytest.mark.parametrize(
        "index",
        [
            (1),  # TODO property testing
        ],
    )
    def test_material_access(_, big_material, index):
        big_material[index]
        # TODO actually test

    @pytest.mark.filterwarnings("ignore::montepy.errors.LineExpansionWarning")
    def test_add_nuclide_expert(_, big_material):
        _.verify_export(big_material)

    def verify_export(_, mat):
        output = mat.format_for_mcnp_input((6, 3, 0))
        print("Material output", output)
        new_mat = Material(Input(output, BlockType.DATA))
        assert mat.number == new_mat.number, "Material number not preserved."
        assert len(mat) == len(new_mat), "number of components not kept."
        for (old_nuc, old_frac), (new_nuc, new_frac) in zip(mat, new_mat):
            assert old_nuc == new_nuc, "Material didn't preserve nuclides."
            assert old_frac == pytest.approx(new_frac)
        for (old_type, old_lib), (new_type, new_lib) in zip(
            mat.default_libraries, new_mat.default_libraries
        ):
            assert old_type == new_type
            assert old_lib == new_lib


class TestThermalScattering:
    def test_thermal_scattering_init(_):
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

    def test_thermal_scattering_particle_parser(_):
        # replicate issue #121
        input_card = Input(["Mt20 h-h2o.40t"], BlockType.DATA)
        card = ThermalScatteringLaw(input_card)
        assert card.old_number == 20
        assert card.thermal_scattering_laws == ["h-h2o.40t"]

    def test_thermal_scatter_validate(_):
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

    def test_thermal_scattering_add(_):
        in_str = "Mt20 grph.20t"
        input_card = Input([in_str], BlockType.DATA)
        card = ThermalScatteringLaw(input_card)
        card.add_scattering_law("grph.21t")
        assert len(card.thermal_scattering_laws) == 2
        assert card.thermal_scattering_laws == ["grph.20t", "grph.21t"]
        card.thermal_scattering_laws = ["grph.22t"]
        assert card.thermal_scattering_laws == ["grph.22t"]

    def test_thermal_scattering_setter(_):
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

    def test_thermal_scattering_material_add(_):
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

    def test_thermal_scattering_format_mcnp(_):
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

    def test_thermal_str(_):
        in_str = "Mt20 grph.20t"
        input_card = Input([in_str], BlockType.DATA)
        card = ThermalScatteringLaw(input_card)
        assert str(card) == "THERMAL SCATTER: ['grph.20t']"
        assert (
            repr(card)
            == "THERMAL SCATTER: material: None, old_num: 20, scatter: ['grph.20t']"
        )


class TestDefaultLib:

    @pytest.fixture
    def mat(_):
        mat = Material()
        mat.number = 1
        return mat

    @pytest.fixture
    def dl(_, mat):
        return DL(mat)

    def test_dl_init(_, dl):
        assert isinstance(dl._parent(), Material)
        assert isinstance(dl._libraries, dict)

    @pytest.mark.parametrize(
        "lib_type, lib", [("nlib", "80c"), ("plib", "80p"), ("alib", "24a")]
    )
    def test_set_get(_, dl, lib_type, lib):
        lib_type_load = LibraryType(lib_type.upper())
        dl[lib_type] = lib
        assert dl[lib_type] == Library(lib), "Library not properly stored."
        assert (
            len(dl._parent()._tree["data"]) == 1
        ), "library not added to parent material"
        dl[lib_type_load] = Library(lib)
        dl[lib_type_load] == Library(lib), "Library not properly stored."
        del dl[lib_type]
        assert (
            len(dl._parent()._tree["data"]) == 0
        ), "library not deleted from parent material"
        assert dl[lib_type] is None, "Default libraries did not delete"
        assert dl["hlib"] is None, "Default value not set."

    def test_bad_set_get(_, dl):
        with pytest.raises(TypeError):
            dl[5] = "80c"
        with pytest.raises(TypeError):
            dl["nlib"] = 5
        with pytest.raises(TypeError):
            del dl[5]

    def test_dl_str(_, dl):
        str(dl)

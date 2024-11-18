# Copyright 2024, Battelle Energy Alliance, LLC All Rights Reserved.
import pytest
from hypothesis import assume, given, note, strategies as st, settings

import montepy

from montepy.data_inputs.element import Element
from montepy.data_inputs.nuclide import Nucleus, Nuclide, Library
from montepy.particle import LibraryType


class TestNuclide:
    def test_nuclide_init(_):
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

    def test_nuclide_metastable_init(_):
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

    def test_nuclide_get_base_zaid(_):
        isotope = Nuclide("92635.02c")
        assert isotope.get_base_zaid() == 92235

    def test_nuclide_library_setter(_):
        isotope = Nuclide("1001.80c")
        isotope.library = "70c"
        assert isotope.library == "70c"
        with pytest.raises(TypeError):
            isotope.library = 1

    def test_nuclide_str(_):
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
    def test_fancy_names(_, input, Z, A, meta, library):
        isotope = Nuclide(input)
        assert isotope.A == A
        assert isotope.Z == Z
        assert isotope.meta_state == meta
        assert isotope.library == Library(library)

    @given(
        st.integers(1, 118),
        st.floats(2.1, 2.7),
        st.integers(0, 4),
        st.integers(0, 999),
        # based on Table B.1 of the 6.3.1 manual
        # ignored `t` because that requires an `MT`
        st.sampled_from(
            [c for c in "cdmgpuyehporsa"]
        ),  # lazy way to avoid so many quotation marks
        st.booleans(),
    )
    def test_fancy_names_pbt(
        _, Z, A_multiplier, meta, library_base, library_extension, hyphen
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
            # this fixes a bug with the test????
            note((input, library))
            if "." in input:
                assert isotope.library == Library(library)
            else:
                assert isotope.library == Library("")


class TestLibrary:

    @pytest.mark.parametrize(
        "input, lib_type",
        [
            ("80c", LibraryType.NEUTRON),
            ("710nc", LibraryType.NEUTRON),
            ("50d", LibraryType.NEUTRON),
            ("50M", LibraryType.NEUTRON),
            ("01g", LibraryType.PHOTO_ATOMIC),
            ("84P", LibraryType.PHOTO_ATOMIC),
            ("24u", LibraryType.PHOTO_NUCLEAR),
            ("30Y", LibraryType.NEUTRON),
            ("03e", LibraryType.ELECTRON),
            ("70H", LibraryType.PROTON),
            ("70o", LibraryType.DEUTERON),
            ("70r", LibraryType.TRITON),
            ("70s", LibraryType.HELION),
            ("70a", LibraryType.ALPHA_PARTICLE),
        ],
    )
    def test_library_init(_, input, lib_type):
        lib = Library(input)
        assert lib.library_type == lib_type, "Library type not properly parsed"
        assert str(lib) == input, "Original string not preserved."
        assert lib.library == input, "Original string not preserved."

    @given(
        input_num=st.integers(min_value=0, max_value=999),
        extra_char=st.characters(min_codepoint=97, max_codepoint=122),
        lib_extend=st.sampled_from("cdmgpuyehorsa"),
        capitalize=st.booleans(),
    )
    def test_library_mass_init(_, input_num, extra_char, lib_extend, capitalize):
        if input_num > 100:
            input = f"{input_num:02d}{extra_char}{lib_extend}"
        else:
            input = f"{input_num:02d}{lib_extend}"
        if capitalize:
            input = input.upper()
        note(input)
        lib = Library(input)
        assert str(lib) == input, "Original string not preserved."
        assert repr(lib) == input, "Original string not preserved."
        assert lib.library == input, "Original string not preserved."
        assert lib.number == input_num, "Library number not preserved."
        assert lib.suffix == lib_extend, "Library suffix not preserved."
        lib2 = Library(input)
        assert lib == lib2, "Equality broke."
        assert hash(lib) == hash(lib2), "Hashing broke for library."

    @pytest.mark.parametrize(
        "input, error", [(5, TypeError), ("hi", ValueError), ("75b", ValueError)]
    )
    def test_bad_library_init(_, input, error):
        with pytest.raises(error):
            Library(input)
        lib = Library("00c")
        if not isinstance(input, str):
            with pytest.raises(TypeError):
                lib == input, "Type enforcement for library equality failed."

    def test_library_sorting(_):
        lib = Library("00c")
        with pytest.raises(TypeError):
            lib < 5
        libs = {Library(s) for s in ["00c", "70c", "70g", "50d", "80m", "24y", "90a"]}
        gold_order = ["90a", "00c", "70c", "50d", "70g", "80m", "24y"]
        assert [str(lib) for lib in sorted(libs)] == gold_order, "Sorting failed."

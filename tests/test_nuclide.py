# Copyright 2024, Battelle Energy Alliance, LLC All Rights Reserved.
from hypothesis import given, strategies as st
import pytest
from hypothesis import assume, given, note, strategies as st

import montepy

from montepy.data_inputs.element import Element
from montepy.data_inputs.nuclide import Nucleus, Nuclide, Library


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
            if library in input:
                assert isotope.library == Library(library)
            else:
                assert isotope.library == Library("")

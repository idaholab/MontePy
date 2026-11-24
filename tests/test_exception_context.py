# Copyright 2026, Battelle Energy Alliance, LLC All Rights Reserved.
import pytest

from montepy.mcnp_object import MCNP_Object


def test_wrap_string_for_mcnp_public_staticmethod_is_wrapped():
    # wrap_string_for_mcnp is a public staticmethod on MCNP_Object; the
    # _ExceptionContextAdder metaclass must wrap it like any other public
    # method so its errors get line-number context added, and it must
    # still work normally when called correctly.
    assert MCNP_Object.wrap_string_for_mcnp("hi", (6, 2, 0), True) == ["hi"]
    with pytest.raises(TypeError):
        MCNP_Object.wrap_string_for_mcnp(["hi"], (6, 2, 0), True)

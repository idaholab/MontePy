import pytest

import montepy
from montepy.mcnp_object import MCNP_Object


class TestErrorWrapper:

    def test_error_handler(_):
        obj = ObjectFixture()
        with pytest.raises(ValueError):
            obj.bad_static()
        with pytest.raises(ValueError):
            obj.bad_class()


class ObjectFixture(MCNP_Object):
    def __init__(self):
        pass

    def _update_values(self):
        pass

    def _init_blank(self):
        pass

    def _generate_default_tree(self):
        pass

    @staticmethod
    def _parser():
        pass

    def _parse_tree(self):
        pass

    @staticmethod
    def bad_static():
        raise ValueError("foo")

    @classmethod
    def bad_class(cls):
        raise ValueError("bar")


class TestErrorExceptionDeprecation:

    def test_deprecated_error(_):
        with pytest.warns(FutureWarning):
            montepy.errors.ParsingError

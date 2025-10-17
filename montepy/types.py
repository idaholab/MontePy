from collections.abc import Iterable, Callable
from numbers import Real, Integral
from typing import Annotated, Self

import montepy._check_value as cv


def positive(func_name, name):
    r"""
    A higher-order function to be used with ``args_checked`` to ensure a value is positive,
    i.e., :math:`x\gt 0`.

    Example
    ^^^^^^^

    .. testcode::

        from numbers import Real
        from typing import Annotated

        @args_checked
        def foo(a: Annotated[Real, positive]):
            pass

    """
    return lambda x: cv.check_greater_than(func_name, name, x, 0)


def negative(func_name, name):
    r"""
    A higher-order function to be used with ``args_checked`` to ensure a value is negative,
    i.e., :math:`x\lt 0`.

    Example
    ^^^^^^^

    .. testcode::

        from numbers import Real
        from typing import Annotated

        @args_checked
        def foo(a: Annotated[Real, negative]):
            pass

    """
    return lambda x: cv.check_less_than(func_name, name, x, 0)


def non_positive(func_name, name):
    r"""
    A higher-order function to be used with ``args_checked`` to ensure a value is non-positive,
    i.e., :math:`x\leq 0`.

    Example
    ^^^^^^^

    .. testcode::

        from numbers import Real
        from typing import Annotated

        @args_checked
        def foo(a: Annotated[Real, non_positive]):
            pass

    """
    return lambda x: cv.check_less_than(func_name, name, x, 0, True)


def non_negative(func_name, name):
    r"""
    A higher-order function to be used with ``args_checked`` to ensure a value is non-negative,
    i.e., :math:`x\geq 0`.

    Example
    ^^^^^^^

    .. testcode::

        from numbers import Real
        from typing import Annotated

        @args_checked
        def foo(a: Annotated[Real, non_negative]):
            pass

    """
    return lambda x: cv.check_greater_than(func_name, name, x, 0, True)


"""
Common types to be used for type annotations.
"""

PositiveInt = Annotated[Integral, positive]
r"""
An integer that is positive, i.e., a member of the set :math:`\mathbb{Z}_{\gt0}`.
"""

NegativeInt = Annotated[Integral, negative]
r"""
An integer that is negative, i.e., a member of the set :math:`\mathbb{Z}_{\lt0}`.
"""

NonNegativeInt = Annotated[Integral, non_negative]
r"""
An integer that is negative, i.e., a member of the set :math:`\mathbb{Z}_{\geq0}`.
"""

PositiveReal = Annotated[Real, positive]
r"""
A real number that is positive, i.e., a member of the set :math:`\mathbb{R}_{\gt0}`.
"""

NegativeReal = Annotated[Real, negative]
r"""
A real number that is negative, i.e., a member of the set :math:`\mathbb{R}_{\gt0}`.
"""

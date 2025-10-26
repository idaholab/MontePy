from collections.abc import Iterable, Callable
from numbers import Real, Integral
from typing import Annotated, Self

import montepy._check_value as cv


def positive(func_name, name, x):
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
    cv.check_greater_than(func_name, name, x, 0)


def negative(func_name, name, x):
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
    cv.check_less_than(func_name, name, x, 0)


def non_positive(func_name, name, x):
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
    cv.check_less_than(func_name, name, x, 0, True)


def non_negative(func_name, name, x):
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
    cv.check_greater_than(func_name, name, x, 0, True)


def less_than(maximum: Real, equality=False):
    r"""
    A higher-order function for use with ``args_checked`` to enforce a value being less than a value.


    Examples
    ^^^^^^^^
    This can be used to annotate a value

    .. testcode::

        import numbers
        import typing

        @args_checked
        def foo(a: typing.Annotated[numbers.Real, less_than(5)]):
            pass

    Parameters
    ----------
    maximum: Real
        The maximum value to be tested against.
    equality: bool
        if true test for :math:`x\leq m` rather than :math:`x\lt m`
    """

    def wrapper(func_name, name, x):
        cv.check_less_than(func_name, name, x, maximum, equality)

    return wrapper


def greater_than(minimum: Real, equality: bool = False):
    r"""
    A higher-order function for use with ``args_checked`` to enforce a value being greater than a value.


    Examples
    ^^^^^^^^
    This can be used to annotate a value

    .. testcode::

        import numbers
        import typing

        @args_checked
        def foo(a: typing.Annotated[numbers.Real, greater_than(5)]):
            pass

    Parameters
    ----------
    minimum: Real
        The minimum value to be tested against.
    equality: bool
        if true test for :math:`x\geq m` rather than :math:`x\gt m`
    """

    def wrapper(func_name, name, x):
        cv.check_greater_than(func_name, name, x, minimum, equality)

    return wrapper


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
NonNegativeReal = Annotated[Real, non_negative]
r"""
A real number that is not negative, i.e., a member of the set :math:`\mathbb{R}_{\geq0}`.
"""

VersionType = tuple[PositiveInt, NonNegativeInt, NonNegativeInt]

# Copyright 2026, Battelle Energy Alliance, LLC All Rights Reserved.
"""A helper for decorators, so the functions they wrap keep resolvable annotations."""

import builtins
import functools
import inspect
import types


def _global_names(code: types.CodeType) -> set[str]:
    """Every name ``code``, or code nested in it, may look up as a global."""
    names = set(code.co_names)
    for const in code.co_consts:
        if isinstance(const, types.CodeType):
            names |= _global_names(const)
    return names


def in_module_of(wrapper: types.FunctionType, func) -> types.FunctionType:
    """Rebuild ``wrapper`` so its ``__globals__`` name the module ``func`` was defined in.

    A decorator's wrapper runs in the globals of the module defining the
    decorator, and ``sphinx_autodoc_typehints`` evaluates the (postponed)
    annotations that :func:`functools.wraps` copies onto it in those globals,
    rather than in those of the wrapped function. A name that is only imported
    where the function is defined, e.g. ``PaddingNode``, then can't be
    resolved, and is documented as an unresolvable bare name.

    The rebuilt wrapper has the same code and closure. Its globals only hold
    what its own code looks up, and the ``__name__`` of the wrapped function's
    module, which is what tools that resolve annotations read to find that
    module.

    Parameters
    ----------
    wrapper : types.FunctionType
        The wrapper, already updated with :func:`functools.wraps`.
    func : Callable
        What ``wrapper`` wraps.

    Returns
    -------
    types.FunctionType
        The rebuilt wrapper, or ``wrapper`` itself if ``func`` isn't defined
        in a module, or already shares its globals.
    """
    target = inspect.unwrap(getattr(func, "__func__", func))
    target_globals = getattr(target, "__globals__", None)
    if (
        target_globals is None
        or target_globals is wrapper.__globals__
        # e.g. a function defined in a doctest, which has no module
        or "__name__" not in target_globals
    ):
        return wrapper
    namespace = {
        name: wrapper.__globals__[name]
        for name in _global_names(wrapper.__code__)
        if name in wrapper.__globals__
    }
    namespace["__name__"] = target_globals["__name__"]
    namespace["__builtins__"] = builtins
    rebuilt = types.FunctionType(
        wrapper.__code__,
        namespace,
        wrapper.__name__,
        wrapper.__defaults__,
        wrapper.__closure__,
    )
    rebuilt.__kwdefaults__ = wrapper.__kwdefaults__
    return functools.update_wrapper(rebuilt, func)


def wraps(func):
    """:func:`functools.wraps`, but the wrapper's globals name ``func``'s module.

    See :func:`in_module_of`.
    """

    def decorate(wrapper):
        return in_module_of(functools.wraps(func)(wrapper), func)

    return decorate

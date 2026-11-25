.. meta::
   :description lang=en:
        How to write decorators in MontePy so the wrapped functions keep resolvable type annotations in the documentation.

Writing Decorators
==================

Most of MontePy's public methods and properties are wrapped at least once:

* every method and property of an :class:`~montepy.mcnp_object.MCNP_Object` is wrapped by its
  ``_ExceptionContextAdder`` metaclass (in ``montepy/_exception_context.py``), which adds the
  input's file and line number to any exception;
* :func:`~montepy._check_value.args_checked` wraps a function to check its arguments;
* :func:`~montepy.utilities.needs_full_ast`, :func:`~montepy.utilities.make_prop_pointer`, and
  the other decorators in ``montepy/utilities.py`` wrap property getters and setters.

Use ``_wrapping.wraps``, not ``functools.wraps``
-------------------------------------------------

A decorator in MontePy must update its wrapper with ``montepy._wrapping.wraps``, a drop-in
replacement for :func:`functools.wraps`:

.. code-block:: python

    from montepy import _wrapping


    def my_decorator(func):
        @_wrapping.wraps(func)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)

        return wrapper

With :func:`functools.wraps` the documentation can't resolve the wrapped function's type
annotations.
MontePy uses ``from __future__ import annotations``, so annotations are strings, which
``functools.wraps`` copies onto the wrapper.
``sphinx_autodoc_typehints`` evaluates them in the wrapper's ``__globals__``, which are those of
the module defining the *decorator*, not of the wrapped function.
A name the wrapped function's module imports, e.g. ``PaddingNode`` in
``-> list[PaddingNode]``, isn't defined there, so it is documented as an unresolvable bare name,
which fails the strict (``-W``) documentation build.

``_wrapping.wraps`` rebuilds the wrapper (same code and closure) with globals naming the
wrapped function's module, so the annotations are evaluated there.
Those globals only hold ``__name__``, ``__builtins__``, and the names the wrapper's own code
uses, copied when the function is decorated.
A wrapper should therefore only use globals, such as imported functions, that exist when it is
decorated.
A function defined outside of a module, e.g. in a doctest, is left as is.

``type`` cross-references
-------------------------

``ShortcutNode.type`` and ``ValueNode.type`` are documented attributes named ``type``.
Sphinx resolves a type in a docstring field or annotation by also searching for any attribute
whose name ends in ``.type``, so a plain ``type`` (e.g. ``type[Tally]``) would be ambiguous
between the two.
``doc/source/conf.py`` has a ``doctree-read`` hook that resolves such a ``type`` reference to the
builtin instead.
Even so, a docstring type should name the actual class, e.g. ``type[MCNP_Lexer]``, rather than a
bare ``type``.

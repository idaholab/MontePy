.. meta::
   :description lang=en:
        How to use args_checked, typing.Annotated, and montepy.types for type and value enforcement in MontePy.

.. _args_type:

Type and Value Enforcement
==========================

A core principle of MontePy is that users will make mistakes and sometimes provide invalid values,
either the wrong data type, or a nonsensical value.
Montepy is moving to type annotations, and decorator magic to enforce this validity,
rather than relying on a series of boiler plate type and value checks.
All of the core functionalities required are from :mod:`montepy.utilities`.
Useful types are stored in :mod:`montepy.types`.

Enforcing a Function's Annotations
------------------------------------

The decorator, :func:`~montepy._check_value.args_checked`, will at run time check that all values passed to a
function are of type (and sometimes the correct value), as detailed in the type annotations.

For type enforcement this is simple enough:

.. doctest::

        >>> from montepy.utilities import *
        >>> import montepy.types as ty
        >>>
        >>> @args_checked
        ... def foo(a: int) -> int:
        ...    return a
        >>> print(foo(1))
        1
        >>> print(foo("a"))
        Traceback (most recent call last):
        ...
        TypeError: Unable to set "a" for "foo" to "a" which is not of type "int"

For more complex types, `typing.Union <https://docs.python.org/3/library/typing.html#typing.Union>`_ can be used. For instance:

.. testcode::

   from numbers import Integral


   @args_checked
   def bar(a: Integral | str):
       pass

.. Note::

   The pipe syntax is preferred for specifying ``typing.Union``, e.g., ``Integral | str``.

.. Note::

   When working with numbers avoid using the types ``float`` and ``int``.
   An ``int`` can substitute for a ``float`` in almost all cases, and
   sometimes libraries, like numpy, provide their own equivalent types.
   Rather you should use the `numbers <https://docs.python.org/3/library/numbers.html>`_ package instead.
   Specifically ``numbers.Real`` and ``numbers.Integral`` are the most commonly used types in
   MontePy.

.. Note::

   ``args_checked`` will work recursively through a data structure, so the type:

   .. code-block:: python

        type FancyData = dict[
            tuple[str, Integral],
            list[list[Real]]
        ]

   would be properly enforced.


Use with ``__future__.annotations``
-------------------------------------

Sometimes it is necessary to include:

``from __future__ import annotations``

in order avoid circular imports in MontePy.
`See the python documentation <https://docs.python.org/3/library/__future__.html#future__.annotations>`_ for details.

What this does is treat type annotations as strings, and not evaluate them.
When this is done ``args_checked`` will evaluate the type annotation at run time, so import errors will not appear until the function is ran.

Value Enforcement
------------------

MontePy also supports value enforcement in the type annotations,
through `typing.Annotated <https://docs.python.org/3/library/typing.html#typing.Annotated>`_
allowed values can also be specified.
MontePy provides functions for the most common value checks, such as :func:`~montepy.types.positive`. For instance:

.. testcode::

   from typing import Annotated
   import montepy.types as ty

   @args_checked
   def foo(a: Annotated[Integral, ty.positive]):
        pass

Some enforcers accept arguments, such as :func:`~montepy.types.greater_than`:

.. testcode::

   @args_checked
   def foo(a: Annotated[Integral, ty.greater_than(5)]):
       pass

Though you can see how this will become very verbose very quickly.
So :mod:`montepy.types` is meant to store most of these ``Annotated`` types.

.. note::

   Multiple arguments can be given ``Annotated`` for instance if you needed a value to be in:
   (0, 5), you could write:

   .. code-block:: Python

        import montepy.types as ty

        def foo(a: Annotated[ty.Real, ty.positive, ty.less_than(5)]):
             pass

Writing a Custom Value Enforcer
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

MontePy uses higher-order functions, functions that return functions, to create value enforcers.
It is helpful to look through the value enforcement process to understand why.

#. A custom type is created/Annotated.
   A new type is created with the enforcer stored as ``AnnotatedTypeAlias.__metadata__``.
   For some enforcers, such as :func:`~montepy.types.greater_than`, this stage will accept arguments.
#. The function is called. At this stage the wrapped function is called, and all of the enforcer functions are called with the actual values passed before the nested decorated function is called. The functions must accept the arguments: ``(func_name, name, value)``.

Some pseudo-implementations may be helpful here.
For a simple implementation, let's look at how :func:`~montepy.types.positive` could be written:

.. code-block:: python

   def positive(func_name, name, x):
       if x <= 0:
           raise ValueError(
               f"The value, {x}, given to {func_name} for argument, {name} is not positive"
           )

For a more complicated scenario let's look at how you might implement :func:`~montepy.types.greater_than`:

.. code-block:: python

   def greater_than(minimum: Real):

        def enforcer_generator(func_name, name, x):
            if x <= minimum:
                 raise ValueError(
                     f"The value, {x}, given to {func_name} for argument, {name} is not greater than the minimum, {minimum}"
                 )
        return enforcer_generator

Example
--------

Note that this below example is the preferred method to import the types and ``args_checked``.

.. testcode::

   from montepy.utilities import *
   import montepy.types as ty

   @args_checked
   def foo(a: str, b: ty.PositiveInt):
       pass

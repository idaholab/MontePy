.. meta::
   :description lang=en:
        How MontePy uses pointers, generators, and constants for maintainable, mutation-tolerant code.

Pointers, Generators, and Constants
=====================================

On the Use of Pointers and Generators
---------------------------------------

First you might be saying there are no pointers in python.
There are pointers you just don't see them.
If these examples aren't clear reach out to one of the core developers.

MontePy abuses pointers a lot.
This will talk a lot like a Rust reference book about ownership and borrowing.
There aren't true parallels in python though.
In this section ownership is considered the first instance of an object,
which should basically live for the lifetime of the problem.
For a ``Surface`` it is owned by the ``Surfaces`` collection owned by the ``MCNP_Problem``.
A cell then borrows this object by referencing it in its own ``Surfaces`` collections.
For example:

.. doctest::

    >>> import montepy
    >>> # owns
    >>> x = montepy.Cell()
    >>> old_id = hex(id(x))
    >>> # borrows
    >>> new_list = [x]
    >>> old_id == hex(id(new_list[0]))
    True

The general principle is that only one-directional pointers should be used,
and bidirectional pointers should never be used.
This is due to the maintenance overhead with mutation.
For instance: a cell knows the surface objects it uses,
but a surface doesn't always know what cell object uses it.
This is a one-directional pointer,
if the surfaces did know, this would be bidirectional.

So how do we decide which direction to point?
In general we should default to MCNP.
So a cell borrows a surface because a cell input in MCNP
references surface numbers,
and not vice versa.
The exception to this is the case of inputs that modify another object.
For example the ``MT`` input modifies its parent ``M`` input.
In general the parent object should own its children modifiers.
This is an area of new development, and this may change.

So how do we get a surface to know about the cells it uses?
With generators!
First, one effectively bi-directional pointer is allowed;
inputs are allowed to point to the parent problem.
This is provided through ``self._problem``, and
is established by: :func:`~montepy.mcnp_object.MCNP_Object.link_to_problem`.
With this the surface can find its cells by::

    @property
    def cells(self):
        if self._problem:
            for cell in self._problem.cells:
                if self in cell.surfaces:
                    yield cell

So why generators and not functions?
This is meant to force the data to be generated on the fly,
so it is tolerant to mutation.
If we were to return a list a user is much more likely to store that,
and use that instead.
If we make it easy to just say::

        if cell in surface.cells:
                pass

Users are more like to use this dynamic code.
In general this philosophy is: if it's not the source of truth,
it should be a generator.

Constants and Meta Data Structures
------------------------------------

MontePy uses constants and data structures to utilize meta-programming
and remove redundant code.
Typical constants can be found in :mod:`montepy.constants`.

Here are the other data structures to be aware of:

* :class:`~montepy.MCNP_Problem` ``_NUMBERED_OBJ_MAP``: maps a based numbered object to its collection
  class. This is used for loading all problem numbered object collections in an instance.
* ``PREFIX_MATCHES`` is a set of the data object classes. The prefix is taken from
  the classes. A data object must be a member of this class for it to automatically parse new data objects.
* :class:`~montepy.Cell` ``_INPUTS_TO_PROPERTY`` maps a cell modifier class to the attribute to load it into for a
  cell. The boolean is whether multiple input instances are allowed.

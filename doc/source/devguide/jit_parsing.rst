.. meta::
   :description lang=en:
        How just-in-time (JIT) parsing works in MontePy, and how to add JIT support to a new MCNP_Object subclass.

.. _jit-parsing:

Just-in-Time (JIT) Parsing
===========================

By default, MontePy defers the full parse of each input until the data are actually
needed.
On first read only a lightweight "JIT" parse is performed: enough to categorize
the input and extract its number (for
:class:`~montepy.numbered_mcnp_object.Numbered_MCNP_Object` subclasses).
The raw :class:`~montepy.input_parser.mcnp_input.Input` object is stored and the full
parse is triggered on-demand.

How it Works
-------------

#. ``MCNP_Object.__init__`` is called with ``jit_parse=True`` (the default).
#. ``_jit_light_init`` instantiates ``self._JitParser()``, parses only the first few
   tokens, and stores the results as instance attributes.
   The attribute ``_not_parsed = True`` is set as a marker.
#. If the JIT parse raises **any** exception (including ``AttributeError`` when
   ``_JitParser`` is not defined), the exception is caught and a full parse is
   performed automatically as a fallback.
   JIT parsing is explicitly "fast and dirty" — correctness is guaranteed by this
   fallback, not by the JIT parser itself.
#. When the full data are required, :func:`~montepy.mcnp_object.MCNP_Object.full_parse`
   is called.
   This re-runs ``__init__`` with ``jit_parse=False``, triggering a full parse via
   ``_parse_tree``.
   Any attributes listed in ``_KEYS_TO_PRESERVE`` are carried over from the JIT state.

.. warning::

   JIT parsers must be context-free (no state, no look-back).
   Do **not** add context-sensitive logic to a ``_JitParser``.
   Keep it minimal: parse only what is needed to categorize the input and read its
   number.
   Anything that could fail gracefully will be handled by the automatic fallback to
   full parsing.

``needs_full_ast`` vs ``needs_full_cst``
------------------------------------------

Two decorators are provided to trigger a full parse on demand.
They differ in *what kind* of parsed data they signal is needed:

:func:`~montepy.utilities.needs_full_ast`
   Use on **getters** (reading data).
   Signals that an Abstract Syntax Tree (AST) — the semantic values — is sufficient.

:func:`~montepy.utilities.needs_full_cst`
   Use on **setters and deleters** (modifying data).
   Signals that a Concrete Syntax Tree (CST) — which preserves whitespace and
   comment formatting — is required so that the modified input can be written back
   faithfully.

Both decorators currently call ``self.full_parse()`` and are therefore functionally
identical.
The distinction is preserved as infrastructure for a possible future where JIT parsing
can provide a partial AST (enough for reads) without yet building the full CST (needed
for writes).
Using the correct decorator now ensures that future optimization can be applied without
changing call sites.

.. code-block:: python

    from montepy.utilities import needs_full_ast, needs_full_cst

    @property
    @needs_full_ast          # reading: AST is sufficient
    def density(self):
        return self._density_node.value

    @density.setter
    @needs_full_cst          # writing: CST required for faithful round-trip output
    def density(self, value):
        self._density_node.value = value

Supporting JIT Parsing in a New Class
----------------------------------------

To add JIT support to a new class:

#. Set ``_JitParser`` to the lightweight, context-free parser class that parses only
   the minimum needed tokens (number, classifier, etc.):

   .. code-block:: python

       class MyInput(MCNP_Object):

           @staticmethod
           def _parser():
               return MyFullParser()

           _JitParser = MyJitParser

#. If any data must survive the JIT → full-parse transition (e.g., problem links
   established between the two steps), add those attribute names to
   ``_KEYS_TO_PRESERVE``:

   .. code-block:: python

       _KEYS_TO_PRESERVE = {"_some_attr"}

#. Decorate getters with ``@needs_full_ast`` and setters/deleters with
   ``@needs_full_cst``.

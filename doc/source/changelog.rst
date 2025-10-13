*****************
MontePy Changelog
*****************

1.1 releases
============

#Next Release#
--------------

**Documentation**

* Improved documentation for NumberedObjectCollections on Slicing behavior. (:issue:`798`)

**Bugs Fixed**

* Fixed bug where lines that were the allowed length was raising a ``LineOverRunWarning`` when read by MontePy (:issue:`517`). 

* Added descriptive TypeError messages (:issue:`801`)



1.1.2
--------------

**Code Quality**

* Refactor ``montepy.errors`` to ``montepy.exceptions``, to reflect that it also contains warnings (:issue:`764`).

**Deprecations**

* Marked ``montepy.errors`` as deprecated, with a ``FutureWarning``, use ``montepy.exceptions`` instead. (:issue:`764`).

**Bugs Fixed**

* Fixed parsing error where MontePy could not handle a fill matrix that was sparse (:issue:`601`).


1.1.1
--------------

**Features Added**

* Added demonstration jupyter notebooks for working with Pin Cell and PWR assemblies in MontePy.

**Bugs Fixed**

* Fixed bug where surfaces created from scratch couldn't be accurately written out to the file (:issue:`652`).
* Fixed bug where surface transformations couldn't be unset and exported properly (:issue:`711`).
* Fixed bug where negative numbers were treated as valid by ``append_renumber`` (:issue:`690`).
* Fixed bug that couldn't parse ``SDEF`` by simply not parsing the input for the time being (:pull:`767`).
* Fixed parsing bug with ``DE LOG`` style inputs by simply not parsing them for now (:pull:`767`).


1.1.0
--------------

**Features Added**

* Added ``Universe.filled_cells``, a generator that yields the cells filled with that universe instance (:issue:`361`).
* Added ``__eq__`` dunder method to ``Universe`` to support equality comparisons (:issue:`361`).
* Changed general plane constants checker to support more than 9 constants (:issue:`761`).

**Bugs Fixed**

* Fixed bug where MontePy would overly aggressively round outputs and remove the user's intent (:issue:`756`).
* Fixed bug where a cell complement in the first five characters causes a spurious vertical mode detection (:issue:`753`).


1.0 releases
============

1.0.0
--------------

**Features Added**

* Redesigned how Materials hold Material_Components. See :ref:`migrate 0 1` (:pull:`507`). 
* Made it easier to create an Isotope (now Nuclide): ``montepy.Nuclide("H-1.80c")`` (:issue:`505`).
* When a typo in an object attribute is made an Error is raised rather than silently having no effect (:issue:`508`).
* Improved material printing to avoid very long lists of components (:issue:`144`).
* Allow querying for materials by components (:issue:`95`), either broadly or specifically (:issue:`642`).
* Added support for getting and setting default libraries, e.g., ``nlib``, from a material (:issue:`369`).
* Added most objects to the top level so they can be accessed like: ``montepy.Cell``.
* Made ``Material.is_atom_fraction`` settable (:issue:`511`). 
* Made NumberedObjectCollections act like a set (:issue:`138`).
* Automatically added children objects, e.g., the surfaces in a cell, to the problem when the cell is added to the problem (:issue:`63`).
* Added ability to parse all MCNP objects from a string (:issue:`88`).
* Added function: :func:`~montepy.mcnp_problem.MCNP_Problem.parse` to parse arbitrary MCNP object (:issue:`88`).
* An error is now raised when typos in object attributes are used, e.g., ``cell.nubmer`` (:issue:`508`).
* Warnings are no longer raised for comments that exceed the maximum line lengths (:issue:`188`).
* Particle type exceptions are now warnings, not errors (:issue:`381`).
* Added :func:`~montepy.data_inputs.material.Material.clear` to ``Material`` to clear out all nuclides (:issue:`665`).
* Allow any ``Real`` type for floating point numbers and any ``Integral`` type for integer numbers during type enforcement (:issue:`679`).
* Avoided multiple ``LineExpansionWarnings`` coming from the same object on export (:issue:`198`).
* Added ``mcnp_str`` function to all ``MCNP_Object`` to quickly get the string that would be printed in the MCNP input file (:issue:`700`).
* Added ``montepy.MCNP_VERSION`` as an easy way to set the default MCNP version to target for reading and writing input files (:issue:`700`).
* Renamed `Cell.lattice` to `Cell.lattice_type`, `Lattice` to `LatticeType`, and `LatticeType.HEXAHEDRA` to `LatticeType.HEXAHEDRAL` with deprecation warnings (:issue:`728`).

**Bugs Fixed**

* Made it so that a material created from scratch can be written to file (:issue:`512`).
* Added support for parsing materials with parameters mixed throughout the definition (:issue:`182`).
* Fixed bug where ``surf.is_reflecting`` would put an extra space in the output e.g., ``* 1 PZ...`` (:issue:`697`).
* Fixed bug where setting a lattice would print as ``LAT=None``. Also switched ``CellModifier`` to print in the cell block by default (:issue:`699`). 
* Fixed bug that wouldn't allow cloning most surfaces (:issue:`704`).
* Fixed bug that crashed when some cells were not assigned to any universes (:issue:`705`).
* Fixed bug where setting ``surf.is_reflecting`` to ``False`` did not always get exported properly (:issue:`709`). 
* Fixed bug where setting multiple universes for a cell fill not being properly exported (:issue:`714`).
* Fixed bug where the ``i`` ("x") and ``k`` ("z") dimensions of multiple universe matrix ``fills`` were switched (:issue:`726`).
* Fixed bug 549 — corrected blank importance printing issue (:issue:`549`).
 
**Breaking Changes**

* Removed :func:`~montepy.data_inputs.material.Material.material_components``. See :ref:`migrate 0 1` (:pull:`507`).
* Removed :class:`~montepy.data_inputs.isotope.Isotope` and changed them to :class:`~montepy.data_inputs.nuclide.Nuclide`.
* Removed :func:`~montepy.mcnp_problem.MCNP_Problem.add_cell_children_to_problem` as it is no longer needed. 

**Deprecated code Removed**

* ``montepy.Cell.geometry_logic_string``
* ``montepy.data_inputs.cell_modifier.CellModifier.has_changed_print_style``
* ``montepy.data_inputs.data_input.DataInputAbstract``
 
  * ``class_prefix``
  * ``has_number``
  * ``has_classifier``

* ``montepy.input_parser.mcnp_input.Card``
* ``montepy.input_parser.mcnp_input.ReadCard``
* ``montepy.input_parser.mcnp_input.Input.words``
* ``montepy.input_parser.mcnp_input.Comment``
* ``montepy.input_parser.mcnp_input.parse_card_shortcuts``
* ``montepy.mcnp_object.MCNP_Object``

  * ``wrap_words_for_mcnp``
  * ``compress_repeat_values``
  * ``compress_jump_values``
  * ``words``
  * ``allowed_keywords``

0.5 releases
============

0.5.5
--------------

**Bug Fixes**

* Fixed parsing bug with sigma baryon particles (e.g., ``+/-``) (:issue:`671`).

0.5.4
--------------

**Bug Fixes**

* Fixed parsing error with not being able to parse a blank ``sdef`` (:issue:`636`).
* Fixed parsing error with parsing ``SSW`` (:issue:`639`).

0.5.3
--------------

**Bug Fixes**

* Fixed how material components work so new components can actually be added to a material and exported (:issue`597`).

0.5.2
--------------

**Error Handling**

* Added the input file, line number, and the input text to almost all errors raised by ``MCNP_Object`` (:pull:`581`).

0.5.1
--------------

**Bug Fixes**

* Fixed ``AttributeError`` that occured when a data block ``IMP`` was preceded by a comment (:issue:`580`).
* Fixed bug where tally inputs in a file prevented the file from being pickled or copied (:issue:`463`).

0.5.0
--------------

**Features Added**

* Added ``clone`` method to simplify making copies of objects (:issue:`469`).

**Performance Improvement**

* Fixed cyclic memory reference that lead to memory leak in ``copy.deepcopy`` (:issue:`514`).
* Fixed O(N\ :sup:`2`) operation in how append works for object collections like Cells (:issue:`556`).

**Bug Fixes**

* Fixed bug with parsing an ``EO`` input (:issue:`551`).
* Fixed a bug raised in an edge case when editing cell geometry, by making the error clearer (:issue:`558`).
* Fixed bug with having a shortcut in a cell fill (:issue:`552`).
* Fixed bug where file streams couldn't actually be read (:pull:`553`).

**Support**

* Added support for Python 3.13, and removed support for Python 3.8, and officially added support NumPy 1 & 2 (:pull:`548`).

0.4 releases
============

0.4.1
----------------

**Features Added**

* Added support for reading an input from either file paths or streams (file handles) with ``montepy.read_input`` (:issue:`519`).

**Bug Fixes**

* Fixed a bug where ``problem.materials.append_renumber`` would double add a material to ``problem.data_inputs`` (:issue:`516`).
* Fixed bug where material-level library specifications (e.g., ``m1 plib=84p``) could not be fully parsed (:issue:`521`).
* Fixed bug with shortcuts right after another shortcut (e.g., ``1 2M 3R``) not being properly recompressed on export (:issue:`499`).
* Fixed bug with shortcuts in cell geometry definitions not being recompressed on export (:issue:`489`).
* Fixed bug where leading comments were not always transferred to the appropriate input. (:issue:`352`, :issue:`526`).

**Performance Improvement**

* Fixed method of linking ``Material`` to ``ThermalScattering`` objects, avoiding a very expensive O(N :sup:`2`) (:issue:`510`).

**Deprecations**

* Marked ``Material.material_components`` as deprecated, and created migration plan describing what to expect moving forward (:issue:`506`).

0.4.0
--------------

**Features Added**

* Write problems to either file paths or streams (file handles) with MCNP_Problem.write_problem() (:issue:`492`).
* When adding a material to problem.materials it will also be added to problem.data_inputs, ensuring it is printed to the file (:pull:`488`).

**Bug Fixes**

* Fixed bug that didn't show metastable states for pretty printing and isotope. Also handled the case that Am-241 metstable states break convention (:issue:`486`).
* Fixed bug where cell modifiers could be made irrelevant by being added after a comment (:issue:`483`).
* Fixed bug where parentheses in cell geometry are not properly exported (:pull:`491`).


0.3 releases
=============

0.3.3
--------------

**Bug fixes**

* Fixed bug with material compositions not being updated when written to file (:issue:`470`).
* Fixed bug with appending and renumbering numbered objects from other MCNP problems (:issue:`466`).
* Fixed bug with dynamic typing and the parsers that only appear in edge cases (:issue:`461`).
* Fixed parser bug with having spaces in the start of the transform input for the fill of a cell (:pull:`479`).
* Fixed bug with trying to get trailing comments from non-existant parts of the syntax tree (:pull:`480`).

**Code Quality**

* Simpler ``Isotope`` representation (:issue:`473`).


0.3.2
--------------

**Bug fixes**

* Fixed bug with trailing dollar sign comments that moved them to a new line. (:issue:`458`).

0.3.1
----------------

**Bug fixes**

* Fixed parser bug with parsing cells with implicit intersection, e.g., ``(1:-2)(3:-4)``. (:issue:`355`).


0.3.0
-------------------

**Features Added**

* ``overwrite`` argument added to ``MCNP_Problem.write_to_file`` to ensure files are only overwritten if the user really wants to do so (:pull:`443`).

**Bug fixes**

* Fixed bug with ``SDEF`` input, and made parser more robust (:issue:`396`).


0.2 releases
============

0.2.10
----------------------

**Bug fixes**

* Fixed bug with parsing tally segments (:issue:`377`)

0.2.8
----------------------


**Documentation**

* Added link to the PyPI project on the Sphinx site (:issue:`410`)
* Added link shortcuts for MCNP manual, and github issues and pull requests (:pull:`417`).
* Added discussion of MCNP output files to FAQ (:issue:`400`).
* Updated MCNP 6.3 manual link to point to OSTI/DOI (:issue:`424`).

**CI/CD**

* Fixed project metadata for author to show up correctly on PyPI (:pull:`408`)
* Removed automated versioning from CI/CD, and simplified deploy process (:pull:`418`)

0.2.7
-----------------------

**Bug fixes**

* Made versioning system more robust for all situations (:issue:`386`).
* Fixed bug with handling `read` inputs, and made parser more efficient (:issue:`206`)
* Fixed bug that couldn't read materials without a library. E.g., `1001` vs. `1001.80c` (:issue:`365`). 

**Documentation**

* Added changelog
* Added contribution guideline
* Added pull request template

**CI/CD**

* Improved coveralls integration so actual source code can be shown.
* Improved sphinx build process (:issue:`388`)


0.2.5
-------------------

**Added**

* Implemented Github actions
* Added default github issue templates

**Changed**

* Improved readme and documentation hyperlinks

**Fixed**

* bug with comments in complex geometry.


0.2.4
-------------------
**Added**

* Public release

0.2.3
--------------------
**Added**

* A license
* A logo

**Changed**

* Explicitly set file encoding for read/write. :issue:`159`.

**Fixed**

* Bug with not detecting comments with no space e.g., `c\n`. :issue:`158`.

0.2.2
--------------------
**Fixed**

* TODO

0.2.1
---------------------
**Fixed**

* A bug with the packaging process

0.2.0
----------------------
**Added**

* User formatting is preserved automatically
* Cell geometry is now stored in `cell.geometry` and can be set with bitwise operators. e.g., `cell.geometry = + inner_sphere & - outer_sphere`. This was heavily influenced by OpenMC.
* You can now check an input file for errors from the command line. `python -m montepy -c /path/to/inputs/*.imcnp`
* The error reporting for syntax errors should be much more intuitive now, and easy to read.
* Dollar sign comments are kept and are available in `obj.comments`
* All comments are now in a generator `.comments`

**Deprecated**

* `montepy.data_cards` moved to `montepy.data_inputs`
* `montepy.data_cards.data_card` is now `montepy.data_inputs.data_input`
* `Montepy.Cell.geometry_logic_string` was completely removed.
* Much of the internal functions with how objects are written to file were changed and/or deprecated.
* `montepy.data_cards.data_card.DataCard.class_prefix` was moved to `_class_prefix` as the user usually shouldn't see this. Same goes for `has_classifier` and `has_number`.
* Most of the data types inside `montepy.input_parser.mcnp_input` were deprecated or changed

0.1 releases
============

0.1.7
-----------------

**Added**

* License information

0.1.6
-------------------

**fixed**

* Fixed bug that `+=` didn't work with Numbered object collections
* Updated the Documentation URL for sphinx
* Improved (and then removed) guidance on weird gitlab installation workflow.

0.1.5
--------------------

**Fixed**

* When a `PX` style surface was `1 PZ 0` this would cause a validation error.
* Empty "cell modifiers" would be printed in the data block even if they had no useful information. E.g., `U 30J`
* Volumes couldn't start with a jump e.g., `vol j 1.0`
* "Cell modifiers" were printed both in the cell block and the data block.
* Running `problem.cells = []` would make the problem impossible to write to file.
* Support was added for tabs.

0.1.0
---------------------


**Added**

* Added infrastructure to support cell modifier inputs easily
* Added support for importances, and particle modes: `imp`, `mode`.
* Added support for cell volumes `vol`.
* Add support for Universes, lattices, and fills `U`, `fill`, `lat`.
* Created universal system for parsing parameters
* If you create an object from scratch and write it out to a file while it is missing, it will gracefully fail with a helpful error message.
* Added support for detecting metastable isotopes.
* Improved the experience with densities in `Cell` instead of having `cell.density` now there is `cell.mass_density` and `cell.atom_density`.


**Fixed**

* Supported parameters that don't have equal signs. MCNP supports `1 0 -1 u 1`
* Now doesn't try to expand shortcuts inside of `FC` and `SC` comments.

**Code Quality**

* Removed magic numbers for number of characters in a line.
* Reduced the usage of regular expressions
* Made error messages related to invalid user set attributes clearer.
* Cleaned up documentation and docstrings
* Improved CI backend


0.0.5
-----------------------

**Added:**

 * `NumberedObjectCollections` which is implemented for `cells`, `surfaces`, and `materials`. This changed these collections from being a list to acting like a dict. Objects are now retrievable by their number e.g., `cells[1005]` will retrieve cell 1005.
 *  Implemented "pass-through" of the original inputs. If an object is not edited or mutated, the original formatting from the input file will be copied out to the output.
 * Support was added for most MCNP shortcuts: (`R`, `I`, `M`, `LOG`), `J` still needs some better support. MontePy will expand these shortcuts, but will not "recompress" them.
 * Added sphinx documentation website. This documents the API, has a starting guide for the users, and a guide for developers.


**Changed:**

* Object numbers are now generalized: e.g., `cell.cell_number` has changed to `cell.number`. The `.number` property is standardized across all numbered objects.

**Fixed:**

* Comments in the middle of an input no longer breaks the input into two.

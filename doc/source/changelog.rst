*****************
MontePy Changelog
*****************

0.5 releases
============

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
* Fixed O(N<sup>2</sup>) operation in how append works for object collections like Cells (:issue:`556`).

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
--------------

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

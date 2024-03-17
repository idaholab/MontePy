MontePy Changelog
=================

#Next Version#
-----------------------

**Documentation**

* Added changelog
* Added code of conduct
* Added contribution guideline
* Added pull request template


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

* Explicitly set file encoding for read/write. #159.

**Fixed**

* Bug with not detecting comments with no space e.g., `c\n`. #158.

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

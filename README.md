# MontePy

<img src="https://raw.githubusercontent.com/idaholab/MontePy/develop/graphics/monty.svg" width="180" alt="MontePY: a cute snek on a red over white circle"/>

[![license](https://img.shields.io/github/license/idaholab/MontePy.svg)](https://github.com/idaholab/MontePy/blob/develop/LICENSE)
[![Coverage Status](https://coveralls.io/repos/github/idaholab/MontePy/badge.svg?branch=develop)](https://coveralls.io/github/idaholab/MontePy?branch=develop)
[![PyPI version](https://badge.fury.io/py/montepy.svg)](https://badge.fury.io/py/montepy)

MontePy is a python library to read, edit, and write MCNP input files. 

## Installing

See the [Installing section in the user guide](https://idaholab.github.io/MontePy/starting.html#installing).


## User Documentation

MontePy has a [sphinx website](https://idaholab.github.io/MontePy/index.html). 
This has a getting started guide for users,
as well as API documentation. 
There is also a developer's guide covering the design and approach of MontePy, and how to contribute.

## Features
	
* Handles almost all MCNP input syntax including: message blocks, & continue, comments, etc.
* Parses Cells, surfaces, materials, and transforms very well.	
* Can parse the following surfaces exactly P(X|Y|Z), C(X|Y|Z), C/(X|Y|Z) (I mean it can do PX, and PY, etc.)
* Can read in all other inputs but not understand them	
* Can write out full MCNP problem even if it doesn't fully understand an input.	
* Can write out the MCNP problem verbatim, and try to match the original user formatting. 
* Can quickly access cells, surfaces, and materials by their numbers. For example: `cell = problem.cells[105]`.
* Can quickly update cell importances. For example `cell.importance.neutron = 2.0`.
* Has over 240 test cases right now 

 
Quick example for renumbering all of the cells in a problem:

```python
import montepy
foo = montepy.read_input("foo.imcnp")
i = 9500
for cell in foo.cells:
  cell.number = i
  i = i + 5
  
foo.write_to_file("foo_update.imcnp")

```

## Limitations

Here a few of the known bugs and limitations:

	
* Cannot handle vertical input mode.
* Does not support tallies in an easy way.
* Does not support source definition in an easy way.
	
## Bugs, Requests and Development

So MontePy doesn't do what you want? Right now development is done with a  Just-In-Time development approach, as in features are added JIT for a developer to use them on my current projects. 
If there's a feature you want add an issue here with the feature request tag. 
If you want to add a feature on your own talk to Micah Gale (but still add the issue). 
The system is very modular and you should be able to develop it pretty quickly.
Also read the [developer's guide](https://idaholab.github.io/MontePy/developing.html).

# Version Numbering Scheme

* Software on `develop` and feature branches are subject to change without a version number increment. These version
  may be suffixed as dev (e.g., `0.1.0.dev2`) and may change as features and bug fixes are implemented.

* Versions are official if and only if they are:
   1. on the branch `main`.
   1. has a release git tag assigned
   1. has distribution packages created and released
   Official shall not change. New merges to main shall have a version number incremented.

 
# Finally: make objects not regexes!

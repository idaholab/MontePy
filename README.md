# MontePy

<img src="https://raw.githubusercontent.com/idaholab/MontePy/develop/graphics/monty.svg" width="180" alt="MontePY: a cute snek on a red over white circle"/>

[![license](https://img.shields.io/github/license/idaholab/MontePy.svg)](https://github.com/idaholab/MontePy/blob/develop/LICENSE)
[![JOSS article status](https://joss.theoj.org/papers/e5b5dc8cea19605a1507dd4d420d5199/status.svg)](https://joss.theoj.org/papers/e5b5dc8cea19605a1507dd4d420d5199)
[![Coverage Status](https://coveralls.io/repos/github/idaholab/MontePy/badge.svg?branch=develop)](https://coveralls.io/github/idaholab/MontePy?branch=develop)
[![PyPI version](https://badge.fury.io/py/montepy.svg)](https://badge.fury.io/py/montepy)
[![Project Status: Active – The project has reached a stable, usable state and is being actively developed.](https://www.repostatus.org/badges/latest/active.svg)](https://www.repostatus.org/#active)

MontePy is the most user friendly Python library for reading, editing, and writing MCNP input files. 

## Installing

Simply run:

```
pip install montepy
```

For more complicated setups
see the [Installing section in the user guide](https://www.montepy.org/starting.html#installing).


## User Documentation

MontePy has a website [documenting how to work with MCNP in python with MontePy](https://www.montepy.org/). 
The website contains a user's guide for getting started, 
a developer's guide covering the design and approach of MontePy,
instructions for contributing, 
and the Python API documentation.

## Features
	
* Handles almost all MCNP input syntax.
* Parses Cells, Surfaces, Materials, and Transforms very well.	
* Can parse all surface types except macrobody facets ([Issue #354](https://github.com/idaholab/MontePy/issues/354)).
* Can read and write out all other MCNP inputs, even if it doesn't not understand them	
* Attempts to write out the MCNP problem verbatim, even matching the original user formatting. (See [Issues](https://github.com/idaholab/MontePy/issues).)
* Can quickly [access cells, surfaces, and materials by their numbers](https://www.montepy.org/starting.html#collections-are-accessible-by-number). For example: `cell = problem.cells[105]`.
* Can quickly update cell parameters, [such as importances](https://www.montepy.org/starting.html#setting-cell-importances). For example `cell.importance.neutron = 2.0`.
* Can easily [create universes, and fill other cells with universes](https://www.montepy.org/starting.html#universes).
* Currently has over 430 test cases.

 
Quick example for renumbering all of the cells in a problem:

```python
import montepy
foo = montepy.read_input("foo.imcnp")
i = 9500
for cell in foo.cells:
  cell.number = i
  i = i + 5
  
foo.write_problem("foo_update.imcnp")

```

## Limitations

Here a few of the known bugs and limitations:

	
* Cannot handle vertical input mode.
* Does not support editing tallies in an easy way.
* Does not support editing source definition in an easy way.
	
## Bugs, Requests and Development

So MontePy doesn't do what you want? 
Add an issue here with the "feature request" tag. 
If you want to add a feature on your own talk to Micah Gale (but still add the issue). 
The system is very modular and you should be able to develop it pretty quickly.
Also read the [developer's guide](https://www.montepy.org/developing.html).

 
# Finally: make objects, not regexes!

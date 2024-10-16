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
* Attempts to write out the MCNP problem verbatim, even matching the original user formatting. (See some of the [open issues](https://github.com/idaholab/MontePy/issues).)
* Can quickly [access cells, surfaces, and materials by their numbers](https://www.montepy.org/starting.html#collections-are-accessible-by-number). For example: `cell = problem.cells[105]`.
* Can quickly update cell parameters, [such as importances](https://www.montepy.org/starting.html#setting-cell-importances). For example `cell.importance.neutron = 2.0`.
* Can easily [create universes, and fill other cells with universes](https://www.montepy.org/starting.html#universes).
* Currently has over 430 test cases.

 
Here is a quick example showing multiple tasks in MontePy:

```python
import montepy
# read in file
problem = montepy.read_input("foo.imcnp")
  
# set photon importance for multiple cells
importances = {1: 0.005,
    2: 0.1,
    3: 1.0,
    99: 1.235
}
for cell_num, importance in importances.items():
    problem.cells[cell_num].importance.photon = importance

#create a universe and fill another cell with it
universe = montepy.Universe(123)
problem.univeres.append(universe)
# add all cells with numbers between 1 and 4
universe.claim(problem.cells[1:5])
# fill cell 99 with universe 123
problem.cells[99].fill.universe = universe

# update all surfaces numbers by adding 1000 to them
for surface in problem.surfaces:
    surface.number += 1000
# all cells using these surfaces will be automatically updated as well

#write out an updated file
problem.write_problem("foo_update.imcnp")

```

## Limitations

Here a few of the known bugs and limitations:

	
* Cannot handle vertical input mode.
* Does not support editing tallies in a user-friendly way.
* Does not support editing source definition in a user-friendly way.
* Cannot parse all valid material definitions. There is a known bug ([#182](https://github.com/idaholab/MontePy/issues/182)) that MontePy can only parse materials where all
    keyword-value pairs show up after the nuclide definitions. For example:
   * `M1 1001.80c 1.0 plib=80p` can be parsed.
   * `M1 plib=80p 1001.80c 1.0` cannot be parsed; despite it being a valid input.
	
## Bugs, Requests and Development

So MontePy doesn't do what you want? 
Add an issue here with the "feature request" tag. 
The system is very modular and you should be able to develop it pretty quickly.
Read the [developer's guide](https://www.montepy.org/developing.html) for more details.
If you have any questions feel free to ask [@micahgale](mailto:mgale@montepy.org).

 
# Finally: make objects, not regexes!

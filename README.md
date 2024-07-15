# MontePy

<img src="https://raw.githubusercontent.com/idaholab/MontePy/develop/graphics/monty.svg" width="180" alt="MontePY: a cute snek on a red over white circle"/>

[![license](https://img.shields.io/github/license/idaholab/MontePy.svg)](https://github.com/idaholab/MontePy/blob/develop/LICENSE)
[![JOSS article status](https://joss.theoj.org/papers/e5b5dc8cea19605a1507dd4d420d5199/status.svg)](https://joss.theoj.org/papers/e5b5dc8cea19605a1507dd4d420d5199)
[![Coverage Status](https://coveralls.io/repos/github/idaholab/MontePy/badge.svg?branch=develop)](https://coveralls.io/github/idaholab/MontePy?branch=develop)
[![PyPI version](https://badge.fury.io/py/montepy.svg)](https://badge.fury.io/py/montepy)

MontePy is a python library to read, edit, and write MCNP input files. 

## Installing

Simply run:

```
pip install montepy
```

For more complicated setups
see the [Installing section in the user guide](https://www.montepy.org/starting.html#installing).


## User Documentation

MontePy has a [sphinx website](https://www.montepy.org/). 
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
Also read the [developer's guide](https://www.montepy.org/developing.html).

 
# Finally: make objects not regexes!

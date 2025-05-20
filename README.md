# MontePy

<img src="https://raw.githubusercontent.com/idaholab/MontePy/develop/graphics/monty.svg" width="180" alt="MontePY: a cute snek on a red over white circle"/>

[![license](https://img.shields.io/github/license/idaholab/MontePy.svg)](https://github.com/idaholab/MontePy/blob/develop/LICENSE)
[![JOSS article status](https://joss.theoj.org/papers/e5b5dc8cea19605a1507dd4d420d5199/status.svg)](https://joss.theoj.org/papers/e5b5dc8cea19605a1507dd4d420d5199)
[![pyOpenSci Peer-Reviewed](https://pyopensci.org/badges/peer-reviewed.svg)](https://github.com/pyOpenSci/software-review/issues/205)
[![Project Status: Active – The project has reached a stable, usable state and is being actively developed.](https://www.repostatus.org/badges/latest/active.svg)](https://www.repostatus.org/#active)


[![Coverage Status](https://coveralls.io/repos/github/idaholab/MontePy/badge.svg?branch=develop)](https://coveralls.io/github/idaholab/MontePy?branch=develop)
[![Testing status](https://github.com/idaholab/MontePy/actions/workflows/main.yml/badge.svg?branch=develop)](https://github.com/idaholab/MontePy/actions/workflows/main.yml?query=branch%3Adevelop)
[![Docs Deployment](https://github.com/idaholab/MontePy/actions/workflows/deploy.yml/badge.svg?branch=main)](https://www.montepy.org/)

[![PyPI version](https://badge.fury.io/py/montepy.svg)](https://badge.fury.io/py/montepy)
[![Conda Version](https://img.shields.io/conda/vn/conda-forge/montepy.svg)](https://anaconda.org/conda-forge/montepy)
[![PyPI pyversions](https://img.shields.io/pypi/pyversions/montepy.svg)](https://pypi.org/project/montepy/)

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.15185506.svg)](https://doi.org/10.5281/zenodo.15185506)

MontePy is the most user-friendly Python library for reading, editing, and writing MCNP input files. 

## Installing

Simply run:

```
pip install montepy
```

For more complicated setups
see the [Installing section in the user guide](https://www.montepy.org/en/stable/starting.html#installing).


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
* Can read and write out all other MCNP inputs, even if it does not understand them	.
* Attempts to write out the MCNP problem verbatim, even matching the original user formatting. (See some of the [open issues](https://github.com/idaholab/MontePy/issues).)
* Can quickly [access cells, surfaces, and materials by their numbers](https://www.montepy.org/en/stable/starting.html#collections-are-accessible-by-number). For example: `cell = problem.cells[105]`.
* Can quickly update cell parameters, [such as importances](https://www.montepy.org/en/stable/starting.html#setting-cell-importances). For example `cell.importance.neutron = 2.0`.
* Can easily [create universes, and fill other cells with universes](https://www.montepy.org/en/stable/starting.html#universes).
* Currently has over 800 test cases.

 
Here is a quick example showing multiple tasks in MontePy:


```python
import montepy
# read in file
problem = montepy.read_input("tests/inputs/test.imcnp")
  
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
problem.universes.append(universe)
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

For more examples see the [getting started guide](https://www.montepy.org/en/stable/starting.html).

## Limitations

Here a few of the known bugs and limitations:

	
* Cannot handle vertical input mode.
* Does not support editing tallies in a user-friendly way.
* Does not support editing source definition in a user-friendly way.
* Cannot parse all valid material definitions. There is a known bug ([#182](https://github.com/idaholab/MontePy/issues/182)) that MontePy can only parse materials where all
    keyword-value pairs show up after the nuclide definitions. For example:
   * `M1 1001.80c 1.0 plib=80p` can be parsed.
   * `M1 plib=80p 1001.80c 1.0` cannot be parsed; despite it being a valid input.

## Current Development Priorities

Here are the rough development priorities for adding new features to MontePy:

1. Improve performance for the intial loading of models.
2. Implement support for tallies.
1. Implement support for source definitions.

If you have a specific feature priority that you would be willing to collaborate on you can open an issue or email us at [mgale@montepy.org](mailto:mgale@montepy.org). 

## Alternatives

There are some python packages that offer some of the same features as MontePy,
    but don't offer the same level of robustness, ease of installation, and user friendliness.


Many of the competitors do not offer the robustness that MontePy does because,
    they do not utilize context-free parsing (as of 2024). 
These packages are:

* [pyMCNP](https://github.com/FSIBT/PyMCNP)

* [MCNP-Input-Reader](https://github.com/ENEA-Fusion-Neutronics/MCNP-Input-Reader)

* [numjuggler](https://github.com/inr-kit/numjuggler)

The only other libraries that do utilize context-free parsing that we are aware of are:
* [MCNPy](https://github.rpi.edu/NuCoMP/mcnpy)
* [mckit](https://github.com/MC-kit/mckit) 

MontePy differs from MCNPy by being:

* On PyPI and conda-forge, and able to be installed via `pip` or `conda`
* Only requiring a Python interpreter and not a Java virtual machine
* Allowing contributions from anyone with a public GitHub account

MontePy differs from mckit by being:
* Thoroughly documented
* Object-oriented 


For only writing, or templating an input file there are also some great tools out there. 
These packages don't provide the same functionality as MontePy inherently,
    but could be the right tool for the job depending on the user's needs.

* [Workflow and Template Toolkit for Simulation (WATTS)](https://github.com/watts-dev/watts)
* [Advanced Reactor Modeling Interface (ARMI)](https://github.com/terrapower/armi)

Another honorable mention that doesn't replicate the features of MontePy,
    but could be a great supplement to MontePy for defining materials, performing activations, etc.
    is [PyNE --- the Nuclear Engineering Toolkit](https://pyne.io/).
	
## Bugs, Requests and Development

So MontePy doesn't do what you want? 
Add an issue here with the "feature request" tag. 
The system is very modular and you should be able to develop it pretty quickly.
Read the [developer's guide](https://www.montepy.org/en/stable/developing.html) for more details.
If you have any questions feel free to ask [@micahgale](mailto:mgale@montepy.org).

## Citation

You can cite MontePy as:

> Gale et al., (2025). MontePy: a Python library for reading, editing, and writing MCNP input files. Journal of Open Source Software, 10(108), 7951, [https://doi.org/10.21105/joss.07951](https://doi.org/10.21105/joss.07951)

 
# Finally: make objects, not regexes!

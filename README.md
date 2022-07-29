# MCNPy

A python library to read, edit, and write MCNP input files. 

## Installing

Go to the packages page and download a wheel or a tar ball. Run `pip install --user mcnpy.XXXXXX.tar.gz`

## User Documentation

MCNPy has a [sphinx website](https://experiment_analysis.pages.hpc.inl.gov/mcnpy). 
This has a getting started guide for users,
as well as API documentation. 
There is also a developer's guide covering the design and approach of MCNPy, and how to contribute.

## Features
	
* Handles almost all MCNP input syntax including: message blocks, & continue, comments, etc.
* Parses Cells, surfaces, materials, and transforms very well.	
* Can parse the following surfaces exactly P(X|Y|Z), C(X|Y|Z), C/(X|Y|Z) (I mean it can do PX, and PY, etc.)
* Can read in all other cards but not understand them	
* Can write out full MCNP problem even if it doesn't fully understand a card.	
* Can write out the MCNP problem verbatim, if it has not been modified at all.
* Can quickly access cells, surfaces, and materials by their numbers. For example: `cell = problem.cells[105]`.
* Has 127 test cases right now 

 
Quick example for renumbering all of the cells in a problem:

```python
import mcnpy
foo = mcnpy.read_input("foo.imcnp")
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

So MCNPy doesn't do what you want? Right now development is done with a  Just-In-Time development approach, as in features are added JIT for a developer to use them on my current projects. 
If there's a feature you want add an issue here with the feature request tag. 
If you want to add a feature on your own talk to Micah Gale (but still add the issue). 
The system is very modular and you should be able to develop it pretty quickly.
Also read the [developer's guide](https://experiment_analysis.pages.hpc.inl.gov/mcnpy/developing.html).

# Version Numbering Scheme

First, versions are only official once they are on the main branch, have a release tag assigned,
and distribution packages have been created.
Once these are completed there is a guarantee that this release will not change without a version number increment.
While on develop and other branches these guarantees do not exist.
These versions will generally be designated as `dev` e.g., `0.1.0.dev2`,
and may change as features and bug fixes are implemented.


 
Finally: make objects not regexs!

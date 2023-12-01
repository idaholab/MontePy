---
title: 'MontePy: a python library for reading, editing, and writing MCNP input files.'
tags:
  - Python
  - nuclear engineering
  - monte carlo methods
  - particle transport
  - Monte Carlo N-Particle (MCNP)
authors :
  - name: Micah D. Gale
    orcid: 0000-0001-6451-4818
    affiliation: 1
  - name: Travis J. Labossiere-Hickman
    orcid: 0000-0003-0742-3404
    affiliation: 1
  - name: Brenna A. Carbno
    affiliation: 1
  - name: Andrew J. Bascom
    affiliation: 1
affiliations:
  - name: Idaho National Laboratory, USA
    index: 1
date: 1 February 2024
bibliography: paper.bib

# Summary
The Monte Carlo N-Particle (MCNP) radiation transport code,
is a highly capable and accurate code with a long legacy.
Unfortunately, part of that legacy is having a history that predates many modern
software conventions.
MCNP operates by being provided an input file by the user,
creating an internal representation of the problem,
and then starting Monte Carlo radiation transport on that problem.
MCNP predates most all modern human readable markup languages,
such as the extensible markup language (XML),
yet another markup language (YAML),
and javascript object notation (JSON).
Due to this MCNP uses an entirely custom defined syntax language for its input,
making off the shelf libraries for XML, YAML, and JSON impossible to use for scripting
various operations on MCNP input files.

# Statement of need

# References

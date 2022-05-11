# MCNPy

A python library to parse and modify MCNP input files. 

## Installing

Go to the packages page and download a wheel or a tar ball. Run `pip install --user mcnpy.XXXXXX.tar.gz`
 

## Features
	
* Handles almost all MCNP input syntax including: message blocks, & continue, comments, etc.
* Parses Cells, surfaces, materials, and transforms very well.	
* Can parse the following surfaces exactly P(X|Y|Z), C(X|Y|Z), C/(X|Y|Z) (I mean it can do PX, and PY, etc.)
* Can read in all other cards but not understand them	
* Can write out full MCNP problem even if it doesn't fully understand a card.	
* Has 110 test cases right now 

 
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
	
## Bugs, Requests and Development

So MCNPy doesn't do what you want? Reasonable; I started writing it in November so it's pretty young. Right now I'm doing what I call Just-In-Time development, as in features are added JIT for me to use them on my current projects. If there's a feature you want add an issue on gitlab with the feature request tag. If you want to add a feature on your own talk to me (but still add the issue). The system is very modular and you should be able to develop it pretty quickly, just guides on how to do this are a bit lacking.
 

 
Finally: make objects not regexs!

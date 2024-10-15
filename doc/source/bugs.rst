**************************
Known Bugs and limitations
**************************

This page is not meant to document every MCNP feature that is not supported.
For seeing if a specific feature is supported refer to the API documentation 
that exists for :mod:`~montepy.data_inputs`, :mod:`~montepy.surfaces`,
to see if an object exists for the feature you want.

This is meant for documenting limitations that are less obvious,
and how to work-around them.

Material Definitions Can't be Read Sometimes
============================================

As detailed in :issue:`182` there are some valid MCNP material definitions,
that MontePy can't read.
MontePy expects all key-value data (e.g., ``nlib=80c`` ) to be after all 
isotope definitions. 

So MontePy can read:

* ``m1 1001.80c 1.0``
* ``m1 1001 1.0 nlib=80c``

But MontePy can't read:

* ``m1 plib=80c 1001 1.0``.

 
Recognizing the Error
---------------------

If MontePy encounters a material definition that it can't handled the error message
will look like::

        File ~/mambaforge/lib/python3.12/site-packages/montepy/data_inputs/material.py:32, in Material.__init__(self, input)
             30 self._thermal_scattering = None
             31 self._number = self._generate_default_node(int, -1)
        ---> 32 super().__init__(input)
             33 if input:
             34     num = self._input_number

        File ~/mambaforge/lib/python3.12/site-packages/montepy/data_inputs/data_input.py:58, in DataInputAbstract.__init__(self, input, fast_parse)
             56 self._particles = None
             57 if not fast_parse:
        ---> 58     super().__init__(input, self._parser)
             59     if input:
             60         self.__split_name(input)

        File ~/mambaforge/lib/python3.12/site-packages/montepy/mcnp_object.py:59, in MCNP_Object.__init__(self, input, parser)
             55     raise MalformedInputError(
             56         input, f"Error parsing object of type: {type(self)}: {e.args[0]}"
             57     )
             58 if self._tree is None:
        ---> 59     raise ParsingError(
             60         input,
             61         "",
             62         parser.log.clear_queue(),
             63     )
             64 if "parameters" in self._tree:
             65     self._parameters = self._tree["parameters"]

        ParsingError:     , line 0

            >    0| M1 plib=80p 1001.80c 1.0
                  |        ^ not expected here.
        There was an error parsing "=".
        sly: Syntax error at line 1, token==


Workaround
----------

For the time being this can be fixed by manually editing all offending material
definitions and moving all key-value pairs to the end of the input.

Long Term Fix
-------------

Work is currently planned to fix this in release 1.0.0,
which will improve many aspects of the material interface.
For more details see: :ref:`migrate 0 1`. 

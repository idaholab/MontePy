.. meta::
   :description lang=en:
        Tips and tricks for improving the parsing performance for MontePy

.. _performance:

Improving MontePy Performance
=============================

For large models MontePy's unoptimized parser can make the initial load for a large MCNP input file slow.
Currently the only strategy to address this is with multi-processing. 


Multi-Processing
----------------

MontePy does support multi-processing in order to use all of the available CPU cores.
However, there are some caveats with multi-processing so it is not the default option.
To enable this feature set ``multi_proc=True`` when calling :func:`~montepy.input_parser.input_reader.read_input`.
The number of processes can be controlled with ``num_processes``. 
If ``None`` is given the number of processors on the system will be used.

.. Warning::

   If using multi-processing on Windows there are extra steps that are necessary.
   See :ref:`windows_warning` for more details.


Limitations
+++++++++++

Multi-processing is not a silver bullet, and it does not make MontePy anymore Computationally efficient. 
The parsing process is not perfectly scalable, does have a few serial bottlenecks, and does have some overhead.
This is to say: don't expect perfect scaling with more cores.

Beyond that caveat, the limitations of multi-processing are:

#. Checking models for errors (:ref:`check_opt`) with multi-processing is not allowed.
#. Scripts using multi-processing in Windows needs to be wrapped in a specific way.  

.. _windows_warning:

How to use multi-processing with Windows
++++++++++++++++++++++++++++++++++++++++

On Windows Python has to use the spawn method for multi-processing. 
`As covered in the Python documentation <https://docs.python.org/3/library/multiprocessing.html#windows>`_,
your script or module that calls MontePy needs to be "import safe", i.e., have a main-guard.

For instance the following script ran on Windows would raise a ``RuntimeError``. 

.. code-block:: python

   import montepy

   problem = montepy.read_input("foo.imcnp", multi_proc=True)


Instead the entry point should be protected with a ``if __name__ == "__main__":`` clause:

.. code-block:: python

   import montepy
   
   if __name__ == "__main__":
        problem = montepy.read_input("foo.imcnp", multi_proc=True)



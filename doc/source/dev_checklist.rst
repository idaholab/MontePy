Developer's Guide to Common Tasks
=================================

Setting up and Typical Development Workflow
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

#. Clone the repository.

#. Install the required packages. 
   MontePy comes with the requirements specfied in ``pyproject.toml``.
   Optional packages are also specified.
   To install all packages needed for development simply run: 
   
   ``pip install .[develop]``

#. Tie your work to an issue. All work on MontePy is tracked through issues. 
   If you are working on a new feature or bug that is not covered by an issue, please file an issue first.

#. Work on a new branch. The branches: ``develop`` and ``main`` are protected. 
   All new code must be accepted through a merge request or pull request. 
   The easiest way to make this branch is to "create pull request" from github.
   This will create a new branch (though with an unwieldy name) that you can checkout and work on.

#. Run the test cases. MontePy relies heavily on its over 380 tests for the development process.
   These are configured so if you run: ``pytest`` from the root of the git repository 
   all tests will be found and ran.

#. Develop test cases. This is especially important if you are working on a bug fix.
   A merge request will not be accepted until it can be shown that a test case can replicate the 
   bug and does in deed fail without the bug fix in place.
   To achieve this, it is recommended that you commit the test first, and push it to gitlab.
   This way there will be a record of the CI pipeline failing that can be quickly reviewed as part of the merge request.

   MontePy is currently working on migrating from ``unittest`` to ``pytest`` for test fixtures.
   All new tests should use a ``pytest`` architecture.
   Generally unit tests of new features go in the test file with the closest class name. 
   Integration tests have all been dumped in ``tests/test_integration.py``. 
   For integration tests you can likely use the ``tests/inputs/test.imcnp`` input file.
   This is pre-loaded as an :class:`~montepy.mcnp_problem.MCNP_Problem` stored as: ``self.simple_problem``.
   If you need to mutate it at all you must first make a ``copy.deepcopy`` of it.

#. Write the code.

#. Document all new classes and functions. MontePy uses `Sphinx docstrings <https://sphinx-rtd-tutorial.readthedocs.io/en/latest/docstrings.html>`_.

#. Format the code with ``black``. You can simply run ``black montepy tests``

#. Add more test cases as necessary. The merge request should show you the code coverage.
   The general goal is near 100\% coverage.

#. Update the documentation. Read the "Getting Started" guide and the "Developer's Guide", and see if any information there should be updated.
   If you expect the feature to be commonly used it should be mentioned in the getting started guide.
   Otherwise just the docstrings may suffice.
   Another option is to write an example in the "Tips and Tricks" guide.

#. Update the authors as necessary. 
   The authors information is in ``AUTHORS`` and ``pyproject.toml``. 

#. Start a merge request review. Generally Micah (@micahgale) or Travis (@tjlaboss) are good reviewers.


Deploy Process
^^^^^^^^^^^^^^
MontePy currently does not use a continuous deploy (CD) process.
Changes are staged on the ``develop`` branch prior to a release.
Both ``develop`` and ``main`` are protected branches.
``main`` is only be used for releases.
If someone clones ``main`` they will get the most recent official release.
Only a select few core-developers are allowed to approve a merge to ``main`` and therefore a new release.
``develop`` is for production quality code that has been approved for release,
but is waiting on the next release.
So all new features and bug fixes must first be merged onto ``develop``. 

The expectation is that features once merged onto ``develop`` are stable,
well tested, well documented, and well-formatted.

Merge Checklist
^^^^^^^^^^^^^^^

Here are some common issues to check before approving a merge request.

#. If this is a bug fix did the new testing fail without the fix?
#. Were the authors and credits properly updated?
#. Check also the authors in ``pyproject.toml``
#. Is this merge request tied to an issue?

Deploy Checklist
^^^^^^^^^^^^^^^^

For a deployment you need to:

#. Run the deploy script : ``.github/scripts/deploy.sh``
#. Manually merge onto main without creating a new commit. 
   This is necessary because there's no way to do a github PR that will not create a new commit, which will break setuptools_scm.
#. Update the release notes on the draft release, and finalize it on GitHub.
#. Update the `Conda feedstock and deploy <https://github.com/conda-forge/montepy-feedstock>`_ if it doesn't happen
   automatically.
#. Upload the release archive to `Zenodo <https://doi.org/10.5281/zenodo.15185600>`_.

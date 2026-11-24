.. meta::
   :description lang=en:
        Best practices for scripting with MontePy: version control, backups, and safe file handling.

Best Practices
==============

Before we begin, here are some guidelines to keep in mind while scripting your work with MCNP models.

#. *Always* version control your input files (not output files) with `git <https://git-scm.com/>`_ or another tool.
   If you are working with very large input models, like `the ITER model <https://doi.org/10.1038/s41560-020-00753-x>`_ you may want to consider `git-lfs <https://git-lfs.com/>`_.

   #. Do learn some `git best practices <https://sethrobertson.github.io/GitBestPractices/>`_. "Update" is not a useful commit message.

#. *Always* have backups. Don't be that person that loses the last months of work when your laptop falls in a pond.
   Make sure there's a cloud backup (could be OneDrive, GitHub, etc.).
   Just make sure you comply with any applicable corporate policies.

#. Don't overwrite your original file. Generally your script should open file "A", modify it, and then save it to file "B".
   This way, when there is a bug in your script, you can debug it and rerun it because "A" still exists.
   Later, if you need to make changes you can modify your script and rerun it.
   This is especially true if your script ever becomes qualified under an `ASME NQA-1 <https://en.wikipedia.org/wiki/ASME_NQA>`_ compliant Software Quality Assurance program,
   which requires that the inputs and outputs of software be preserved.

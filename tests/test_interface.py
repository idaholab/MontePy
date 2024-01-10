# Copyright 2024, Battelle Energy Alliance, LLC All Rights Reserved.
import io
import glob
import montepy
import os
import unittest
from tests import constants

import pickle

"""
This is for testing MontePy's interface with other libraries,
which are not dependencies.

This doesn't mean these interfaces are supported, but is meant to reduce user frustration
when using common workflows.
"""


class TestBrinyFermentation(unittest.TestCase):
    def test_pickling_all_models(self):
        for file in glob.glob(os.path.join("tests", "inputs", "*.imcnp")):
            if (
                os.path.basename(file) not in constants.BAD_INPUTS
                and os.path.basename(file) not in constants.IGNORE_FILES
            ):
                print(file)
                problem = montepy.read_input(file)
                with io.BytesIO() as fh:
                    pickle.dump(problem, fh)
                    fh.seek(0)
                    new_problem = pickle.load(fh)
                data = pickle.dumps(problem)
                new_problem = pickle.loads(data)

# Copyright 2024, Battelle Energy Alliance, LLC All Rights Reserved.

import io
import glob
import montepy
import os
import pytest
from tests import constants
import pickle

"""
This is for testing MontePy's interface with other libraries,
which are not dependencies.

This doesn't mean these interfaces are supported, but is meant to reduce user frustration
when using common workflows.
"""


@pytest.mark.parametrize(
    "file",
    [
        f
        for f in glob.glob(os.path.join("tests", "inputs", "*.imcnp"))
        if os.path.basename(f) not in constants.BAD_INPUTS
        and os.path.basename(f) not in constants.IGNORE_FILES
    ],
)
def test_pickling_all_models(file):
    print(file)
    problem = montepy.read_input(file)
    with io.BytesIO() as fh:
        pickle.dump(problem, fh)
        fh.seek(0)
        new_problem = pickle.load(fh)
    data = pickle.dumps(problem)
    new_problem = pickle.loads(data)
    for attr in {"cells", "surfaces", "materials", "data_inputs"}:
        assert len(getattr(problem, attr)) == len(getattr(new_problem, attr))
        for obj in getattr(new_problem, attr):
            assert obj._problem is not None
            assert obj._problem is new_problem

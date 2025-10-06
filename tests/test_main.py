# Copyright 2024, Battelle Energy Alliance, LLC All Rights Reserved.

import glob
import os
import pytest
import montepy
from montepy import __main__ as main
from montepy.exceptions import *
from tests import constants


def test_argument_parsing():
    arguments = ["-c", "foo.imcnp", "bar.imcnp"]
    args = main.define_args(arguments)
    assert len(args.check) == 2
    assert "foo.imcnp" in args.check
    assert "bar.imcnp" in args.check


def test_check_no_error():
    main.check_inputs([os.path.join("tests", "inputs", "test.imcnp")])
    with pytest.raises(FileNotFoundError):
        main.check_inputs(["foo"])


@pytest.mark.parametrize("bad_input", constants.BAD_INPUTS)
def test_check_warning_bad_inputs(bad_input):
    with pytest.warns(Warning):
        print(f"Testing that a warning is issued for: {bad_input}")
        main.check_inputs([os.path.join("tests", "inputs", bad_input)])


@pytest.mark.parametrize(
    "file",
    [
        f
        for f in glob.glob(os.path.join("tests", "inputs", "*.imcnp"))
        if os.path.basename(f) not in constants.BAD_INPUTS
        and os.path.basename(f) not in constants.IGNORE_FILES
    ],
)
def test_check_warning_good_inputs(file):
    print(f"Testing no errors are raised for file: {file}")
    montepy.read_input(file)

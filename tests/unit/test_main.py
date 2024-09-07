# Copyright 2024, Battelle Energy Alliance, LLC All Rights Reserved.
import glob
import montepy
from montepy import __main__ as main
from montepy.errors import *
from unittest import TestCase
from tests import constants
import os


class TestMainRunner(TestCase):
    def test_argument_parsing(self):
        arguments = ["-c", "foo.imcnp", "bar.imcnp"]
        args = main.define_args(arguments)
        self.assertEqual(len(args.check), 2)
        self.assertIn("foo.imcnp", args.check)
        self.assertIn("bar.imcnp", args.check)

    def test_check_no_error(self):
        main.check_inputs([os.path.join("tests", "inputs", "test.imcnp")])
        with self.assertRaises(FileNotFoundError):
            main.check_inputs(["foo"])

    def test_check_warning(self):
        for bad_input in constants.BAD_INPUTS:
            with self.assertWarns(Warning):
                print(f"Testing that a warning is issued for: {bad_input}")
                main.check_inputs([os.path.join("tests", "inputs", bad_input)])
        for file in glob.glob(os.path.join("tests", "inputs", "*.imcnp")):
            if (
                os.path.basename(file) not in constants.BAD_INPUTS
                and os.path.basename(file) not in constants.IGNORE_FILES
            ):
                print(f"Testing no errors are raised for file: {file}")
                montepy.read_input(file)

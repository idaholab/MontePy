import glob
import mcnpy
from mcnpy import __main__ as main
from mcnpy.errors import *
from unittest import TestCase
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
        bad_inputs = {
            "test_excess_mt.imcnp",
            "test_vol_redundant.imcnp",
            "testVerticalMode.imcnp",
            "test_missing_mat_for_mt.imcnp",
            "test_imp_redundant.imcnp",
            "test_broken_cell_surf_link.imcnp",
            "test_broken_surf_link.imcnp",
            "test_broken_transform_link.imcnp",
            "test_broken_mat_link.imcnp",
            "test_broken_complement.imcnp",
            "testVerticalMode.imcnp",
        }
        for bad_input in bad_inputs:
            with self.assertWarns(Warning):
                print(f"Testing that a warning is issued for: {bad_input}")
                main.check_inputs([os.path.join("tests", "inputs", bad_input)])
        for file in glob.glob(os.path.join("tests", "inputs", "*.imcnp")):
            if os.path.basename(file) not in bad_inputs:
                print(f"Testing no errors are raised for file: {file}")
                mcnpy.read_input(file)

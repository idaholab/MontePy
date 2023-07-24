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

    def test_check_warning(self):
        with self.assertWarns(Warning):
            main.check_inputs([os.path.join("tests", "inputs", "test_excess_mt.imcnp")])

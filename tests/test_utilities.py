# Copyright 2024, Battelle Energy Alliance, LLC All Rights Reserved.
from unittest import TestCase

from montepy.utilities import fortran_float


class testFortranFloat(TestCase):
    def test_normal_float_parse(self):
        tests = {"123": 123, "1.23": 1.23, "1.2e+3": 1.2e3, "1.2e-3": 1.2e-3}
        for test_string in tests:
            self.assertAlmostEqual(fortran_float(test_string), tests[test_string])

    def test_stupid_float_parse(self):
        tests = {"1.2+3": 1.2e3, "1.2-3": 1.2e-3, "-2-3": -2.0e-3}
        for test_string in tests:
            self.assertAlmostEqual(fortran_float(test_string), tests[test_string])

    def test_raise_error(self):
        with self.assertRaises(ValueError):
            fortran_float("Dog")

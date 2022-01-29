from unittest import TestCase

import mcnpy


class testFullFileIntegration(TestCase):
    def test_reading_test_file(self):
        file_name = "tests/inputs/test.imcnp"
        problem = mcnpy.read_input(file_name)

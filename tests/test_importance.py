from unittest import TestCase
import mcnpy
import os


class TestImportance(TestCase):
    def test_data_imp_card(self):
        problem = mcnpy.read_input(
            os.path.join("tests", "inputs", "test_importance.imcnp")
        )

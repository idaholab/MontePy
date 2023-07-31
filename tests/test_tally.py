import mcnpy
from mcnpy.data_inputs.data_input import DataInput
from mcnpy.input_parser.block_type import BlockType
from mcnpy.input_parser.mcnp_input import Input


from unittest import TestCase


class TestTallyParser(TestCase):
    def test_parsing_tally_groups(self):
        input = Input(["F4 (1 3i 5)"], BlockType.DATA)
        data = DataInput(input)
        self.assertEqual(data.prefix, "F")

    def test_parsing_tally_print(self):
        input = Input(["Fq4 f p e"], BlockType.DATA)
        data = DataInput(input)
        self.assertEqual(data.prefix, "FQ")

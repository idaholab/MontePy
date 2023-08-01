import mcnpy
from mcnpy.data_inputs.data_parser import parse_data
from mcnpy.input_parser.block_type import BlockType
from mcnpy.input_parser.mcnp_input import Input


from unittest import TestCase


class TestTallyParser(TestCase):
    def test_parsing_tally_groups(self):
        input = Input(["F4:n (1 3i 5) T"], BlockType.DATA)
        data = parse_data(input)
        self.assertEqual(data.prefix, "f")
        input = Input(["F4:n 1 2 3"], BlockType.DATA)
        data = parse_data(input)
        self.assertEqual(data.prefix, "f")
        input = Input(["F4:n (1 3i 5) (7 8 9) T"], BlockType.DATA)
        data = parse_data(input)
        self.assertEqual(data.prefix, "f")
        input = Input(["F4:n (1 3i 5) (7 8 9)"], BlockType.DATA)
        data = parse_data(input)
        self.assertEqual(data.prefix, "f")

    def test_parsing_tally_print(self):
        input = Input(["Fq4 f p e"], BlockType.DATA)
        data = parse_data(input)
        self.assertEqual(data.prefix, "fq")

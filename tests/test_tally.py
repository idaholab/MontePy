import montepy
from montepy.data_inputs.data_parser import parse_data
from montepy.input_parser.block_type import BlockType
from montepy.input_parser.mcnp_input import Input


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
        input = Input(["F7 (1 3i 5) (7 8 9)"], BlockType.DATA)
        data = parse_data(input)
        self.assertEqual(data.prefix, "f")

    def test_parsing_tally_print(self):
        input = Input(["Fq4 f p e"], BlockType.DATA)
        data = parse_data(input)
        self.assertEqual(data.prefix, "fq")

    def test_parsing_tally_multiplier(self):
        test_lines = {
            "fm904   (1.0) (1.0 961 103)",
            "fm3064 (1.0 361001 444) $ 1.0=mult",
        }
        for test in test_lines:
            print(test)
            input = Input([test], BlockType.DATA)
            data = parse_data(input)

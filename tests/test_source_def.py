# Copyright 2024, Battelle Energy Alliance, LLC All Rights Reserved.
from unittest import TestCase

import montepy
from montepy.data_inputs.data_parser import parse_data
from montepy.input_parser.block_type import BlockType


class TestSourceDefinition(TestCase):
    def test_complex_sdef_parser(self):
        lines = ["si1  l   60001 838i 60840", " sp1  d 0.0100 0.01000 0.0100"]
        for test_line in lines:
            print(test_line)
            input = montepy.input_parser.mcnp_input.Input([test_line], BlockType.DATA)
            parse_data(input)

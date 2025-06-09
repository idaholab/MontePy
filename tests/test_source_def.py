# Copyright 2024-2025, Battelle Energy Alliance, LLC All Rights Reserved.
import pytest

import montepy
from montepy.data_inputs.data_parser import parse_data
from montepy.input_parser.block_type import BlockType


@pytest.mark.parametrize(
    "test_line",
    [
        "si1  l   60001 838i 60840",
        " sp1  d 0.0100 0.01000 0.0100",
        "sdef x=d1 Y=d2 Z=d3 erg=d4",
    ],
)
def test_complex_sdef_parser(test_line):
    parse_data(test_line)

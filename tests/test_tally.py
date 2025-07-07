# Copyright 2024-2025, Battelle Energy Alliance, LLC All Rights Reserved.
import pytest

import montepy
from montepy.data_inputs.data_parser import parse_data
from montepy.input_parser.block_type import BlockType
from montepy.input_parser.mcnp_input import Input


class TestTallyParser:
    @pytest.mark.parametrize(
        "line",
        [
            "F4:n (1 3i 5) T",
            "F4:n (1 2 3 4 5) T",
            "F4:n 1 2 3",
            "F4:n (1 3i 5) (7 8 9) T",
            "f4:n (1 3i 5) (7 8 9)",
            "F7 (1 3i 5) (7 8 9)",
            "F7 (1 3i 5) (7 8 9) ",
        ],
    )
    def test_parsing_tally_groups(_, line):
        data = parse_data(line)
        assert data.prefix == "f"

    def test_parsing_tally_print(_):
        input = Input(["Fq4 f p e"], BlockType.DATA)
        data = parse_data(input)
        assert data.prefix == "fq"

    @pytest.mark.parametrize(
        "test",
        [
            "fm904   (1.0) (1.0 961 103)",
            "fm3064 (1.0 361001 444) $ 1.0=mult",
        ],
    )
    def test_parsing_tally_multiplier(_, test):
        test_lines = {
            "fm904   (1.0) (1.0 961 103)",
            "fm3064 (1.0 361001 444) $ 1.0=mult",
        }
        for test in test_lines:
            print(test)
            input = Input([test], BlockType.DATA)
            data = parse_data(input)

    @pytest.mark.parametrize(
        "line",
        [
            "fs14 -123",
            "fs12 -456 t",
            "fs11 -1 -2",
            "fs16 +1 +2 c",
            "fs17 -1 -2 t c",
        ],
    )
    def test_tally_segment_init(_, line):
        input = Input([line], BlockType.DATA)
        data = parse_data(input)

    @pytest.mark.parametrize("line", ["de4 log 1 2 3 4"])
    def test_de_parsing_jail(_, line):
        data = parse_data(line)
        assert data.mcnp_str() == line
        with pytest.raises(montepy.exceptions.UnsupportedFeature):
            data.data

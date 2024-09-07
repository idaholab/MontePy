import montepy
from montepy.data_inputs.data_parser import parse_data
from montepy.input_parser.block_type import BlockType
from montepy.input_parser.mcnp_input import Input

import pytest


@pytest.mark.parametrize(
    "line", ["sdef  cel=d1 erg=d2 pos=fcel d3 ext=fcel d4 axs=0 0 1 rad=d5"]
)
def test_source_parse_and_parrot(line):
    input = Input([line], BlockType.DATA)
    data = parse_data(input)
    print(repr(data._tree))
    assert data._tree.format() == line

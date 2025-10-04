
# Copyright 2024, Battelle Energy Alliance, LLC All Rights Reserved.
import pytest

import montepy

from montepy._cell_data_control import CellDataPrintController
from montepy.data_inputs.data_input import DataInput
from montepy.data_inputs import material, thermal_scattering, transform, volume
from montepy.data_inputs.data_parser import parse_data
from montepy.exceptions import *
from montepy.input_parser.mcnp_input import Input, Jump
from montepy.input_parser import syntax_node
from montepy.input_parser.block_type import BlockType
from montepy.mcnp_problem import MCNP_Problem


def test_data_card_init():
    in_str = "imp:n 1 1 1 0"
    input_card = Input([in_str], BlockType.DATA)
    data_card = DataInput(input_card)
    words = in_str.split()[1:]
    for i, word in enumerate(data_card.data):
        assert word.value == float(words[i])
    # TODO test comments
    # assert comment == data_card.comments[0]

def test_data_card_empty_constructor():
    card = DataInput()

def test_data_card_str():
    in_str = "vol 1 1 0"
    data = DataInput(in_str)
    assert str(data) == "DATA INPUT: vol "

def test_data_card_format_mcnp():
    in_strs = ["c foo", "c bar", "m1 1001.80c 1.0 $ bar"]
    data = DataInput("\n".join(in_strs))
    output = data.format_for_mcnp_input((6, 2, 0))
    print(output)
    assert len(output) == len(in_strs)
    for answer, out in zip(in_strs, output):
        assert answer == out

def test_comment_setter():
    in_str = "m1 1001.80c 1.0"
    comment = syntax_node.CommentNode("foo")
    data = DataInput(in_str)
    data.leading_comments = [comment]
    assert comment == data.comments[0]


import itertools

identifiers = {
    "m235": material.Material,
    "mt235": thermal_scattering.ThermalScatteringLaw,
    "tr601": transform.Transform,
    "ksrc": DataInput,
}
in_strs = {
    "m235": "m235 1001.80c 1.0",
    "mt235": "mt235 grph.29t",
    "tr601": "tr601 0.0 0.0 10.",
    "ksrc": "ksrc 1.0 0.0 0.0",
}

@pytest.mark.parametrize(
    "identifier, ident_case, w, expected_type",
    [
        (identifier, ident_case, in_strs[identifier], identifiers[identifier])
        for identifier, ident_case in itertools.product(in_strs.keys(), [lambda x: x, lambda x: x.upper()])
        for ident_case in [ident_case(identifier)]
    ]
)
def test_data_parser(identifier, ident_case, w, expected_type):
    obj = parse_data(w)
    assert isinstance(obj, expected_type)

def test_data_card_mutate_print():
    in_str = "IMP:N 1 1"
    data = DataInput(in_str)
    output = data.format_for_mcnp_input((6, 2, 0))
    assert output == [in_str]

def test_print_in_data_block():
    cell_controller = CellDataPrintController()
    cell_controller["imp"] = True
    cell_controller["Imp"] = True
    assert cell_controller["IMP"]
    with pytest.raises(TypeError):
        cell_controller[5] = True
    with pytest.raises(TypeError):
        cell_controller["imp"] = 5
    with pytest.raises(TypeError):
        cell_controller[5]
    with pytest.raises(KeyError):
        cell_controller["a"] = True
    with pytest.raises(KeyError):
        cell_controller["a"]

def test_volume_init_cell():
    vol = 1.0
    list_node = syntax_node.ListNode("data")
    list_node.append(syntax_node.ValueNode(str(vol), float))
    node = syntax_node.SyntaxNode(
        "volume",
        {
            "classifier": syntax_node.ValueNode("VoL", str),
            "seperator": syntax_node.ValueNode("=", str),
            "data": list_node,
        },
    )
    v = volume.Volume(key="VoL", value=node, in_cell_block=True)
    assert v.volume == vol
    assert v.in_cell_block
    assert v.set_in_cell_block
    assert not v.is_mcnp_calculated
    assert v.set
    v2 = volume.Volume(in_cell_block=True)
    assert v2.is_mcnp_calculated
    with pytest.raises(ValueError):
        list_node = syntax_node.ListNode("data")
        list_node.append(syntax_node.ValueNode("s", str))
        node = syntax_node.SyntaxNode(
            "volume",
            {
                "classifier": syntax_node.ValueNode("VoL", str),
                "seperator": syntax_node.ValueNode("=", str),
                "data": list_node,
            },
        )
        card = volume.Volume(key="VoL", value=node, in_cell_block=True)
    with pytest.raises(ValueError):
        list_node = syntax_node.ListNode("data")
        list_node.append(syntax_node.ValueNode("-1", float))
        node = syntax_node.SyntaxNode(
            "volume",
            {
                "classifier": syntax_node.ValueNode("VoL", str),
                "seperator": syntax_node.ValueNode("=", str),
                "data": list_node,
            },
        )
        card = volume.Volume(key="VoL", value=node, in_cell_block=True)

    # TODO merge manually
    """
    def test_volume_init_data(self):
        in_str = "VOL 1 1 2J 0"
        input_card = Card([in_str], BlockType.DATA)
        vol_card = parse_data(input_card)
        answers = [1.0, 1.0, Jump, Jump, 0.0]
        for i, vol in enumerate(vol_card._volume):
            if isinstance(answers[i], float):
                self.assertAlmostEqual(vol, answers[i])
            else:
                self.assertIsInstance(vol, Jump)
        # test starting jump
        in_str = "VOL 2J 1 0"
        input_card = Card([in_str], BlockType.DATA)
        vol_card = parse_data(input_card)
        answers = [Jump, Jump, 1.0, 0.0]
        for i, vol in enumerate(vol_card._volume):
            if isinstance(answers[i], float):
                self.assertAlmostEqual(vol, answers[i])
            else:
                self.assertIsInstance(vol, Jump)
        # tests starting no
        in_str = "VOL NO 1 1 2J 0"
        input_card = Card([in_str], BlockType.DATA)
        vol_card = parse_data(input_card)
        self.assertTrue(not vol_card.is_mcnp_calculated)
        # invalid number
        in_str = "VOL NO s 1 2J 0"
        input_card = Card([in_str], BlockType.DATA)
        with self.assertRaises(MalformedInputError):
            vol_card = parse_data(input_card)
        # negative volume
        in_str = "VOL NO -1 1 2J 0"
        input_card = Card([in_str], BlockType.DATA)
        with self.assertRaises(MalformedInputError):
            vol_card = parse_data(input_card)
    """

    def test_volume_init_data(self):
        in_str = "VOL 1 1 2J 0"
        input_card = Input([in_str], BlockType.DATA)
        vol_card = parse_data(input_card)
        answers = [1.0, 1.0, None, None, 0.0]
        for i, vol in enumerate(vol_card._volume):
            if isinstance(vol, syntax_node.ValueNode):
                self.assertAlmostEqual(vol.value, answers[i])
            else:
                self.assertIsInstance(vol, Jump)
        in_str = "VOL NO 1 1 2J 0"
        input_card = Input([in_str], BlockType.DATA)
        vol_card = parse_data(input_card)
        self.assertTrue(not vol_card.is_mcnp_calculated)
        # invalid number
        in_str = "VOL NO s 1 2J 0"
        input_card = Input([in_str], BlockType.DATA)
        with self.assertRaises(MalformedInputError):
            vol_card = parse_data(input_card)
        # negative volume
        in_str = "VOL NO -1 1 2J 0"
        input_card = Input([in_str], BlockType.DATA)
        with self.assertRaises(MalformedInputError):
            vol_card = parse_data(input_card)

    def test_volumes_for_only_some_cells(self):
        cells = [
            montepy.Cell(Input([f"{i + 1} 0 -1 u=3"], BlockType.CELL))
            for i in range(10)
        ]
        prob = MCNP_Problem(None)
        prob.cells = cells
        vol_card = Input(["VOL 1 1 2 3 5"], BlockType.DATA)
        vol_data = volume.Volume(vol_card, in_cell_block=False)
        vol_data.link_to_problem(prob)
        vol_data.push_to_cells()
        is_set = [cell.volume_is_set for cell in cells]
        reference = [True] * 5 + [False] * 5
        self.assertListEqual(is_set, reference)

    def test_volume_setter(self):
        vol = 1.0
        list_node = syntax_node.ListNode("data")
        list_node.append(syntax_node.ValueNode(str(vol), float))
        node = syntax_node.SyntaxNode(
            "volume",
            {
                "classifier": syntax_node.ValueNode("VoL", str),
                "seperator": syntax_node.ValueNode("=", str),
                "data": list_node,
            },
        )
        card = volume.Volume(key="VoL", value=node, in_cell_block=True)
        card.volume = 5.0
        self.assertEqual(card.volume, 5.0)
        with self.assertRaises(TypeError):
            card.volume = "hi"
        with self.assertRaises(ValueError):
            card.volume = -5.0

    def test_volume_deleter(self):
        vol = 1.0
        list_node = syntax_node.ListNode("data")
        list_node.append(syntax_node.ValueNode(str(vol), float))
        node = syntax_node.SyntaxNode(
            "volume",
            {
                "classifier": syntax_node.ValueNode("VoL", str),
                "seperator": syntax_node.ValueNode("=", str),
                "data": list_node,
            },
        )
        card = volume.Volume(key="VoL", value=node, in_cell_block=True)
        del card.volume
        self.assertIsNone(card.volume)

    def test_volume_merge(self):
        vol = 1.0
        list_node = syntax_node.ListNode("data")
        list_node.append(syntax_node.ValueNode(str(vol), float))
        node = syntax_node.SyntaxNode(
            "volume",
            {
                "classifier": syntax_node.ValueNode("VoL", str),
                "seperator": syntax_node.ValueNode("=", str),
                "data": list_node,
            },
        )
        card = volume.Volume(key="VoL", value=node, in_cell_block=True)
        card2 = volume.Volume(key="VoL", value=node, in_cell_block=True)
        with self.assertRaises(MalformedInputError):
            card.merge(card2)

    def test_volume_repr(self):
        vol = 1.0
        list_node = syntax_node.ListNode("data")
        list_node.append(syntax_node.ValueNode(str(vol), float))
        node = syntax_node.SyntaxNode(
            "volume",
            {
                "classifier": syntax_node.ValueNode("VoL", str),
                "seperator": syntax_node.ValueNode("=", str),
                "data": list_node,
            },
        )
        card = volume.Volume(key="VoL", value=node, in_cell_block=True)
        self.assertIn("VOLUME", repr(card))

    def test_data_clone(_):
        problem = montepy.MCNP_Problem("")
        data_input = DataInput("ksrc 0 0 0")
        data_input.link_to_problem(problem)
        new_data = data_input.clone()



def test_classifier_start_comment():
    lines = [
        "c ******************************************************************************",
        "c *******************************Data Cards*************************************",
        "c ******************************************************************************",
        "c",
        "c",
        "c data file=fuel",
        "c ******************** Begin Fuel Data *****************************************",
        "c",
        "c",
        "c fuel",
        "c     material number 2001 total atom density =  ",
        "m2001",
        "      92235.50c     5.0E-01",
    ]
    data = parse_data("\n".join(lines))

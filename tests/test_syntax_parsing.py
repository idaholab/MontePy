# Copyright 2024-2025, Battelle Energy Alliance, LLC All Rights Reserved.
import copy
from io import StringIO
import pytest

import montepy
from montepy.exceptions import *
from montepy.input_parser import input_syntax_reader
from montepy.input_parser.mcnp_input import Input, Jump, Message, ReadInput, Title
from montepy.input_parser.block_type import BlockType
from montepy.input_parser.input_file import MCNP_InputFile
from montepy.input_parser.parser_base import MCNP_Parser
from montepy.input_parser.shortcuts import Shortcuts
from montepy.input_parser import syntax_node
from montepy.particle import Particle
import warnings


lat = montepy.data_inputs.lattice.LatticeType
st = montepy.surfaces.surface_type.SurfaceType


class TestValueNode:
    def test_valuenoode_init(self):
        for type, token, answer in [
            (str, "hi", "hi"),
            (float, "1.2300", 1.23),
            (int, "1", 1),
            (float, "1.23e-3", 1.23e-3),
            (float, "6.02+23", 6.02e23),
        ]:
            for padding in [None, syntax_node.PaddingNode(" ")]:
                node = syntax_node.ValueNode(token, type, padding)
                assert node.value == answer
                assert node.token == token
                if padding:
                    assert node.padding == padding
                else:
                    assert node.padding is None
        # test with None values
        for type in {str, float, int}:
            node = syntax_node.ValueNode(None, type)
            assert None is (node.value)
            node = syntax_node.ValueNode(Jump(), type)
            assert None is (node.value)

    def test_valuenode_convert_to_int(self):
        node = syntax_node.ValueNode("1", float)
        node.convert_to_int()
        assert node.type == int
        assert node.value == 1
        # test 1.0
        node = syntax_node.ValueNode("1.0", float)
        node.convert_to_int()
        assert node.type == int
        assert node.value == 1
        # test wrong type
        with pytest.raises(ValueError):
            node = syntax_node.ValueNode("hi", str)
            node.convert_to_int()
        # test real float
        with pytest.raises(ValueError):
            node = syntax_node.ValueNode("1.23", float)
            node.convert_to_int()

    def test_valuenode_convert_to_enum(self):
        node = syntax_node.ValueNode("1", float)
        lat = montepy.data_inputs.lattice.LatticeType
        node.convert_to_enum(lat)
        assert node.type == lat
        assert node.value == lat(1)
        # test with None
        with pytest.raises(ValueError):
            node = syntax_node.ValueNode(None, float)
            node.convert_to_enum(lat)
        node.convert_to_enum(lat, allow_none=True)
        assert None is (node.value)
        st = montepy.surfaces.surface_type.SurfaceType
        node = syntax_node.ValueNode("p", str)
        node.convert_to_enum(st, switch_to_upper=True)
        assert node.type == st
        assert node.value == st("P")

    def test_is_negat_identifier(self):
        node = syntax_node.ValueNode("-1", float)
        assert not node.is_negatable_identifier
        assert None is (node.is_negative)
        node.is_negatable_identifier = True
        assert node.is_negatable_identifier
        assert node.type == int
        assert node.value > 0
        assert node.is_negative
        # test with positive number
        node = syntax_node.ValueNode("1", float)
        node.is_negatable_identifier = True
        assert node.type == int
        assert node.value > 0
        assert not node.is_negative
        # test with none
        node = syntax_node.ValueNode(None, float)
        node.is_negatable_identifier = True
        assert node.type == int
        assert None is (node.value)
        assert None is (node.is_negative)
        node.value = 1
        assert node.value == 1
        assert not node.is_negative

    def test_is_negat_float(self):
        node = syntax_node.ValueNode("-1.23", float)
        assert not node.is_negatable_float
        assert None is (node.is_negative)
        node.is_negatable_float = True
        assert node.type == float
        assert node.value > 0
        assert node.is_negative
        assert node.is_negatable_float
        # test with positive number
        node = syntax_node.ValueNode("1.23", float)
        node.is_negatable_float = True
        assert node.type == float
        assert not node.is_negative
        # test with None
        node = syntax_node.ValueNode(None, float)
        node.is_negatable_float = True
        assert node.type == float
        assert None is (node.value)
        assert None is (node.is_negative)
        node.value = 1
        assert node.value == 1
        assert not node.is_negative

    def test_is_negative(self):
        node = syntax_node.ValueNode("-1.23", float)
        node.is_negatable_float = True
        assert node.is_negative
        node.is_negative = False
        assert node.value > 0
        assert not node.is_negative
        node = syntax_node.ValueNode("hi", str)
        node.is_negative = True
        assert None is (node.is_negative)

    @pytest.mark.parametrize(
        "token, val, answer, expand",
        [
            ("1", 5, "5", False),
            (1, 5, "5", False),
            ("-1", 2, " 2", False),
            ("-1", -2, "-2", False),
            ("+1", 5, "+5", False),
            ("0001", 5, "0005", False),
            (Jump(), 5, "5 ", False),
        ],
    )
    def test_valuenode_int_format(_, token, val, answer, expand):
        node = syntax_node.ValueNode("-1", int)
        output = node.format()
        assert output == "-1"
        node = syntax_node.ValueNode(token, int)
        node.value = val
        assert node.format() == answer
        node = syntax_node.ValueNode(token, int)
        node.is_negatable_identifier = True
        node.value = val
        node.is_negative = val < 0
        if expand:
            with pytest.warns(LineExpansionWarning):
                assert node.format() == answer
        else:
            assert node.format() == answer

    @pytest.mark.parametrize(
        "padding, val, answer, expand",
        [
            ([" "], 10, "10 ", True),
            (["  "], 10, "10 ", False),
            (["\n"], 10, "10\n", False),
            ([" ", "\n", "c hi"], 10, "10\nc hi", False),
            ([" ", "\n", "c hi"], 100, "100\nc hi", False),
            (["  ", "\n"], 10, "10 \n", False),
        ],
    )
    def test_value_node_format_padding(self, padding, val, answer, expand):
        pad_node = syntax_node.PaddingNode(padding[0])
        for pad in padding[1:]:
            pad_node.append(pad)
        node = syntax_node.ValueNode("1", int, pad_node)
        node.value = val
        if expand:
            warnings.simplefilter("default")
            with pytest.warns(LineExpansionWarning):
                assert node.format() == answer
        else:
            # change warnings to errors to ensure not raised
            warnings.resetwarnings()
            warnings.simplefilter("error")
            assert node.format() == answer

    def test_value_has_changed(self):
        # test None no change
        node = syntax_node.ValueNode(None, int)
        assert not node._value_changed
        # test None changed
        node.value = 5
        assert node._value_changed
        node = syntax_node.ValueNode("1.23", float)
        assert not node._value_changed
        node.value = 1.25
        assert node._value_changed
        node = syntax_node.ValueNode("hi", str)
        assert not node._value_changed
        node.value = "foo"
        assert node._value_changed

    @pytest.mark.parametrize(
        "input, val_type, val, answer, expand",
        [
            ("1.23", float, 1.23, "1.23", False),
            ("1.23", float, 4.56, "4.56", False),
            (1.23, float, 4.56, "4.56", False),
            # test bad rounding
            ("1", float, 1.5, "1.5", True),
            ("1.0", float, 1.05, "1.05", True),
            ("1.0", float, 1.056, "1.056", True),
            ("-1.23", float, 4.56, " 4.56", False),
            ("1.0e-2", float, 2, "2.0e+0", False),
            # bad rounding
            ("1.0e-2", float, 1.01e-3, "1.01e-3", True),
            ("1.602-19", float, 6.02e23, "6.020+23", False),
            ("1.602-0019", float, 6.02e23, "6.020+0023", False),
            (Jump(), float, 5.4, "5.4 ", True),
            ("1", float, 2, "2", False),
            ("0.5", float, 0, "0.0", False),
            ("hi", str, "foo", "foo", True),
            ("hi", str, None, "", False),
        ],
    )
    def test_value_float_format(_, input, val_type, val, answer, expand):
        node = syntax_node.ValueNode(input, val_type)
        node.value = val
        if expand:
            warnings.simplefilter("default")
            with pytest.warns(LineExpansionWarning):
                assert node.format() == answer
        else:
            # change warnings to errors to ensure not raised
            warnings.resetwarnings()
            warnings.simplefilter("error")
            assert node.format() == answer

    @pytest.mark.parametrize(
        "padding, val_type, val, answer, expand",
        [
            ([" "], float, 10, "10.0 ", True),
            (["  "], float, 10, "10.0 ", False),
            (["\n"], float, 10, "10.0\n", False),
            ([" ", "\n", "c hi"], float, 10, "10.0\nc hi", False),
            (["  ", "\n"], float, 10, "10.0 \n", False),
            ([" "], str, "foo", "foo ", True),
            (["  "], str, "foo", "foo ", False),
            (["\n"], str, "foo", "foo\n", False),
            ([" ", "\n", "c hi"], str, "foo", "foo\nc hi", False),
            (["  ", "\n"], str, "foo", "foo \n", False),
        ],
    )
    def test_value_gen_padding_format(_, padding, val_type, val, answer, expand):
        pad_node = syntax_node.PaddingNode(padding[0])
        for pad in padding[1:]:
            pad_node.append(pad)
        if val_type == float:
            default = "1.0"
        elif val_type == str:
            default = "hi"
        node = syntax_node.ValueNode(default, val_type, pad_node)
        node.value = val
        if expand:
            warnings.simplefilter("default")
            with pytest.warns(LineExpansionWarning):
                assert node.format() == answer
        else:
            # change warnings to errors to ensure not raised
            warnings.resetwarnings()
            warnings.simplefilter("error")
            assert node.format() == answer

    @pytest.mark.parametrize(
        "input, val, enum_class, args, answer, expand",
        [
            (
                "1",
                lat.HEXAGONAL,
                lat,
                {"format_type": int, "switch_to_upper": False},
                "2",
                False,
            ),
            (
                1,
                lat.HEXAGONAL,
                lat,
                {"format_type": int, "switch_to_upper": False},
                "2",
                False,
            ),
            ("p", st.PZ, st, {"format_type": str, "switch_to_upper": True}, "PZ", True),
        ],
    )
    def test_value_enum_format(_, input, val, enum_class, args, answer, expand):
        node = syntax_node.ValueNode(input, args["format_type"])
        node.convert_to_enum(enum_class, **args)
        node.value = val
        if expand:
            warnings.simplefilter("default")
            with pytest.warns(LineExpansionWarning):
                assert node.format() == answer
        else:
            # change warnings to errors to ensure not raised
            warnings.resetwarnings()
            warnings.simplefilter("error")
            assert node.format() == answer

    def test_value_comments(self):
        value_node = syntax_node.ValueNode("1", int)
        assert len(list(value_node.comments)) == 0
        padding = syntax_node.PaddingNode("$ hi", True)
        value_node.padding = padding
        comments = list(value_node.comments)
        assert len(comments) == 1
        assert "hi" in comments[0].contents

    def test_value_trailing_comments(self):
        value_node = syntax_node.ValueNode("1", int)
        assert None is (value_node.get_trailing_comment())
        value_node._delete_trailing_comment()
        assert None is (value_node.get_trailing_comment())
        padding = syntax_node.PaddingNode("c hi", True)
        value_node.padding = padding
        comment = value_node.get_trailing_comment()
        assert len(comment) == 1
        assert comment[0].contents == "hi"
        value_node._delete_trailing_comment()
        assert None is (value_node.get_trailing_comment())

    def test_value_str(self):
        value_node = syntax_node.ValueNode("1", int)
        str(value_node)
        repr(value_node)
        padding = syntax_node.PaddingNode("$ hi", True)
        value_node.padding = padding
        str(value_node)
        repr(value_node)

    def test_value_equality(self):
        value_node1 = syntax_node.ValueNode("1", int)
        assert value_node1 == value_node1
        assert not value_node1 == syntax_node.PaddingNode("")
        value_node2 = syntax_node.ValueNode("2", int)
        assert value_node1 != value_node2
        value_node3 = syntax_node.ValueNode("hi", str)
        assert value_node1 != value_node3
        assert value_node1 == 1
        assert value_node1 != 2
        assert value_node1 != "hi"
        value_node4 = syntax_node.ValueNode("1.5", float)
        value_node5 = syntax_node.ValueNode("1.50000000000001", float)
        assert value_node4 == value_node5
        value_node5.value = 2.0
        assert value_node4 != value_node5


class TestSyntaxNode:
    @pytest.fixture
    def test_node(_):
        value1 = syntax_node.ValueNode("1.5", float)
        value2 = syntax_node.ValueNode("1", int)
        test_node = syntax_node.SyntaxNode(
            "test",
            {"foo": value1, "bar": value2, "bar2": syntax_node.SyntaxNode("test2", {})},
        )
        return test_node

    def test_syntax_init(_, test_node):
        test = test_node
        assert test.name == "test"
        assert "foo" in test.nodes
        assert "bar" in test.nodes
        assert isinstance(test.nodes["foo"], syntax_node.ValueNode)

    def test_syntax_name(_, test_node):
        test = test_node
        test.name = "hi"
        assert test.name == "hi"
        with pytest.raises(TypeError):
            test.name = 1.0

    def test_get_value(_, test_node):
        test = test_node
        assert test.get_value("foo") == 1.5
        with pytest.raises(KeyError):
            test.get_value("foo2")
        with pytest.raises(KeyError):
            test.get_value("bar2")

    def test_syntax_format(_, test_node):
        output = test_node.format()
        assert output == "1.51"

    def test_syntax_dict(_, test_node):
        test = test_node
        assert "foo" in test
        assert test["foo"] == test.nodes["foo"]

    def test_syntax_comments(_, test_node):
        padding = syntax_node.PaddingNode("$ hi", True)
        test = copy.deepcopy(test_node)
        test["foo"].padding = padding
        padding = syntax_node.PaddingNode("$ foo", True)
        test["bar"].padding = padding
        comments = list(test.comments)
        assert len(comments) == 2

    def test_syntax_trailing_comments(_, test_node):
        # test with blank tail
        assert None is test_node.get_trailing_comment()
        test = copy.deepcopy(test_node)
        test["bar2"].nodes["foo"] = syntax_node.ValueNode("1.23", float)
        assert None is (test.get_trailing_comment())
        test["bar2"]["foo"].padding = syntax_node.PaddingNode("c hi", True)
        assert len(test.get_trailing_comment()) == 1
        test._delete_trailing_comment()
        assert None is (test.get_trailing_comment())

    def test_syntax_str(_, test_node):
        str(test_node)
        repr(test_node)
        test_node._pretty_str()


class TestGeometryTree:

    @pytest.fixture
    def test_tree(_):
        left = syntax_node.ValueNode("1", int)
        right = syntax_node.ValueNode("2", int)
        op = syntax_node.PaddingNode(" ")
        return syntax_node.GeometryTree(
            "test",
            {"left": left, "operator": op, "right": right},
            montepy.Operator.INTERSECTION,
            left,
            right,
        )

    def test_geometry_init(self):
        left = syntax_node.ValueNode("1", int)
        right = syntax_node.ValueNode("2", int)
        op = syntax_node.PaddingNode(" ")
        tree = syntax_node.GeometryTree(
            "test",
            {"left": left, "operator": op, "right": right},
            montepy.Operator.INTERSECTION,
            left,
            right,
        )
        assert tree.left is left
        assert tree.right is right
        assert tree.operator == montepy.Operator.INTERSECTION

    def test_geometry_format(_, test_tree):
        assert test_tree.format() == "1 2"

    def test_geometry_str(_, test_tree):
        test = test_tree
        str(test)
        repr(test)
        test._pretty_str()

    def test_geometry_comments(_, test_tree):
        test = copy.deepcopy(test_tree)
        test.left.padding = syntax_node.PaddingNode("$ hi", True)
        comments = list(test.comments)
        assert len(comments) == 1


def test_geometry_tree_mark_last_leaf_shortcut():
    # test left leaf
    tree = {
        "left": syntax_node.ValueNode("123", int),
        "operator": syntax_node.PaddingNode(" "),
    }
    geom = syntax_node.GeometryTree(
        "test", tree, montepy.Operator.INTERSECTION, tree["left"]
    )
    geom.mark_last_leaf_shortcut(Shortcuts.REPEAT)
    assert geom._left_short_type == Shortcuts.REPEAT
    # try overriding old shortcut
    geom.mark_last_leaf_shortcut(Shortcuts.MULTIPLY)
    assert geom._left_short_type == Shortcuts.REPEAT
    tree["right"] = syntax_node.ValueNode("789", int)
    geom = syntax_node.GeometryTree(
        "test", tree, montepy.Operator.INTERSECTION, tree["left"], tree["right"]
    )
    del tree["right"]
    tree["left"] = syntax_node.ValueNode("456", int)
    # make unbalanced tree in the other way for rigor
    geom = syntax_node.GeometryTree(
        "test", tree, montepy.Operator.INTERSECTION, tree["left"], geom
    )
    # test a right-side leaf
    geom.mark_last_leaf_shortcut(Shortcuts.REPEAT)
    assert geom.right._right_short_type == Shortcuts.REPEAT
    # try overriding old shortcut
    geom.mark_last_leaf_shortcut(Shortcuts.MULTIPLY)
    assert geom.right._right_short_type == Shortcuts.REPEAT


class TestPaddingNode:
    def test_padding_init(self):
        pad = syntax_node.PaddingNode(" ")
        assert len(pad.nodes) == 1
        assert pad.value == " "

    def test_padding_is_space(self):
        pad = syntax_node.PaddingNode(" ")
        assert pad.is_space(0)
        pad.append("\n")
        assert not pad.is_space(1)
        pad.append("$ hi", True)
        assert not pad.is_space(2)
        with pytest.raises(IndexError):
            pad.is_space(5)

    def test_padding_append(self):
        pad = syntax_node.PaddingNode(" ")
        pad.append("\n")
        assert len(pad) == 2
        pad.append(" ")
        assert len(pad) == 3
        pad.append(" \n")
        assert len(pad) == 5
        pad.append("$ hi", True)
        assert len(pad) == 6

    def test_padding_format(self):
        pad = syntax_node.PaddingNode(" ")
        assert pad.format() == " "
        pad.append("$ hi", True)
        assert pad.format() == " $ hi"

    def test_padding_grab_beginning_format(self):
        pad = syntax_node.PaddingNode(" ")
        new_pad = [
            syntax_node.CommentNode("c hi"),
            "\n",
            syntax_node.CommentNode("c foo"),
        ]
        answer = copy.copy(new_pad)
        pad._grab_beginning_comment(new_pad)
        assert pad.nodes == answer + ["\n", " "]

    def test_padding_eq(self):
        pad = syntax_node.PaddingNode(" ")
        assert pad == " "
        assert pad != " hi "
        pad1 = syntax_node.PaddingNode(" ")
        assert pad == pad1
        assert not pad == 1

    def test_comment_init(self):
        comment = syntax_node.CommentNode("$ hi")
        assert isinstance(comment.nodes[0], syntax_node.SyntaxNode)
        assert len(comment.nodes) == 1
        assert comment.is_dollar
        comment = syntax_node.CommentNode(" c hi")
        assert not comment.is_dollar
        assert len(list(comment.comments)) == 1

    def test_comment_append(self):
        comment = syntax_node.CommentNode("c foo")
        comment.append("c bar")
        assert len(comment.nodes) == 2
        # test mismatch
        comment = syntax_node.CommentNode("$ hi")
        with pytest.raises(TypeError):
            comment.append("c hi")

    def test_comment_str(self):
        comment = syntax_node.CommentNode("$ hi")
        str(comment)
        repr(comment)

    def test_blank_dollar_comment(self):
        comment = syntax_node.CommentNode("$")
        assert comment.is_dollar
        assert len(list(comment.comments)) == 1
        assert len(comment.contents) == 0


def test_graveyard_comment():
    padding = syntax_node.PaddingNode(" ")
    padding.append("$ test", True)
    assert padding.has_graveyard_comment()
    padding.append(" ")
    assert padding.has_graveyard_comment()
    padding.append("\n")
    assert not padding.has_graveyard_comment()


@pytest.mark.parametrize(
    "padding,expect",
    [
        (["$ hi"], False),
        ([" c style comment"], False),
        ([" "], True),
        (["$ hi", "    ", "c hi"], True),
    ],
)
def test_padding_has_space(padding, expect):
    node = syntax_node.PaddingNode(padding[0])
    for pad in padding[1:]:
        node.append(pad)
    assert node.has_space() == expect


class TestParticlesNode:
    def test_particle_init(self):
        parts = syntax_node.ParticleNode("test", ":n,p,e")
        particle = montepy.particle.Particle
        answers = {particle.NEUTRON, particle.PHOTON, particle.ELECTRON}
        assert parts.particles == answers
        assert len(list(parts.comments)) == 0
        for part in parts:
            assert part in answers
        answers = [particle.NEUTRON, particle.PHOTON, particle.ELECTRON]
        assert parts._particles_sorted == answers

    def test_particles_setter(self):
        parts = syntax_node.ParticleNode("test", "n,p,e")
        particle = montepy.particle.Particle
        parts.particles = {particle.TRITON}
        assert parts.particles == {particle.TRITON}
        parts.particles = [particle.TRITON]
        assert parts.particles == {particle.TRITON}
        with pytest.raises(TypeError):
            parts.particles = "hi"
        with pytest.raises(TypeError):
            parts.particles = {"hi"}

    def test_particles_add_remove(self):
        parts = syntax_node.ParticleNode("test", "n,p,e")
        particle = montepy.particle.Particle
        parts.add(particle.TRITON)
        assert particle.TRITON in parts
        assert parts._particles_sorted[-1] == particle.TRITON
        with pytest.raises(TypeError):
            parts.add("hi")
        parts.remove(particle.NEUTRON)
        assert particle.NEUTRON not in parts
        with pytest.raises(TypeError):
            parts.remove("hi")

    def test_particles_sorted(self):
        parts = syntax_node.ParticleNode("test", "n,p,e")
        particle = montepy.particle.Particle
        # lazily work around internals
        parts._particles.remove(particle.NEUTRON)
        assert particle.NEUTRON not in parts._particles_sorted
        parts._particles.add(particle.TRITON)
        assert particle.TRITON in parts._particles_sorted

    def test_particles_format(self):
        parts = syntax_node.ParticleNode("test", "n,p,e")
        repr(parts)
        assert parts.format() == ":n,p,e"
        parts = syntax_node.ParticleNode("test", "N,P,E")
        assert parts.format() == ":N,P,E"


class TestListNode:
    def test_list_init(self):
        list_node = syntax_node.ListNode("list")
        assert list_node.nodes == []

    def test_list_append(self):
        list_node = syntax_node.ListNode("list")
        list_node.append(syntax_node.ValueNode("1.0", float))
        assert len(list_node) == 1

    def test_list_str(self):
        list_node = syntax_node.ListNode("list")
        list_node.append(syntax_node.ValueNode("1.0", float))
        str(list_node)
        repr(list_node)
        list_node._pretty_str()

    def test_list_slicing(self):
        list_node = syntax_node.ListNode("list")
        for i in range(20):
            list_node.append(syntax_node.ValueNode("1.0", float))
        assert list_node[5] == syntax_node.ValueNode("1.0", float)
        for val in list_node[1:5]:
            assert val == syntax_node.ValueNode("1.0", float)
        for val in list_node[1:5:1]:
            assert val == syntax_node.ValueNode("1.0", float)
        for val in list_node[::1]:
            assert val == syntax_node.ValueNode("1.0", float)
        for val in list_node[5:1:-1]:
            assert val == syntax_node.ValueNode("1.0", float)
        for val in list_node[::-1]:
            assert val == syntax_node.ValueNode("1.0", float)
        with pytest.raises(IndexError):
            list_node[50]

    def test_list_equality(self):
        list_node1 = syntax_node.ListNode("list")
        for i in range(20):
            list_node1.append(syntax_node.ValueNode("1.0", float))
        assert not list_node1 == "hi"
        list2 = [syntax_node.ValueNode("1.0", float)] * 19
        assert not list_node1 == list2
        list2 = [syntax_node.ValueNode("1.0", float)] * 20
        assert list_node1 == list2
        list2 = [syntax_node.ValueNode("1.0", float)] * 19 + [
            syntax_node.ValueNode("1.5", float)
        ]
        assert list_node1 != list2

    def test_list_trailing_comment(self):
        list_node1 = syntax_node.ListNode("list")
        for i in range(20):
            list_node1.append(syntax_node.ValueNode("1.0", float))
        padding = syntax_node.PaddingNode("c hi", True)
        list_node1[-1].padding = padding
        comments = list(list_node1.get_trailing_comment())
        assert len(comments) == 1
        list_node1._delete_trailing_comment()
        assert None is (list_node1.get_trailing_comment())
        # test an empty list
        list_node1 = syntax_node.ListNode("list")
        assert None is (list_node1.get_trailing_comment())
        list_node1._delete_trailing_comment()
        assert None is (list_node1.get_trailing_comment())

    def test_list_format(self):
        list_node = syntax_node.ListNode("list")
        for i in range(20):
            list_node.append(syntax_node.ValueNode("1.0", float))
        assert list_node.format() == "1.0 " * 19 + "1.0"

    def test_list_comments(self):
        list_node = syntax_node.ListNode("list")
        for i in range(20):
            list_node.append(syntax_node.ValueNode("1.0", float))
        padding = syntax_node.PaddingNode("$ hi", True)
        list_node[-1].padding = padding
        comments = list(list_node.comments)
        assert len(comments) == 1


class TestMaterialssNode:
    def test_isotopes_init(self):
        isotope = syntax_node.MaterialsNode("test")
        assert isotope.name == "test"
        assert isinstance(isotope.nodes, list)

    def test_isotopes_append(self):
        isotopes = syntax_node.MaterialsNode("test")
        zaid = syntax_node.ValueNode("1001.80c", str)
        concentration = syntax_node.ValueNode("1.5", float)
        isotopes.append_nuclide(("isotope_fraction", zaid, concentration))
        assert isotopes.nodes[-1][0] == zaid
        assert isotopes.nodes[-1][1] == concentration

    def test_isotopes_format(self):
        padding = syntax_node.PaddingNode(" ")
        isotopes = syntax_node.MaterialsNode("test")
        zaid = syntax_node.ValueNode("1001.80c", str)
        zaid.padding = padding
        concentration = syntax_node.ValueNode("1.5", float)
        concentration.padding = padding
        isotopes.append_nuclide(("isotope_fraction", zaid, concentration))
        assert isotopes.format() == "1001.80c 1.5 "

    def test_isotopes_str(self):
        isotopes = syntax_node.MaterialsNode("test")
        zaid = syntax_node.ValueNode("1001.80c", str)
        concentration = syntax_node.ValueNode("1.5", float)
        isotopes.append_nuclide(("isotope_fraction", zaid, concentration))
        str(isotopes)
        repr(isotopes)
        isotopes._pretty_str()

    def test_isotopes_iter(self):
        isotopes = syntax_node.MaterialsNode("test")
        zaid = syntax_node.ValueNode("1001.80c", str)
        concentration = syntax_node.ValueNode("1.5", float)
        isotopes.append_nuclide(("isotope_fraction", zaid, concentration))
        isotopes.append_nuclide(("isotope_fraction", zaid, concentration))
        for combo in isotopes:
            assert len(combo) == 2

    def test_isotopes_comments(self):
        padding = syntax_node.PaddingNode(" ")
        isotopes = syntax_node.MaterialsNode("test")
        zaid = syntax_node.ValueNode("1001.80c", str)
        zaid.padding = padding
        concentration = syntax_node.ValueNode("1.5", float)
        padding = copy.deepcopy(padding)
        padding.append("$ hi", True)
        concentration.padding = padding
        isotopes.append_nuclide(("isotope_fraction", zaid, concentration))
        comments = list(isotopes.comments)
        assert len(comments) == 1
        assert comments[0].contents == "hi"

    def test_isotopes_trailing_comment(self):
        padding = syntax_node.PaddingNode(" ")
        isotopes = syntax_node.MaterialsNode("test")
        zaid = syntax_node.ValueNode("1001.80c", str)
        zaid.padding = padding
        concentration = syntax_node.ValueNode("1.5", float)
        padding = copy.deepcopy(padding)
        padding.append("c hi", True)
        concentration.padding = padding
        isotopes.append_nuclide(("isotope_fraction", zaid, concentration))
        comments = isotopes.get_trailing_comment()
        assert len(comments) == 1
        assert comments[0].contents == "hi"
        isotopes._delete_trailing_comment()
        comments = isotopes.get_trailing_comment()
        assert None is (comments)


class TestShortcutNode:
    def test_basic_shortcut_init(self):
        with pytest.raises(ValueError):
            syntax_node.ShortcutNode("")
        # test a blank init
        shortcut = syntax_node.ShortcutNode(
            short_type=syntax_node.Shortcuts.LOG_INTERPOLATE
        )
        assert shortcut._type == syntax_node.Shortcuts.LOG_INTERPOLATE
        assert shortcut.end_padding.nodes == [" "]
        with pytest.raises(TypeError):
            syntax_node.ShortcutNode(short_type="")

    def test_shortcut_end_padding_setter(self):
        short = syntax_node.ShortcutNode()
        pad = syntax_node.PaddingNode(" ")
        short.end_padding = pad
        assert short.end_padding == pad
        with pytest.raises(TypeError):
            short.end_padding = " "


"""
Most examples, unless otherwise noted are taken from Section 2.8.1
of LA-UR-17-29981.
"""
tests = {
    "1 3M 2r": [1, 3, 3, 3],
    # unofficial
    "0.01 2ILOG 10": [0.01, 0.1, 1, 10],
    "1 3M I 4": [1, 3, 3.5, 4],
    "1 3M 3M": [1, 3, 9],
    "1 2R 2I 2.5": [1, 1, 1, 1.5, 2, 2.5],
    "1 R 2m": [1, 1, 2],
    "1 R R": [1, 1, 1],
    "1 2i 4 3m": [1, 2, 3, 4, 12],
    # unofficial
    "1 i 3": [1, 2, 3],
    # unofficial
    "1 ilog 100": [1, 10, 100],
    "1 1r ilog 100": [1, 1, 10, 100],
    # last official one
    "1 2i 4 2i 10": [
        1,
        2,
        3,
        4,
        6,
        8,
        10,
    ],
    "1 2j 4": [1, montepy.Jump(), montepy.Jump(), 4],
    "1 j": [1, montepy.Jump()],
}


@pytest.mark.parametrize("test, answer", tests.items())
def test_shortcut_expansion_valid(test, answer):
    parser = ShortcutTestFixture()
    print(test)
    input = Input([test], BlockType.DATA)
    parsed = parser.parse(input.tokenize())
    print(parsed)
    for val, gold in zip(parsed, answer):
        if val.value is None:
            assert gold == montepy.Jump()
        else:
            assert val.value == pytest.approx(gold)
    assert parsed.format() == test


@pytest.mark.parametrize(
    "test, exception",
    [
        ("3J 4R", ValueError),
        ("1 4I 3M", MalformedInputError),
        # last official test
        ("1 4I J", MalformedInputError),
        ("1 2Ilog J", MalformedInputError),
        ("J 2Ilog 5", ValueError),
        ("3J 2M", ValueError),
        ("10 M", MalformedInputError),
        ("2R", MalformedInputError),
    ],
)
def test_shortcut_expansion_invalid(test, exception):
    print(test)
    parser = ShortcutTestFixture()
    with pytest.raises(exception):
        input = Input([test], BlockType.DATA)
        parsed = parser.parse(input.tokenize())
        if parsed is None:
            raise montepy.exceptions.MalformedInputError("", "")


@pytest.mark.parametrize(
    "test, answer, form_ans",
    [
        ("1 3r ", [1, 1, 1, 1], None),
        ("1 1 3r ", [1, 1, 1, 1, 1], None),
        ("1 1 2M 3r ", [1, 1, 2, 2, 2, 2], None),
        ("1 -2M ", [1, -2], None),
        ("1 2i 4 ", [1, 2, 3, 4], None),
        ("1 2i 4 ", [1, 2, 3, 4], None),
        ("1 1 2i 4 ", [1, 1, 2, 3, 4], None),
        ("1 1 2i 4 5 6 ", [1, 1, 2, 3, 4, 5, 6], "1 1 2I 4  5 6"),
        ("1 1 2i 4:5 6 ", [1, 1, 2, 3, 4, 5, 6], "1 1 2I 4 :5 6"),
        ("1 ilog 100 ", [1, 10, 100], "1 1ILOG 100"),
        ("1 1r ilog 100 ", [1, 1, 10, 100], "1 1R 1ILOG 100"),
        # secretly test iterator
        ("#1", [1], None),
        ("#(1 2 3)", [1, 2, 3], None),
        ("1 2:( 3 4 5)", [1, 2, 3, 4, 5], None),
    ],
)
def test_shortcut_geometry_expansion(test, answer, form_ans):

    parser = ShortcutGeometryTestFixture()
    print(test)
    input = Input([test], BlockType.CELL)
    parsed = parser.parse(input.tokenize())
    for val, gold in zip(parsed, answer):
        assert val.value == gold
    if form_ans:
        assert parsed.format().rstrip() == form_ans
    else:
        assert parsed.format().rstrip() == test.upper().rstrip()


@pytest.mark.parametrize(
    "test, length, indices",
    [
        ("1 3r ", 1, {0: Shortcuts.REPEAT}),
        ("1 1 3r ", 2, {1: Shortcuts.REPEAT}),
        ("1 1 2M 3r ", 3, {1: Shortcuts.MULTIPLY, 2: Shortcuts.REPEAT}),
        ("1 -2M ", 1, {0: Shortcuts.MULTIPLY}),
        ("1 2i 4 ", 1, {0: Shortcuts.INTERPOLATE}),
        ("1 2i 4 ", 1, {0: Shortcuts.INTERPOLATE}),
        ("1 1 2i 4 ", 2, {1: Shortcuts.INTERPOLATE}),
        ("1 1 2i 4 5 6 ", 4, {1: Shortcuts.INTERPOLATE}),
        ("1 1 2i 4:5 6 ", 4, {1: Shortcuts.INTERPOLATE}),
        ("1 ilog 100 ", 1, {0: Shortcuts.LOG_INTERPOLATE}),
        # secretly test iterator
        ("#1", 1, {}),
        ("#(1 2 3)", 3, {}),
        ("1 2:( 3 4 5)", 5, {}),
    ],
)
def test_shortcut_flatten(test, length, indices):

    parser = ShortcutGeometryTestFixture()
    print(test)
    input = Input([test], BlockType.CELL)
    parsed = parser.parse(input.tokenize())
    flatpack = parsed._flatten_shortcut()
    assert len(flatpack) == length
    for index, short_type in indices.items():
        assert isinstance(flatpack.nodes[index], syntax_node.ShortcutNode)
        assert flatpack.nodes[index].type == short_type


@pytest.mark.parametrize(
    "in_str, answer",
    [
        ("1 5R", "1 5R"),
        ("1 5r", "1 5r"),
        ("1 5r 2m", "1 5r 2m"),
        ("1 r", "1 r"),
        ("1 r 2 2r", "1 r 2 2r"),
        ("1 J 5 2R", "1 J 5 2R"),
        ("1 2i 5", "1 2i 5"),
        ("1 2ilog 5", "1 2ilog 5"),
        ("1 r 2i 5", "1 r 2i 5"),
        ("1 2i 5 r", "1 2i 5 r"),
        ("1 r 2ilog 5", "1 r 2ilog 5"),
        ("1 5M", "1 5M"),
        ("1 5m", "1 5m"),
        ("1 5m 2r", "1 5m 2r"),
        ("2j ", "2j "),
        ("2j", "2j"),
        ("2J ", "2J "),
        ("J", "J"),
        ("0 2i 3 10 2i 16 1", "0 2i 3 10 2i 16 1"),
    ],
)
def test_shortcut_format(in_str, answer):
    parser = ShortcutTestFixture()
    input = Input([in_str], BlockType.CELL)
    shortcut = parser.parse(input.tokenize())
    assert shortcut.format() == answer
    # try jump with empty jump shortcut
    shortcut.nodes.clear()
    assert shortcut.format() == ""


@pytest.mark.parametrize(
    "testee, outcome",
    [("(", False), (1.0, True), (0.0, True), ("s", False), (5.0, False)],
)
def test_shortcut_contains(testee, outcome):
    parser = ShortcutTestFixture()
    input = Input(["1 0 2R"], BlockType.CELL)
    node = parser.parse(input.tokenize())
    assert (testee in node) == outcome, "Contains result was incorrect."


class ShortcutTestFixture(MCNP_Parser):
    @_("number_sequence", "shortcut_sequence")
    def shortcut_magic(self, p):
        return p[0]


class ShortcutGeometryTestFixture(montepy.input_parser.cell_parser.CellParser):
    @_("geometry_expr")
    def geometry(self, p):
        return p[0]


class TestShortcutListIntegration:
    @pytest.fixture
    def parser(_):
        return ShortcutTestFixture()

    @pytest.fixture
    def list_node(_, parser):
        input = Input(["1 1 2i 4"], BlockType.DATA)
        return parser.parse(input.tokenize())

    def test_shortcut_list_node_init(_, list_node):
        answers = [1, 1, 2, 3, 4]
        for val, gold in zip(list_node, answers):
            assert val.value == pytest.approx(gold)

    def test_shortcut_list_update_vals(_, list_node):
        list_node = copy.deepcopy(list_node)
        values = list(list_node)
        list_node.update_with_new_values(values)
        assert list(list_node) == values

    def test_shortcut_list_update_vals_repeat(_, parser):
        input = Input(["1 2 3 5R 0 0"], BlockType.DATA)
        list_node = parser.parse(input.tokenize())
        values = list(list_node)
        values.insert(2, syntax_node.ValueNode(3.0, float))
        list_node.update_with_new_values(values)
        assert len(list_node._shortcuts[0].nodes) == 7
        assert list(list_node) == values

    def test_shortcut_list_trailing_jump(_, parser):
        input = Input(["1 2 3 5R 0 0"], BlockType.DATA)
        list_node = parser.parse(input.tokenize())
        values = list(list_node)
        values.append(syntax_node.ValueNode(Jump(), float))
        list_node.update_with_new_values(values)
        assert list(list_node) == values[:-1]
        # test with User specified end jump
        input = Input(["1 2 3 5R 0 0 j"], BlockType.DATA)
        list_node = parser.parse(input.tokenize())
        values = list(list_node)
        values.append(syntax_node.ValueNode(Jump(), float))
        list_node.update_with_new_values(values)
        assert list(list_node) == values

    def test_shortcut_list_touching_shortcuts(_, parser):
        input = Input(["1 2 3 5R 3 3 4R 0 0"], BlockType.DATA)
        list_node = parser.parse(input.tokenize())
        values = list(list_node)
        list_node.update_with_new_values(values)
        assert list(list_node) == values

    def test_shortcut_then_jump_compress(_, parser):
        for input_str, index in [
            ("1 2 3 5R 3 3 4R 0 0", -2),
            ("1 2 3M 4", -2),
            ("1 2ilog 10", -2),
        ]:
            print(input_str)
            input = Input([input_str], BlockType.DATA)
            list_node = parser.parse(input.tokenize())
            values = list(list_node)
            values[index].value = None
            list_node.update_with_new_values(values)
            assert list(list_node) == values

    def test_shortcut_list_shortcut_cant_consume(_, parser):
        # try with wrong type
        input = Input(["1 2 3 5R 3 3 4R "], BlockType.DATA)
        list_node = parser.parse(input.tokenize())
        values = list(list_node)
        values.append(syntax_node.ValueNode("hi", str))
        list_node.update_with_new_values(values)
        assert list(list_node) == values
        assert len(list_node._shortcuts[1].nodes) == 5
        # try with wrong value
        input = Input(["1 2 3 5R 3 3 4R "], BlockType.DATA)
        list_node = parser.parse(input.tokenize())
        values = list(list_node)
        values.append(syntax_node.ValueNode("5.0", float))
        list_node.update_with_new_values(values)
        assert list(list_node) == values
        assert len(list_node._shortcuts[1].nodes) == 5
        # try with right value
        values[-1].value = 3.0
        list_node.update_with_new_values(values)
        assert list(list_node) == values
        assert len(list_node._shortcuts[1].nodes) == 6

    def test_shortcut_list_multiply(_, parser):
        input = Input(["1 2 5M "], BlockType.DATA)
        list_node = parser.parse(input.tokenize())
        values = list(list_node)
        values.append(syntax_node.ValueNode("5.0", float))
        list_node.update_with_new_values(values)
        assert list(list_node) == values
        assert len(list_node._shortcuts[0].nodes) == 2
        input = Input(["0.5 2R 5M "], BlockType.DATA)
        list_node = parser.parse(input.tokenize())
        values = list(list_node)
        values.append(syntax_node.ValueNode("5.0", float))
        list_node.update_with_new_values(values)
        assert list(list_node) == values
        assert len(list_node._shortcuts[1].nodes) == 1

    def test_shortcut_list_interpolate(_, parser):
        # try with log interpolate
        input = Input(["1.0 0.01 2ILOG 10"], BlockType.DATA)
        list_node = parser.parse(input.tokenize())
        values = list(list_node)
        values.append(syntax_node.ValueNode("100", float))
        list_node.update_with_new_values(values)
        assert list(list_node) == values
        assert len(list_node._shortcuts[0].nodes) == 5
        # try with linear interpolate
        input = Input(["1 1 2I 2.5"], BlockType.DATA)
        list_node = parser.parse(input.tokenize())
        values = list(list_node)
        values.append(syntax_node.ValueNode("3", float))
        list_node.update_with_new_values(values)
        assert list(list_node) == values
        assert len(list_node._shortcuts[0].nodes) == 5


class TestSyntaxParsing:
    def testCardInit(self):
        with pytest.raises(TypeError):
            Input("5", BlockType.CELL)
        with pytest.raises(TypeError):
            Input([5], BlockType.CELL)
        with pytest.raises(TypeError):
            Input(["5"], "5")

    def testMessageInit(self):
        with pytest.raises(TypeError):
            Message(["hi"], "5")
        with pytest.raises(TypeError):
            Message(["hi"], [5])

    def testTitleInit(self):
        with pytest.raises(TypeError):
            Title(["hi"], 5)

    def testMessageFinder(self):
        test_message = "this is a message"
        test_string = f"""message: {test_message}

test title
"""
        for tester, validator in [
            (test_string, test_message),
            (test_string.upper(), test_message.upper()),
        ]:
            with StringIO(tester) as fh:
                generator = input_syntax_reader.read_front_matters(fh, (6, 2, 0))
                card = next(generator)
                assert isinstance(card, montepy.input_parser.mcnp_input.Message)
                assert card.lines[0] == validator
                assert len(card.lines) == 1

    def testReadCardStr(self):
        card = ReadInput(["Read file=hi.imcnp"], BlockType.CELL)
        assert str(card) == "READ INPUT: Block_Type: BlockType.CELL"
        assert (
            repr(card)
            == "READ INPUT: BlockType.CELL: ['Read file=hi.imcnp'] File: hi.imcnp"
        )

    def testSingleLineEndComment(self):
        # tests issues #117
        input = Input(["c"], BlockType.CELL)
        generator = input.tokenize()
        token = next(generator)
        assert token.type == "COMMENT"
        assert token.value == "c"

    def testReadCardConfusions(self):
        for file in {"A1_cells", "I1_cells"}:
            input = ReadInput([f"Read FILE={file}"], BlockType.CELL)
            assert input.file_name == file

    def testReadCardBadSyntax(self):
        with pytest.raises(ParsingError):
            card = ReadInput(["Read 1"], BlockType.CELL)

    def testTitleFinder(self):
        test_title = "Richard Stallman writes GNU"
        test_string = f"""{test_title}
1 0 -1
"""
        for tester, validator in [
            (test_string, test_title),
            (test_string.upper(), test_title.upper()),
        ]:
            with StringIO(tester) as fh:
                generator = input_syntax_reader.read_front_matters(fh, (6, 2, 0))
                card = next(generator)
                assert isinstance(card, montepy.input_parser.mcnp_input.Title)
                assert card.title == validator

    def testCardFinder(self):
        test_string = """1 0 -1
     5"""
        for i in range(5):
            tester = " " * i + test_string
            with StringIO(tester) as fh:
                fh.lineno = 0
                fh.path = "foo"
                generator = input_syntax_reader.read_data(fh, (6, 2, 0))
                card = next(generator)
                assert isinstance(card, montepy.input_parser.mcnp_input.Input)
                answer = [" " * i + "1 0 -1", "     5"]
                assert len(answer) == len(card.input_lines)
                for j, line in enumerate(card.input_lines):
                    assert line == answer[j]
                assert card.block_type == montepy.input_parser.block_type.BlockType.CELL

    def testReadCardFinder(self):
        test_string = "read file=foo.imcnp "
        with StringIO(test_string) as fh:
            fh.lineno = 0
            fh.path = "foo"
            card = next(input_syntax_reader.read_data(fh, (6, 2, 0)))
            assert None is (card)  # the read input is hidden from the user

    def testBlockId(self):
        test_string = "1 0 -1"
        for i in range(3):
            tester = "\n" * i + test_string
            with StringIO(tester) as fh:
                fh.lineno = 0
                fh.path = "foo"
                fh.name = "name"
                for card in input_syntax_reader.read_data(
                    fh, (6, 2, 0), recursion=True
                ):
                    pass
                assert montepy.input_parser.block_type.BlockType(i) == card.block_type

    def testCommentFormatInput(self):
        in_strs = ["c foo", "c bar"]
        card = montepy.input_parser.syntax_node.CommentNode(in_strs[0])
        output = card.format()
        answer = "c foo"
        str_answer = "COMMENT: c foo"
        assert repr(card) == str_answer
        assert "c foo" == str(card)
        assert len(answer) == len(output)
        for i, line in enumerate(output):
            assert answer[i] == line

    def testMessageFormatInput(self):
        answer = ["MESSAGE: foo", "bar", ""]
        card = montepy.input_parser.mcnp_input.Message(answer, ["foo", "bar"])
        str_answer = """MESSAGE:
foo
bar
"""
        assert str_answer == repr(card)
        assert "MESSAGE: 2 lines" == str(card)
        output = card.format_for_mcnp_input((6, 2, 0))
        assert len(answer) == len(output)
        for i, line in enumerate(output):
            assert answer[i] == line

    def testTitleFormatInput(self):
        card = montepy.input_parser.mcnp_input.Title(["foo"], "foo")
        answer = ["foo"]
        str_answer = "TITLE: foo"
        assert str(card) == str_answer
        output = card.format_for_mcnp_input((6, 2, 0))
        assert len(answer) == len(output)
        for i, line in enumerate(output):
            assert answer[i] == line

    def testReadInput(self):
        # TODO ensure comments are properly glued to right input
        generator = input_syntax_reader.read_input_syntax(
            MCNP_InputFile("tests/inputs/test.imcnp")
        )
        mcnp_in = montepy.input_parser.mcnp_input
        input_order = [mcnp_in.Message, mcnp_in.Title]
        input_order += [mcnp_in.Input] * 29
        for i, input in enumerate(generator):
            print(input.input_lines)
            print(input_order[i])
            assert isinstance(input, input_order[i])

    def testReadInputWithRead(self):
        generator = input_syntax_reader.read_input_syntax(
            MCNP_InputFile("tests/inputs/testRead.imcnp")
        )
        next(generator)  # skip title
        next(generator)  # skip read none
        next(generator)  # skip surfaces input
        next(generator)  # skip data mode input
        card = next(generator)
        answer = ["1 0 -1", "c"]
        assert answer == card.input_lines

    def testReadInputWithVertMode(self):
        generator = input_syntax_reader.read_input_syntax(
            MCNP_InputFile("tests/inputs/testVerticalMode.imcnp")
        )
        next(generator)
        next(generator)
        with pytest.raises(montepy.exceptions.UnsupportedFeature):
            next(generator)

    def testCardStringRepr(self):
        in_str = "1 0 -1"
        card = montepy.input_parser.mcnp_input.Input(
            [in_str], montepy.input_parser.block_type.BlockType.CELL
        )
        assert str(card) == "INPUT: BlockType.CELL"
        assert repr(card) == "INPUT: BlockType.CELL: ['1 0 -1']"

    def testDataInputNameParsing(self):
        tests = {
            "kcOde": {"prefix": "kcode", "number": None, "classifier": None},
            "M300": {"prefix": "m", "number": 300, "classifier": None},
            "IMP:N,P,E": {
                "prefix": "imp",
                "number": None,
                "classifier": [Particle.NEUTRON, Particle.PHOTON, Particle.ELECTRON],
            },
            "F1004:n,P": {
                "prefix": "f",
                "number": 1004,
                "classifier": [Particle.NEUTRON, Particle.PHOTON],
            },
        }
        for in_str, answer in tests.items():
            # Testing parsing the names
            print("in", in_str, "answer", answer)
            card = montepy.input_parser.mcnp_input.Input(
                [in_str], montepy.input_parser.block_type.BlockType.DATA
            )
            data_input = montepy.data_inputs.data_input.DataInput(card, fast_parse=True)
            assert data_input.prefix == answer["prefix"]
            if answer["number"]:
                assert data_input._input_number.value == answer["number"]
            if answer["classifier"]:
                assert sorted(data_input.particle_classifiers) == sorted(
                    answer["classifier"]
                )

    @pytest.mark.parametrize(
        "in_str, answer",
        [
            ("kcOde5", {"prefix": "kcode", "number": False, "classifier": 0}),
            ("M-300", {"prefix": "m", "number": True, "classifier": 0}),
            ("M", {"prefix": "m", "number": True, "classifier": 0}),
            ("f4m", {"prefix": "fm", "number": True, "classifier": 1}),
            ("IMP:N,P,E", {"prefix": "imp", "number": False, "classifier": 0}),
            ("IMP", {"prefix": "imp", "number": False, "classifier": 2}),
        ],
    )
    def test_data_name_enforce_bad(_, in_str, answer):
        with pytest.raises(montepy.exceptions.MalformedInputError):
            card = montepy.input_parser.mcnp_input.Input(
                [in_str], montepy.input_parser.block_type.BlockType.DATA
            )
            Fixture = DataInputTestFixture
            Fixture._class_prefix1 = answer["prefix"]
            Fixture._has_number1 = answer["number"]
            Fixture._has_classifier1 = answer["classifier"]
            card = Fixture(card)

    @pytest.mark.parametrize(
        "in_str, answer",
        [
            ("IMP:N,P,E", {"prefix": "imp", "number": False, "classifier": 2}),
            ("F1004:n,P", {"prefix": "f", "number": True, "classifier": 1}),
        ],
    )
    def test_dat_name_enforce_good(_, in_str, answer):
        card = montepy.input_parser.mcnp_input.Input(
            [in_str], montepy.input_parser.block_type.BlockType.DATA
        )
        Fixture = DataInputTestFixture
        Fixture._class_prefix1 = answer["prefix"]
        Fixture._has_number1 = answer["number"]
        Fixture._has_classifier1 = answer["classifier"]
        card = Fixture(card)

    @pytest.mark.parametrize(
        "version, line_number",
        [
            ((5, 1, 60), 80),
            ((6, 1, 0), 80),
            ((6, 2, 0), 128),
            ((6, 3, 0), 128),
            ((6, 3, 1), 128),
            ((6, 3, 3), 128),  # Test for newer not released versions
            ((7, 4, 0), 128),
        ],
    )
    def test_get_line_numbers(_, version, line_number):
        assert line_number == montepy.constants.get_max_line_length(version)
        with pytest.raises(montepy.exceptions.UnsupportedFeature):
            montepy.constants.get_max_line_length((5, 1, 38))

    def test_jump(self):
        jump = Jump()
        assert "J" == str(jump)
        jump2 = Jump()
        assert jump == jump2
        with pytest.raises(TypeError):
            bool(jump)

    def test_jump_and_a_hop(self):
        jump = Jump()
        # first you need to hop
        assert "j" == jump.lower()
        # then you need to skip
        assert "Jump" == jump.title()
        # before you can jump
        assert "J" == jump.upper()
        str(jump)
        repr(jump)


class TestClassifierNode:
    def test_classifier_init(self):
        classifier = syntax_node.ClassifierNode()
        assert None is (classifier.prefix)
        assert None is (classifier.number)
        assert None is (classifier.particles)
        assert None is (classifier.modifier)
        assert None is (classifier.padding)

    def test_classifier_setter(self):
        classifier = syntax_node.ClassifierNode()
        classifier.prefix = syntax_node.ValueNode("M", str)
        assert classifier.prefix.value == "M"
        classifier.number = syntax_node.ValueNode("124", int)
        assert classifier.number.value == 124
        classifier.modifier = syntax_node.ValueNode("*", str)
        assert classifier.modifier.value == "*"
        classifier.padding = syntax_node.PaddingNode(" ")
        assert len(classifier.padding.nodes) == 1

    def test_classifier_format(self):
        classifier = syntax_node.ClassifierNode()
        classifier.prefix = syntax_node.ValueNode("M", str)
        assert classifier.format() == "M"
        classifier.number = syntax_node.ValueNode("124", int)
        assert classifier.format() == "M124"
        classifier.modifier = syntax_node.ValueNode("*", str)
        assert classifier.format() == "*M124"
        classifier.padding = syntax_node.PaddingNode(" ")
        assert classifier.format() == "*M124 "
        str(classifier)
        repr(classifier)

    def test_classifier_comments(self):
        classifier = syntax_node.ClassifierNode()
        classifier.prefix = syntax_node.ValueNode("M", str)
        assert len(list(classifier.comments)) == 0
        classifier.padding = syntax_node.PaddingNode(" ")
        classifier.padding.append("$ hi", True)
        assert len(list(classifier.comments)) == 1


class TestParametersNode:
    @pytest.fixture
    def param(_):
        param = syntax_node.ParametersNode()
        classifier = syntax_node.ClassifierNode()
        classifier.prefix = syntax_node.ValueNode("vol", str)
        list_node = syntax_node.ListNode("data")
        list_node.append(syntax_node.ValueNode("1.0", float))
        param.append(
            syntax_node.SyntaxNode(
                "hi",
                {
                    "classifier": classifier,
                    "seperator": syntax_node.ValueNode("=", str),
                    "data": list_node,
                },
            )
        )
        return param

    def test_parameter_init(self):
        param = syntax_node.ParametersNode()
        assert isinstance(param.nodes, dict)

    def test_parameter_append(_, param):
        assert len(param.nodes) == 1
        with pytest.raises(RedundantParameterSpecification):
            classifier = syntax_node.ClassifierNode()
            classifier.prefix = syntax_node.ValueNode("vol", str)
            param.append(syntax_node.SyntaxNode("foo", {"classifier": classifier}))

    def test_parameter_dict(_, param):
        assert param["vol"] == param.nodes["vol"]
        with pytest.raises(KeyError):
            param["hi"]
        assert "vol" in param

    def test_parameter_str(_, param):
        str(param)
        repr(param)
        param._pretty_str()

    def test_parameter_format(_, param):
        assert param.format() == "vol=1.0"

    def test_parameter_comments(_, param):
        assert len(list(param.comments)) == 0
        param["vol"]["data"][0].padding = syntax_node.PaddingNode(" ")
        param["vol"]["data"][0].padding.append("$ hi", True)
        assert len(list(param.comments)) == 1

    def test_parameter_trailing_comments(_, param):
        assert None is (param.get_trailing_comment())
        param._delete_trailing_comment()
        assert None is (param.get_trailing_comment())
        padding = syntax_node.PaddingNode("$ hi", True)
        param["vol"]["data"][0].padding = padding
        comment = param.get_trailing_comment()
        assert None is (comment)
        padding.append(syntax_node.CommentNode("c hi"), True)
        comment = param.get_trailing_comment()
        assert comment[0].contents == "hi"
        param._delete_trailing_comment()
        assert None is (param.get_trailing_comment())


class DataInputTestFixture(montepy.data_inputs.data_input.DataInputAbstract):
    _class_prefix1 = None
    _has_number1 = None
    _has_classifier1 = None

    def __init__(self, input_card=None):
        """
        :param input_card: the Card object representing this data input
        :type input_card: Input
        """
        super().__init__(input_card, fast_parse=True)

    def _class_prefix(self):
        return self._class_prefix1

    def _has_number(self):
        return self._has_number1

    def _has_classifier(self):
        return self._has_classifier1

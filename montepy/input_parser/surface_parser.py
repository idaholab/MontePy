# Copyright 2024-2025, Battelle Energy Alliance, LLC All Rights Reserved.
import montepy
from montepy.input_parser.parser_base import MCNP_Parser
from montepy.input_parser.tokens import SurfaceLexer
from montepy.input_parser import syntax_node

from sly.lex import Token
import typing


class SurfaceParser(MCNP_Parser):
    """A parser for MCNP surfaces.

    Returns
    -------
    SyntaxNode
    """

    debugfile = None

    @_(
        "surface_id SURFACE_TYPE padding number_sequence",
        "padding surface_id SURFACE_TYPE padding number_sequence",
        "surface_id number_phrase SURFACE_TYPE padding number_sequence",
        "padding surface_id number_phrase SURFACE_TYPE padding number_sequence",
    )
    def surface(self, p):
        ret = {}
        if isinstance(p[0], syntax_node.PaddingNode):
            ret["start_pad"] = p[0]
        else:
            ret["start_pad"] = syntax_node.PaddingNode()
        ret["surface_num"] = p.surface_id
        if hasattr(p, "number_phrase"):
            ret["pointer"] = p.number_phrase
        else:
            ret["pointer"] = syntax_node.ValueNode(None, int)
        if hasattr(p, "padding"):
            padding = p.padding
        else:
            padding = p.padding1
        ret["surface_type"] = syntax_node.ValueNode(p.SURFACE_TYPE, str, padding)
        ret["data"] = p.number_sequence
        return syntax_node.SyntaxNode("surface", ret)

    @_('"*" number_phrase', '"+" number_phrase', "number_phrase")
    def surface_id(self, p):
        ret = {}
        token = None
        if isinstance(p[0], str) and p[0] in {"*", "+"}:
            token = p[0]
        ret["modifier"] = syntax_node.ValueNode(token, str, never_pad=True)

        ret["number"] = p.number_phrase
        return syntax_node.SyntaxNode("surface_number", ret)


class JitSurfParser:

    @staticmethod
    def parse(tokenizer: typing.Generator[Token, None, None]):
        number = None
        surface_type = None
        for token in tokenizer:
            if token.type in {"SPACE", "COMMENT", "DOLLAR_COMMENT", "*", "+"}:
                continue
            if token.type == "NUMBER" and number is None:
                number = syntax_node.ValueNode(token.value, int)
            # skip pointer
            elif token.type == "NUMBER":
                continue
            elif number is not None and token.type != "SURFACE_TYPE":
                assert False
            else:
                surface_type = syntax_node.ValueNode(token.value, str)
                surface_type._convert_to_enum(montepy.surfaces.SurfaceType)
                return syntax_node.SyntaxNode(
                    "jit surface", {"number": number, "surface_type": surface_type}
                )

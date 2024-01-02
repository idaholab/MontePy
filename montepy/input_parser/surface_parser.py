# Copyright 2024, Battelle Energy Alliance, LLC All Rights Reserved.
from montepy.input_parser.parser_base import MCNP_Parser
from montepy.input_parser.tokens import SurfaceLexer
from montepy.input_parser import syntax_node


class SurfaceParser(MCNP_Parser):
    """
    A parser for MCNP surfaces.

    .. versionadded:: 0.2.0
        This was added with the major parser rework.

    :rtype: SyntaxNode
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
        if isinstance(p[0], str) and p[0] in {"*", "+"}:
            ret["modifier"] = syntax_node.ValueNode(p[0], str)
        else:
            ret["modifier"] = syntax_node.ValueNode(None, str)

        ret["number"] = p.number_phrase
        return syntax_node.SyntaxNode("surface_number", ret)

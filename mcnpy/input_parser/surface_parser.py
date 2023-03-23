from mcnpy.input_parser.parser_base import MCNP_Parser
from mcnpy.input_parser.tokens import SurfaceLexer
from mcnpy.input_parser import syntax_node


class SurfaceParser(MCNP_Parser):
    debugfile = None

    @_(
        "surface_id SURFACE_TYPE padding number_sequence",
        "surface_id number_phrase SURFACE_TYPE padding number_sequence",
    )
    def surface(self, p):
        ret = {}
        ret["surface_num"] = p.surface_id
        if hasattr(p, "number_phrase"):
            ret["pointer"] = p.number_phrase
        else:
            ret["pointer"] = syntax_node.ValueNode(None, int)
        ret["surface_type"] = syntax_node.ValueNode(p.SURFACE_TYPE, str, p.padding)
        ret["data"] = p.number_sequence
        return syntax_node.SyntaxNode("surface", ret)

    @_('"*" number_phrase', '"+" number_phrase', "number_phrase")
    def surface_id(self, p):
        ret = {}
        if p[0].value in {"*", "+"}:
            ret["modifier"] = syntax_node.ValueNode(p[0], str)
        else:
            ret["modifier"] = syntax_node.ValueNode(None, str)

        ret["number"] = p.number_phrase
        return syntax_node.SyntaxNode("surface_number", ret)

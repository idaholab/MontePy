from mcnpy.input_parser.parser_base import MCNP_Parser
from mcnpy.input_parser import syntax_node


class SurfaceParser(MCNP_Parser):
    @_(
        "surface_id SURFACE_TYPE padding number_sequence",
        "surface_id number_phrase SURFACE_TYPE padding number_sequence",
    )
    def surface(self, p):
        ret = {}
        ret["surface_num"] = p.surface_id
        if hasattr(p, "number_phrase"):
            ret["pointer"] = p.number_phrase
        ret["surface_type"] = syntax_node.ValueNode(p.SURFACE_TYPE, str, p.padding)
        ret["data"] = p.number_sequence
        return syntax_node.SyntaxNode("surface", ret)

    @_('"*" number_phrase', '"+" number_phrase', "number_phrase")
    def surface_id(self, p):
        ret = {}
        if p[0] in {"*", "+"}:
            ret["modifier"] = p[0]
        ret["number"] = p.number_phrase
        return syntax_node.SyntaxNode("surface_number", ret)

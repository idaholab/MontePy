from mcnpy.input_parser.parser_base import MCNP_Parser
from mcnpy.input_parser import semantic_node


class CellParser(MCNP_Parser):
    @_(
        "number_phrase material geometry_expr parameters",
        "number_phrase material geometry_expr",
    )
    def cell(self, p):
        dict_tree = {
            "cell_num": p.number_phrase,
            "material": p.material,
            "geometry": p.geometry_expr,
        }
        if len(p) == 4:
            dict_tree["parameters"] = p.parameters
        return semantic_node.SemanticNode("cell", dict_tree)

    @_("null_phrase", "number_phrase number_phrase")
    def material(self, p):
        if len(p) == 1:
            ret_dict = {"mat_number": p.null_phrase}
        else:
            ret_dict = {"mat_number": p[0], "density": p[1]}
        return semantic_node.SemanticNode("material", ret_dict)

    @_('":"')
    def union(self, p):
        return p

    @_("union padding")
    def union(self, p):
        return p

    @_("geometry_expr union geometry_term")
    def geometry_expr(self, p):
        return p

    @_("geometry_expr padding")
    def geometry_expr(self, p):
        return p

    @_("geometry_term")
    def geometry_expr(self, p):
        return p.geometry_term

    @_("geometry_term padding geometry_factor")
    def geometry_term(self, p):
        return p

    @_("geometry_term padding")
    def geometry_term(self, p):
        return p

    @_("geometry_factor")
    def geometry_term(self, p):
        return p.geometry_factor

    @_("geometry_factory")
    def geometry_factor(self, p):
        return p.geometry_factory

    @_("COMPLEMENT geometry_factory")
    def geometry_factor(self, p):
        return p

    @_("NUMBER")
    def geometry_factory(self, p):
        return p

    @_('"(" geometry_expr ")"')
    def geometry_factory(self, p):
        return p

    @_("KEYWORD PARTICLE_DESIGNATOR param_seperator number_phrase")
    def parameter(self, p):
        return p

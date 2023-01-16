from mcnpy.errors import *
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

    @_("number_phrase KEYWORD")
    def cell(self, p):
        if p.KEYWORD.lower() == "like":
            raise UnsupportedFeature("The like but feature is not supported")

    @_("null_phrase", "number_phrase number_phrase")
    def material(self, p):
        if len(p) == 1:
            ret_dict = {"mat_number": p.null_phrase}
        else:
            ret_dict = {"mat_number": p[0], "density": p[1]}
        return semantic_node.SemanticNode("material", ret_dict)

    @_('":"')
    def union(self, p):
        return semantic_node.PaddingNode(p[0])

    @_("union padding")
    def union(self, p):
        ret = p.union
        for node in p.padding.nodes:
            ret.append(node)
        return ret

    @_("geometry_expr union geometry_term")
    def geometry_expr(self, p):
        left = p.geometry_expr
        right = p.geometry_term
        return semantic_node.GeometryTree(
            "union", left.nodes + [p.union] + right.nodes, ":", left, right
        )

    @_("geometry_expr padding")
    def geometry_expr(self, p):
        ret = p.geometry_expr
        ret.append(p.padding)
        return ret

    @_("geometry_term")
    def geometry_expr(self, p):
        return p.geometry_term

    @_("geometry_term padding geometry_factor")
    def geometry_term(self, p):
        left = p.geometry_term
        right = p.geometry_factor
        return semantic_node.GeometryTree(
            "intersection", left.nodes + [p.padding] + right.nodes, "*", left, right
        )

    @_("geometry_term padding")
    def geometry_term(self, p):
        ret = p.geometry_term
        ret.append(p.padding)
        return ret

    @_("geometry_factor")
    def geometry_term(self, p):
        return p.geometry_factor

    @_("geometry_factory")
    def geometry_factor(self, p):
        return p.geometry_factory

    @_("COMPLEMENT geometry_factory")
    def geometry_factor(self, p):
        return semantic_node.GeometryTree(
            "complement",
            [p.COMPLEMENT] + p.geometry_factory.nodes,
            "#",
            p.geometry_factory,
        )

    @_("NUMBER")
    def geometry_factory(self, p):
        return semantic_node.ValueNode(p.NUMBER, float)

    @_('"(" geometry_expr ")"')
    def geometry_factory(self, p):
        ret = semantic_node.ListNode("geom parens")
        ret.append(p[0])
        for node in p.geometry_expr.nodes:
            ret.append(node)
        ret.append(p[2])
        return ret

    # support for fill card wierdness
    @_(
        'number_sequence "(" number_sequence ")"',
        'number_sequence "(" number_sequence ")" padding',
    )
    def number_sequence(self, p):
        sequence = p[0]
        for node in list(p)[1:]:
            sequence.append(node)
        return sequence

    @_("KEYWORD PARTICLE_DESIGNATOR param_seperator number_phrase")
    def parameter(self, p):
        return p

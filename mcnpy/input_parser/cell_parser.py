from mcnpy.errors import *
from mcnpy.input_parser.parser_base import MCNP_Parser
from mcnpy.input_parser import syntax_node


class CellParser(MCNP_Parser):
    debugfile = None

    # TODO implement doc parser meta class
    # TODO implement dictionary overloading
    @_(
        "identifier_phrase material geometry_expr parameters",
        "identifier_phrase material geometry_expr",
        "padding identifier_phrase material geometry_expr parameters",
        "padding identifier_phrase material geometry_expr",
    )
    def cell(self, p):
        dict_tree = {}
        if isinstance(p[0], syntax_node.PaddingNode):
            dict_tree["start_pad"] = p[0]
        else:
            dict_tree["start_pad"] = syntax_node.PaddingNode()

        dict_tree["cell_num"] = p.identifier_phrase
        dict_tree["material"] = p.material
        dict_tree["geometry"] = p.geometry_expr
        if hasattr(p, "parameters"):
            dict_tree["parameters"] = p.parameters
        else:
            dict_tree["parameters"] = syntax_node.ParametersNode()
        return syntax_node.SyntaxNode("cell", dict_tree)

    @_("number_phrase KEYWORD")
    def cell(self, p):
        if p.KEYWORD.lower() == "like":
            raise UnsupportedFeature("The like but feature is not supported")

    @_("null_ident_phrase", "identifier_phrase number_phrase")
    def material(self, p):
        if len(p) == 1:
            ret_dict = {"mat_number": p.null_ident_phrase}
        else:
            ret_dict = {"mat_number": p[0], "density": p[1]}
        return syntax_node.SyntaxNode("material", ret_dict)

    @_('":"')
    def union(self, p):
        return syntax_node.PaddingNode(p[0])

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
        return syntax_node.GeometryTree(
            "union", left.nodes + [p.union] + right.nodes, ":", left, right
        )

    @_("geometry_expr padding")
    def geometry_expr(self, p):
        ret = p.geometry_expr
        ret.append(p.padding)
        return ret

    @_("geometry_term")
    def geometry_expr(self, p):
        term = p.geometry_term
        if isinstance(term, syntax_node.ValueNode):
            term = syntax_node.GeometryTree("shift", term.nodes, ">", term)
        return term

    @_("geometry_term padding geometry_factor")
    def geometry_term(self, p):
        left = p.geometry_term
        right = p.geometry_factor
        return syntax_node.GeometryTree(
            "intersection", left.nodes + [p.padding] + right.nodes, "*", left, right
        )

    @_("geometry_term shortcut_sequence")
    def geometry_term(self, p):
        left = p.geometry_term
        for node in p.shortcut_sequence.nodes:
            new_tree = syntax_node.GeometryTree(
                "intersection", left.nodes + node.nodes, "*", left, node
            )
            left = new_tree
        return new_tree

    @_(
        "geometry_term REPEAT",
        "geometry_term MULTIPLY",
        "geometry_term INTERPOLATE padding number_phrase",
        "geometry_term LOG_INTERPOLATE padding number_phrase",
    )
    def geometry_term(self, p):
        shortcut = syntax_node.ShortcutNode(p)
        node_iter = iter(shortcut.nodes)
        left = next(node_iter)
        for node in node_iter:
            new_tree = syntax_node.GeometryTree(
                "intersection", left.nodes + node.nodes, "*", left, node
            )
            left = new_tree
        return new_tree

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
        return syntax_node.GeometryTree(
            "complement",
            [p.COMPLEMENT] + p.geometry_factory.nodes,
            "#",
            p.geometry_factory,
        )

    @_("NUMBER")
    def geometry_factory(self, p):
        return syntax_node.ValueNode(p.NUMBER, float)

    @_('"(" geometry_expr ")"', '"(" padding geometry_expr ")"')
    def geometry_factory(self, p):
        nodes = [p[0]]
        if hasattr(p, "padding"):
            nodes += p.padding.nodes
        nodes += p.geometry_expr.nodes + [p[-1]]
        return syntax_node.GeometryTree("geom parens", nodes, ">", p.geometry_expr)

    # support for fill card weirdness
    @_(
        'number_sequence "(" number_sequence ")"',
        'number_sequence "(" number_sequence ")" padding',
        'number_sequence ":" numerical_phrase',
    )
    def number_sequence(self, p):
        sequence = p[0]
        for node in list(p)[1:]:
            if isinstance(node, syntax_node.ListNode):
                for val in node.nodes:
                    sequence.append(val)
            elif isinstance(node, str):
                sequence.append(syntax_node.ValueNode(node, str))
            else:
                sequence.append(node)
        return sequence

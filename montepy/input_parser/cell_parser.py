# Copyright 2024, Battelle Energy Alliance, LLC All Rights Reserved.
from montepy.errors import *
from montepy.input_parser.parser_base import MCNP_Parser
from montepy.input_parser import syntax_node


class CellParser(MCNP_Parser):
    """
    The parser for parsing a Cell input.

    .. versionadded:: 0.2.0
        This was added with the major parser rework.

    :returns: a syntax tree of the cell.
    :rtype: SyntaxNode
    """

    debugfile = None

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

    @_(
        "null_ident_phrase",
        "identifier_phrase number_phrase",
        "identifier_phrase null_phrase",
    )
    def material(self, p):
        if len(p) == 1:
            ret_dict = {
                "mat_number": p.null_ident_phrase,
                "density": syntax_node.ValueNode(None, float),
            }
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
            is_comment = isinstance(node, syntax_node.CommentNode)
            ret.append(node, is_comment)
        return ret

    @_("geometry_expr union geometry_term")
    def geometry_expr(self, p):
        left = p.geometry_expr
        right = p.geometry_term
        nodes = {"left": left, "operator": p.union, "right": right}
        return syntax_node.GeometryTree("union", nodes, ":", left, right)

    @_("geometry_term")
    def geometry_expr(self, p):
        term = p.geometry_term
        if isinstance(term, syntax_node.ValueNode):
            term = syntax_node.GeometryTree("shift", {"left": term}, ">", term)
        return term

    # handle intersection
    @_("geometry_term padding geometry_factor")
    def geometry_term(self, p):
        left = p.geometry_term
        right = p.geometry_factor
        nodes = {"left": left, "operator": p.padding, "right": right}
        return syntax_node.GeometryTree("intersection", nodes, "*", left, right)

    # handle implicit intersection of: ( )( )
    @_("geometry_term geometry_factory")
    def geometry_term(self, p):
        left = p.geometry_term
        right = p.geometry_factory
        nodes = {"left": left, "operator": syntax_node.PaddingNode(), "right": right}
        return syntax_node.GeometryTree("intersection", nodes, "*", left, right)

    @_(
        "geometry_term NUM_REPEAT",
        "geometry_term REPEAT",
        "geometry_term NUM_MULTIPLY",
        "geometry_term MULTIPLY",
        "geometry_term NUM_INTERPOLATE padding number_phrase",
        "geometry_term INTERPOLATE padding number_phrase",
        "geometry_term NUM_LOG_INTERPOLATE padding number_phrase",
        "geometry_term LOG_INTERPOLATE padding number_phrase",
    )
    def geometry_term(self, p):
        shortcut = syntax_node.ShortcutNode(p, data_type=int)
        node_iter = iter(shortcut.nodes)
        if isinstance(p.geometry_term, syntax_node.GeometryTree):
            left = p.geometry_term
            left.mark_last_leaf_shortcut(shortcut.type)
        else:
            left = next(node_iter)
        left_type = None
        if isinstance(left, syntax_node.ValueNode) and left == shortcut.nodes[0]:
            left_type = shortcut.type
        for node in node_iter:
            new_tree = syntax_node.GeometryTree(
                "intersection",
                {"left": left, "operator": syntax_node.PaddingNode(), "right": node},
                "*",
                left,
                node,
                left_short_type=left_type,
                right_short_type=shortcut.type,
            )
            left = new_tree
        return new_tree

    @_("geometry_term padding")
    def geometry_term(self, p):
        ret = p.geometry_term
        if isinstance(ret, syntax_node.ValueNode):
            if ret.padding:
                ret.padding.append(p.padding)
            else:
                ret.padding = p.padding
        else:
            if "end_pad" in ret.nodes:
                ret.nodes["end_pad"] += p.padding
            else:
                ret.nodes["end_pad"] = p.padding
        return ret

    @_("geometry_factor")
    def geometry_term(self, p):
        return p.geometry_factor

    @_("geometry_factory")
    def geometry_factor(self, p):
        return p.geometry_factory

    @_("COMPLEMENT geometry_factory")
    def geometry_factor(self, p):
        nodes = {
            "operator": syntax_node.PaddingNode(p.COMPLEMENT),
            "left": p.geometry_factory,
        }
        return syntax_node.GeometryTree(
            "complement",
            nodes,
            "#",
            p.geometry_factory,
        )

    @_("NUMBER")
    def geometry_factory(self, p):
        return syntax_node.ValueNode(p.NUMBER, float)

    @_('"(" geometry_expr ")"', '"(" padding geometry_expr ")"')
    def geometry_factory(self, p):
        nodes = {
            "start_pad": syntax_node.PaddingNode(p[0]),
            "left": p.geometry_expr,
            "end_pad": syntax_node.PaddingNode(p[-1]),
        }
        if hasattr(p, "padding"):
            for node in p.padding.nodes:
                nodes["start_pad"].append(node)
        return syntax_node.GeometryTree("geom parens", nodes, "()", p.geometry_expr)

    # support for fill card weirdness
    @_(
        'number_sequence "(" number_sequence ")"',
        'number_sequence "(" padding number_sequence ")"',
        'number_sequence "(" number_sequence ")" padding',
        'number_sequence "(" padding number_sequence ")" padding',
        'number_sequence ":" numerical_phrase',
        'number_sequence ":" padding numerical_phrase',
        # support for TRCL syntax
        '"(" number_sequence ")"',
        '"(" number_sequence ")" padding',
        '"(" padding number_sequence ")" padding',
    )
    def number_sequence(self, p):
        if isinstance(p[0], str):
            sequence = syntax_node.ListNode("parenthetical statement")
            sequence.append(p[0])
        else:
            sequence = p[0]
        for node in list(p)[1:]:
            if isinstance(node, syntax_node.ListNode):
                for val in node.nodes:
                    sequence.append(val)
            elif isinstance(node, str):
                sequence.append(syntax_node.PaddingNode(node))
            else:
                sequence.append(node)
        return sequence

# Copyright 2024, Battelle Energy Alliance, LLC All Rights Reserved.
from montepy.exceptions import *
from montepy.input_parser.parser_base import MCNP_Parser
from montepy.input_parser import syntax_node


class CellParser(MCNP_Parser):
    """The parser for parsing a Cell input.

    Returns
    -------
    SyntaxNode
        a syntax tree of the cell.
    """

    debugfile = None

    @_(
        "identifier_phrase material geometry_expr cell_parameters",
        "identifier_phrase material geometry_expr",
        "padding identifier_phrase material geometry_expr cell_parameters",
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
        if hasattr(p, "cell_parameters"):
            dict_tree["parameters"] = p.cell_parameters
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

    @_(
        "parameter",
        "cell_param",
        "cell_parameters parameter",
        "cell_parameters cell_param",
    )
    def cell_parameters(self, p):
        """A list of the parameters (key, value pairs) for this input.

        Returns
        -------
        ParametersNode
            all parameters
        """
        if len(p) == 1:
            params = syntax_node.ParametersNode()
            param = p[0]
        else:
            params = p[0]
            param = p[1]
        params.append(param)
        return params

    @_(
        "classifier param_seperator cell_param_data",
    )
    def cell_param(self, p):
        """A singular Key-value pair.

        Returns
        -------
        SyntaxNode
            the parameter.
        """
        return syntax_node.SyntaxNode(
            p.classifier.prefix.value,
            {"classifier": p.classifier, "seperator": p.param_seperator, "data": p[2]},
        )

    @_("cell_fill", "transform")
    def cell_param_data(self, p):
        return p[0]

    @_(
        "numerical_phrase transform",
        "indices number_sequence",
        "indices number_sequence transform",
    )
    def cell_fill(self, p):
        """
        A fill parameter data in a cell.
        """
        tree = {}
        if hasattr(p, "indices"):
            tree["indices"] = p.indices
        else:
            tree["indices"] = syntax_node.ListNode("fill indices")
        if hasattr(p, "numerical_phrase"):
            unis = syntax_node.ListNode("fill universes")
            unis.append(p.numerical_phrase)
        else:
            unis = p.number_sequence
        tree["universes"] = unis
        if hasattr(p, "transform"):
            tree["transform"] = p.transform
        else:
            tree["transform"] = syntax_node.ListNode("fill transform")
        return syntax_node.SyntaxNode("cell fill", tree)

    @_("index_pair index_pair index_pair")
    def indices(self, p):
        ret = p[0]
        for lnode in list(p)[1:]:
            for node in lnode.nodes:
                ret.append(node)
        return ret

    @_('numerical_phrase ":" numerical_phrase')
    def index_pair(self, p):
        ret = syntax_node.ListNode("index list")
        for node in p:
            if isinstance(node, str):
                node = syntax_node.PaddingNode(node)
            ret.append(node)
        return ret

    @_("lparen_phrase number_sequence rparen_phrase")
    def transform(self, p):
        ret = syntax_node.ListNode("cell transform")
        for node in p:
            if isinstance(node, syntax_node.ListNode):
                for n in node.nodes:
                    ret.append(n)
            else:
                ret.append(node)
        return ret


class JitCellParser:

    @staticmethod
    def parse(tokenizer):
        for token in tokenizer:
            if token.type in {"SPACE", "COMMENT", "DOLLAR_COMMENT"}:
                continue
            elif token.type == "NUMBER":
                return syntax_node.SyntaxNode(
                    "jit_cell", {"number": syntax_node.ValueNode(token.value, int)}
                )
            else:
                assert False

# Copyright 2024, Battelle Energy Alliance, LLC All Rights Reserved.
from montepy.input_parser.data_parser import DataParser
from montepy.input_parser import syntax_node


class MaterialParser(DataParser):
    debugfile = None

    @_(
        "introduction isotopes",
        "introduction isotopes parameters",
    )
    def material(self, p):
        ret = {}
        for key, node in p.introduction.nodes.items():
            ret[key] = node
        ret["data"] = p.isotopes
        if hasattr(p, "parameters"):
            ret["parameters"] = p.parameters
        return syntax_node.SyntaxNode("data", ret)

    @_("isotope_fractions", "number_sequence", "isotope_hybrid_fractions")
    def isotopes(self, p):
        return p[0]

    @_("number_sequence isotope_fraction", "isotope_hybrid_fractions isotope_fraction")
    def isotope_hybrid_fractions(self, p):
        ret = p[0]
        for node in p.isotope_fraction[1:]:
            ret.append(node)
        return ret

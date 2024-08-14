# Copyright 2024, Battelle Energy Alliance, LLC All Rights Reserved.
import itertools

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
        if hasattr(p, "number_sequence"):
            return self._convert_to_isotope(p.number_sequence)
        return p[0]

    @_("number_sequence isotope_fraction", "isotope_hybrid_fractions isotope_fraction")
    def isotope_hybrid_fractions(self, p):
        if hasattr(p, "number_sequence"):
            ret = self._convert_to_isotope(p.number_sequence)
        else:
            ret = p[0]
        ret.append(p.isotope_fraction)
        return ret

    def _convert_to_isotope(self, old):
        new_list = syntax_node.IsotopesNode("converted isotopes")

        def batch_gen():
            it = iter(old)
            while batch := tuple(itertools.islice(it, 2)):
                yield batch

        for group in batch_gen():
            new_list.append(("foo", *group))
        return new_list

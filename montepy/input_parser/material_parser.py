# Copyright 2024, Battelle Energy Alliance, LLC All Rights Reserved.
import itertools

from montepy.input_parser.data_parser import DataParser
from montepy.input_parser import syntax_node


class MaterialParser(DataParser):
    debugfile = None

    @_(
        "introduction isotopes",
        "introduction isotopes parameters",
        "introduction isotopes mat_parameters",
    )
    def material(self, p):
        ret = {}
        for key, node in p.introduction.nodes.items():
            ret[key] = node
        ret["data"] = p.isotopes
        if len(p) > 2:
            ret["parameters"] = p[2]
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

    @_(
        "mat_parameter",
        "parameter",
        "mat_parameters mat_parameter",
        "mat_parameters parameter",
    )
    def mat_parameters(self, p):
        """
        A list of the parameters (key, value pairs) that allows material libraries.

        :returns: all parameters
        :rtype: ParametersNode
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
        "classifier param_seperator library",
    )
    def mat_parameter(self, p):
        """
        A singular Key-value pair that includes a material library.

        :returns: the parameter.
        :rtype: SyntaxNode
        """
        return syntax_node.SyntaxNode(
            p.classifier.prefix.value,
            {"classifier": p.classifier, "seperator": p.param_seperator, "data": p[2]},
        )

    @_("NUMBER_WORD")
    @_("NUMBER_WORD padding")
    def library(self, p):
        """
        A library name.
        """
        return self._flush_phrase(p, str)

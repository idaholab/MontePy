# Copyright 2024, Battelle Energy Alliance, LLC All Rights Reserved.
import itertools

from montepy.input_parser.data_parser import DataParser
from montepy.input_parser import syntax_node


class MaterialParser(DataParser):
    debugfile = None

    @_(
        "introduction mat_data",
    )
    def material(self, p):
        ret = {}
        for key, node in p.introduction.nodes.items():
            ret[key] = node
        ret["data"] = p.mat_data
        return syntax_node.SyntaxNode("data", ret)
    
    @_("mat_datum", "mat_data mat_datum")
    def mat_data(self, p):
        if len(p) == 1:
            ret = syntax_node.MaterialsNode("mat stuff")
        else:
            ret = p.mat_data
        ret.append(p.mat_datum)
        return ret

    @_("isotope_fraction", "number_sequence", "parameter", "mat_parameter")
    def mat_datum(self, p):
        return p
    
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

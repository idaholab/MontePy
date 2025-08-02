# Copyright 2024, Battelle Energy Alliance, LLC All Rights Reserved.
import itertools

from montepy.input_parser.data_parser import DataParser
from montepy.input_parser import syntax_node


class MaterialParser(DataParser):
    debugfile = None

    @_(
        "classifier_phrase mat_data",
        "padding classifier_phrase mat_data",
    )
    def material(self, p):
        ret = {}
        if isinstance(p[0], syntax_node.PaddingNode):
            ret["start_pad"] = p.padding
        else:
            ret["start_pad"] = syntax_node.PaddingNode()
        ret["classifier"] = p.classifier_phrase
        ret["data"] = p.mat_data
        return syntax_node.SyntaxNode("data", ret)

    @_("mat_datum", "mat_data mat_datum")
    def mat_data(self, p):
        if len(p) == 1:
            ret = syntax_node.MaterialsNode("mat stuff")
        else:
            ret = p.mat_data
        datum = p.mat_datum
        if isinstance(datum, tuple):
            ret.append_nuclide(datum)
        elif isinstance(datum, syntax_node.ListNode):
            [ret.append_nuclide(n) for n in self._convert_to_isotope(datum)]
        else:
            ret.append_param(datum)
        return ret

    def _convert_to_isotope(self, old):
        new_list = []

        def batch_gen():
            it = iter(old)
            while batch := tuple(itertools.islice(it, 2)):
                yield batch

        for group in batch_gen():
            if group[0].type != str:
                group[0].convert_to_str()
            new_list.append(("foo", *group))
        return new_list

    @_("isotope_fraction", "even_number_sequence", "parameter", "mat_parameter")
    def mat_datum(self, p):
        return p[0]

    @_(
        "classifier param_seperator library",
    )
    def mat_parameter(self, p):
        """A singular Key-value pair that includes a material library.

        Returns
        -------
        SyntaxNode
            the parameter.
        """
        return syntax_node.SyntaxNode(
            p.classifier.prefix.value,
            {"classifier": p.classifier, "seperator": p.param_seperator, "data": p[2]},
        )

    @_("NUMBER_WORD")
    @_("NUMBER_WORD padding")
    def library(self, p):
        """A library name."""
        return self._flush_phrase(p, str)

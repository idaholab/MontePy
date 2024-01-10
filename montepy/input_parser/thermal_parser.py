# Copyright 2024, Battelle Energy Alliance, LLC All Rights Reserved.
from montepy.input_parser.data_parser import DataParser
from montepy.input_parser import syntax_node


class ThermalParser(DataParser):
    """
    A parser for thermal scattering law inputs.

    .. versionadded:: 0.2.0
        This was added with the major parser rework.

    :rtype: SyntaxNode
    """

    debugfile = None

    @_("introduction thermal_law_sequence")
    def thermal_mat(self, p):
        ret = {}
        for key, node in p.introduction.nodes.items():
            ret[key] = node
        ret["data"] = p.thermal_law_sequence
        return syntax_node.SyntaxNode("thermal scattering", ret)

    @_("thermal_law", "thermal_law_sequence thermal_law")
    def thermal_law_sequence(self, p):
        if len(p) == 1:
            sequence = syntax_node.ListNode("thermal law sequence")
            sequence.append(p[0])
        else:
            sequence = p[0]
            sequence.append(p[1])
        return sequence

    @_("THERMAL_LAW", "THERMAL_LAW padding")
    def thermal_law(self, p):
        return self._flush_phrase(p, str)

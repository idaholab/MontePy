from mcnpy.input_parser.data_parser import DataParser
from mcnpy.input_parser import syntax_node


class ThermalParser(DataParser):
    """
    A parser for thermal scattering law inputs.

    .. versionadded:: 0.2.0
        This was added with the major parser rework.

    :rtype: SyntaxNode
    """

    debugfile = None

    @_("classifier_phrase thermal_law_sequence")
    def thermal_mat(self, p):
        return syntax_node.SyntaxNode(
            "thermal scattering",
            {"classifier": p.classifier_phrase, "data": p.thermal_law_sequence},
        )

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

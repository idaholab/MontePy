from mcnpy.errors import *
from mcnpy.input_parser.parser_base import MCNP_Parser, MetaBuilder
from mcnpy.input_parser import syntax_node


class DataParser(MCNP_Parser):
    debugfile = None

    @_(
        "introduction data",
        "introduction data parameters",
    )
    def data_input(self, p):
        ret = {}
        for key, node in p.introduction.nodes.items():
            ret[key] = node
        ret["data"] = p.data
        if hasattr(p, "parameters"):
            ret["parameters"] = p.parameters
        return syntax_node.SyntaxNode("data", ret)

    @_(
        "classifier_phrase",
        "classifier_phrase KEYWORD padding",
        "padding classifier_phrase",
        "padding classifier_phrase KEYWORD padding",
    )
    def introduction(self, p):
        ret = {}
        if isinstance(p[0], syntax_node.PaddingNode):
            ret["start_pad"] = p[0]
        ret["classifier"] = p.classifier_phrase
        if hasattr(p, "KEYWORD"):
            ret["keyword"] = syntax_node.ValueNode(p.KEYWORD, str, padding=p[-1])
        return syntax_node.SyntaxNode("data intro", ret)

    @_("number_sequence", "isotope_fractions")
    def data(self, p):
        return p[0]

    @_("zaid_phrase number_phrase")
    def isotope_fraction(self, p):
        return p

    @_("isotope_fraction", "isotope_fractions isotope_fraction")
    def isotope_fractions(self, p):
        if hasattr(p, "isotope_fractions"):
            fractions = p.isotope_fractions
        else:
            fractions = syntax_node.IsotopesNode("isotope list")
        fractions.append(p.isotope_fraction)
        return fractions

    @_("ZAID padding")
    def zaid_phrase(self, p):
        return self._flush_phrase(p, str)

    @_("KEYWORD param_seperator NUMBER text_phrase")
    def parameter(self, p):
        return p


class ClassifierParser(DataParser):
    debugfile = None

    @_("classifier")
    def data_classifier(self, p):
        return syntax_node.SyntaxNode(
            "data input classifier", {"classifier": p.classifier}
        )

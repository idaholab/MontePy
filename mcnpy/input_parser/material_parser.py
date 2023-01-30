from mcnpy.input_parser.data_parser import DataParser
from mcnpy.input_parser import syntax_node


class MaterialParser(DataParser):
    @_("classifier isotope_fractions", "classifier isotope_fractions parameters")
    def material(self, p):
        ret = {"classifier": p.classifier, "isotope_fractions": p.isotope_fractions}
        if hasattr(p, "parameters"):
            ret["parameters"] = p.parameters
        return syntax_node.SyntaxNode("material", ret)

    @_("KEYWORD param_seperator NUMBER text_phrase")
    def parameter(self, p):
        return p

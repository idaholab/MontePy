from mcnpy.errors import *
from mcnpy.input_parser.parser_base import MCNP_Parser, MetaBuilder
from mcnpy.input_parser import syntax_node


class DataParser(MCNP_Parser):
    @_(
        "classifier_phrase number_sequence",
        "classifier_phrase KEYWORD padding number_sequence",
        "classifier_phrase isotope_fractions",
        "data_input parameters",
    )
    def data_input(self, p):
        if "data_input" in p:
            ret = p.data_input
            ret.nodes["parameters"] = p.parameters
        else:
            ret = syntax_node.SyntaxNode("data input", {})
        if hasattr(p, "classifier_phrase"):
            ret.nodes["classifier"] = p.classifier_phrase
            if hasattr(p, "KEYWORD"):
                ret.nodes["keyword"] = syntax_node.ValueNode(
                    p.KEYWORD, str, padding=p.padding
                )
            if hasattr(p, "number_sequence"):
                ret.nodes["data"] = p.number_sequence
            else:
                ret.nodes["data"] = p.isotope_fractions
        return ret

    @_(
        "modifier classifier",
        "TEXT",
        "KEYWORD",
        "classifier NUMBER",
        "classifier PARTICLE_DESIGNATOR",
    )
    def classifier(self, p):
        if hasattr(p, "classifier"):
            classifier = p.classifier
        else:
            classifier = syntax_node.ClassifierNode()

        if hasattr(p, "modifier"):
            classifier.modifier = syntax_node.ValueNode(p.modifier, str)
        if hasattr(p, "TEXT") or hasattr(p, "KEYWORD"):
            if hasattr(p, "TEXT"):
                text = p.TEXT
            else:
                text = p.KEYWORD
            classifier.prefix = syntax_node.ValueNode(text, str)
        if hasattr(p, "NUMBER"):
            classifier.number = syntax_node.ValueNode(p.NUMBER, int)
        if hasattr(p, "PARTICLE_DESIGNATOR"):
            classifier.particles = syntax_node.ParticleNode(
                "data particles", p.PARTICLE_DESIGNATOR
            )

        return classifier

    @_("classifier padding")
    def classifier_phrase(self, p):
        classifier = p.classifier
        classifier.padding = p.padding
        return classifier

    @_('"*"')
    def modifier(self, p):
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
    @_("classifier")
    def data_classifier(self, p):
        return syntax_node.SyntaxNode(
            "data input classifier", {"classifier": p.classifier}
        )

from mcnpy.errors import *
from mcnpy.input_parser.parser_base import MCNP_Parser, MetaBuilder
from mcnpy.input_parser import semantic_node


class DataParser(MCNP_Parser, metaclass=MetaBuilder):
    @_(
        "classifier number_sequence",
        "classifier isotope_fractions",
        "data_input parameters",
    )
    def data_input(self, p):
        if "data_input" in p:
            ret = p.data_input
            ret.nodes["parameters"] = p.parameters
        else:
            ret = semantic_node.SemanticNode("data input", {})
        if "classifier" in p:
            ret.nodes["classifier"] = p.classifier
            ret.nodes["data"] = p[1]
        return p

    @_(
        "modifier TEXT",
        "TEXT",
        "classifier NUMBER",
        "classifier PARTICLE_DESIGNATOR",
        "classifier padding",
    )
    def classifier(self, p):
        if "classifier" in p:
            classifier = p.classifier
        else:
            classifier = semantic_node.ClassifierNode()

        if "modifier" in p:
            classifier.modifier = semantic_node.ValueNode(p.modifier, str)
        if "TEXT" in p:
            classifier.prefix = semantic_node.ValueNode(p.TEXT, str)
        if "NUMBER" in p:
            classifier.number = semantic_node.ValueNode(p.NUMBER, int)
        if "PARTICLE_DESIGNATOR" in p:
            classifier.particles = semantic_node.ParticleNode(
                "data particles", p.PARTICLE_DESIGNATOR
            )
        if "padding" in p:
            classifier.append(p.padding)

        return classifier

    @_('"*"')
    def modifier(self, p):
        return p[0]

    @_("zaid_phrase number_phrase")
    def isotope_fraction(self, p):
        return p

    @_("isotope_fraction", "isotope_fractions isotope_fraction")
    def isotope_fractions(self, p):
        return p

    @_("ZAID padding")
    def zaid_phrase(self, p):
        return p

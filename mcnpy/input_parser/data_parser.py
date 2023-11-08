from mcnpy.errors import *
from mcnpy.input_parser.parser_base import MCNP_Parser, MetaBuilder
from mcnpy.input_parser import syntax_node


class DataParser(MCNP_Parser):
    """
    A parser for almost all data inputs.

    .. versionadded:: 0.2.0
        This was added with the major parser rework.

    :returns: a syntax tree for the data input.
    :rtype: SyntaxNode
    """

    debugfile = None

    @_(
        "introduction",
        "introduction data",
        "introduction data parameters",
        "introduction parameters",
    )
    def data_input(self, p):
        ret = {}
        for key, node in p.introduction.nodes.items():
            ret[key] = node
        if hasattr(p, "data"):
            ret["data"] = p.data
        else:
            ret["data"] = syntax_node.ListNode("empty data")
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
        else:
            ret["start_pad"] = syntax_node.PaddingNode()
        ret["classifier"] = p.classifier_phrase
        if hasattr(p, "KEYWORD"):
            ret["keyword"] = syntax_node.ValueNode(p.KEYWORD, str, padding=p[-1])
        else:
            ret["keyword"] = syntax_node.ValueNode(None, str, padding=None)
        return syntax_node.SyntaxNode("data intro", ret)

    @_(
        "number_sequence",
        "isotope_fractions",
        "particle_sequence",
        "text_sequence",
        "kitchen_sink",
    )
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

    @_("ZAID", "ZAID padding")
    def zaid_phrase(self, p):
        return self._flush_phrase(p, str)

    @_("particle_phrase", "particle_sequence particle_phrase")
    def particle_sequence(self, p):
        if len(p) == 1:
            sequence = syntax_node.ListNode("particle sequence")
            sequence.append(p[0])
        else:
            sequence = p[0]
            sequence.append(p[1])
        return sequence

    @_("PARTICLE", "SURFACE_TYPE", "PARTICLE_SPECIAL")
    def particle_text(self, p):
        return p[0]

    @_("particle_text padding", "particle_text")
    def particle_phrase(self, p):
        return self._flush_phrase(p, str)

    @_("LIBRARY_SUFFIX", "LIBRARY_SUFFIX padding")
    def text_phrase(self, p):
        self._flush_phrase(p, str)

    @_("text_phrase", "text_sequence text_phrase")
    def text_sequence(self, p):
        if len(p) == 1:
            sequence = syntax_node.ListNode("text sequence")
            sequence.append(p[0])
        else:
            sequence = p[0]
            sequence.append(p[1])
        return sequence

    @_("kitchen_junk", "kitchen_sink kitchen_junk")
    def kitchen_sink(self, p):
        sequence = p[0]
        if len(p) != 1:
            for node in p[1].nodes:
                sequence.append(node)
        return sequence

    @_("number_sequence", "text_sequence", "particle_sequence")
    def kitchen_junk(self, p):
        return p[0]

    @_("classifier param_seperator NUMBER text_phrase")
    def parameter(self, p):
        return syntax_node.SyntaxNode(
            p.classifier.prefix.value,
            {
                "classifier": p.classifier,
                "seperator": p.param_seperator,
                "data": syntax_node.ValueNode(p.NUMBER + p.text_phrase, str),
            },
        )


class ClassifierParser(DataParser):
    """
    A parser for parsing the first word or classifier of a data input.

    .. versionadded:: 0.2.0
        This was added with the major parser rework.

    :returns: the classifier of the data input.
    :rtype: ClassifierNode
    """

    debugfile = None

    @_("classifier", "padding classifier")
    def data_classifier(self, p):
        if hasattr(p, "padding"):
            padding = p.padding
        else:
            padding = syntax_node.PaddingNode(None)
        return syntax_node.SyntaxNode(
            "data input classifier", {"start_pad": padding, "classifier": p.classifier}
        )

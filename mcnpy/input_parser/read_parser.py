from mcnpy.input_parser.parser_base import MCNP_Parser
from mcnpy.input_parser import syntax_node


class ReadParser(MCNP_Parser):
    debugfile = None
    dont_copy = {"parameter"}

    @_("KEYWORD padding parameters", "padding KEYWORD padding parameters")
    def read_input(self, p):
        if isinstance(p[0], syntax_node.PaddingNode):
            start_pad = p[0]
        else:
            start_pad = syntax_node.PaddingNode()
        if p.KEYWORD.lower() == "read":
            return syntax_node.SyntaxNode(
                "read",
                {
                    "start_pad": start_pad,
                    "keyword": p.KEYWORD,
                    "padding": p.padding,
                    "parameters": p.parameters,
                },
            )
        else:
            return False

    @_(
        "classifier param_seperator file_phrase",
    )
    def parameter(self, p):
        return syntax_node.SyntaxNode(
            p.classifier.prefix.value,
            {"classifier": p.classifier, "seperator": p.param_seperator, "data": p[2]},
        )

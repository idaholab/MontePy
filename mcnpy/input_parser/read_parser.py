from mcnpy.input_parser.parser_base import MCNP_Parser
from mcnpy.input_parser import syntax_node


class ReadParser(MCNP_Parser):
    debugfile = None

    @_("KEYWORD padding parameters")
    def read_input(self, p):
        if p.KEYWORD.lower() == "read":
            return syntax_node.SyntaxNode(
                "read",
                {
                    "keyword": p.KEYWORD,
                    "padding": p.padding,
                    "parameters": p.parameters,
                },
            )
        else:
            return False

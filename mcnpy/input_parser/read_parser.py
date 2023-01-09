from mcnpy.input_parser.parser_base import MCNP_Parser
from mcnpy.input_parser import semantic_node


class ReadParser(MCNP_Parser):
    @_("KEYWORD padding parameters")
    def read_input(self, p):
        if p.KEYWORD.lower() == "read":

            return semantic_node.SemanticNode("read", p)
        else:
            return False

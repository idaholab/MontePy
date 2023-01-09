from mcnpy.input_parser.parser_base import MCNP_Parser


class ReadParser(MCNP_Parser):
    @_("KEYWORD padding parameters")
    def read_input(self, p):
        if p.KEYWORD.lower() == "read":
            return p
        else:
            return False

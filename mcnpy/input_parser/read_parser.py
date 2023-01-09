from mcnpy.input_parser.parser_base import MCNP_Parser


class ReadParser(MCNP_Parser):
    @_("KEYWORD seen_keyword padding parameters")
    def read(self, p):
        if p.KEYWORD.value.lower() == "read":
            return p
        else:
            return False

from mcnpy.input_parser.tokens import MCNP_Lexer
from sly import Parser


class CellParser(Parser):
    tokens = MCNP_Lexer.tokens
    debugfile = "parser.out"

    @_("int_phrase material")
    def cell(self, p):
        return p

    @_("NULL SPACE")
    def material(self, p):
        return p

    @_("int_phrase float_phrase")
    def material(self, p):
        return p

    @_("INT padding")
    def int_phrase(self, p):
        return p

    @_("FLOAT padding")
    def float_phrase(self, p):
        return p

    @_("SPACE")
    def padding(self, p):
        return p

    @_("padding SPACE")
    def padding(self, p):
        return p

    @_("padding DOLLAR_COMMENT")
    def padding(self, p):
        return p

    @_("padding COMMENT")
    def padding(self, p):
        return p

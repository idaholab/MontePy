from mcnpy.input_parser.tokens import MCNP_Lexer
from sly import Parser
import sly

_dec = sly.yacc._decorator


class MetaBuilder(sly.yacc.ParserMeta):
    protected_names = {
        "debugfile",
        "errok",
        "error",
        "index_position",
        "line_position",
        "log",
        "parse",
        "restart",
        "tokens",
    }

    def __new__(meta, classname, bases, attributes):
        if classname != "MCNP_Parser":
            for attr_name in dir(MCNP_Parser):
                if (
                    not attr_name.startswith("_")
                    and attr_name not in MetaBuilder.protected_names
                ):
                    print(attr_name)
                    func = getattr(MCNP_Parser, attr_name)
                    attributes[attr_name] = func
        cls = super().__new__(meta, classname, bases, attributes)
        return cls


class MCNP_Parser(Parser, metaclass=MetaBuilder):
    tokens = MCNP_Lexer.tokens

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

    @_("padding #")
    def padding(self, p):
        return p


class CellParser(MCNP_Parser):
    @_("int_phrase material")
    def cell(self, p):
        return p

    @_("NULL SPACE")
    def material(self, p):
        return p

    @_("int_phrase float_phrase")
    def material(self, p):
        return p

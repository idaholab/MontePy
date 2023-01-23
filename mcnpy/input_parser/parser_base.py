from mcnpy.input_parser.tokens import MCNP_Lexer
from mcnpy.input_parser import syntax_node
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
            for basis in bases:
                MetaBuilder._flatten_rules(classname, basis, attributes)
        cls = super().__new__(meta, classname, bases, attributes)
        return cls

    @staticmethod
    def _flatten_rules(classname, basis, attributes):
        for attr_name in dir(basis):
            if (
                not attr_name.startswith("_")
                and attr_name not in MetaBuilder.protected_names
            ):
                func = getattr(basis, attr_name)
                attributes[attr_name] = func
        parent = basis.__bases__
        for par_basis in parent:
            if par_basis != Parser:
                return
                MetaBuilder._flatten_rules(classname, par_basis, attributes)


class MCNP_Parser(Parser, metaclass=MetaBuilder):
    tokens = MCNP_Lexer.tokens

    @_("NUMBER", "NUMBER padding")
    def number_phrase(self, p):
        return self._flush_phrase(p, float)

    @_("NUMBER", "NUMBER padding")
    def identifier_phrase(self, p):
        return self._flush_phrase(p, int)

    @_(
        "number_phrase",
        "null_phrase",
        "shortcut_sequence",
        "number_sequence number_phrase",
        "number_sequence number_sequence",
        "number_sequence null_phrase",
    )
    def number_sequence(self, p):
        if len(p) == 1:
            sequence = syntax_node.ListNode("number sequence")
            sequence.append(p[0])
        else:
            sequence = p[0]
            sequence.append(p[1])
        return sequence

    @_(
        "number_phrase REPEAT",
        "number_phrase NUMBER MULTIPLY",
        "number_phrase INTERPOLATE number_phrase",
        "number_phrase LOG_INTERPOLATE number_phrase",
        "JUMP",
    )
    def shortcut_sequence(self, p):
        return syntax_node.ShortcutNode(p)

    @_("NULL", "NULL padding")
    def null_phrase(self, p):
        return self._flush_phrase(p, float)

    @_("NULL", "NULL padding")
    def null_ident_phrase(self, p):
        return self._flush_phrase(p, int)

    @_("TEXT", "TEXT padding")
    def text_phrase(self, p):
        return self._flush_phrase(p, str)

    def _flush_phrase(self, p, token_type):
        if len(p) > 1:
            padding = p[1]
        else:
            padding = None
        return syntax_node.ValueNode(p[0], token_type, padding)

    @_("SPACE")
    def padding(self, p):
        return syntax_node.PaddingNode(p.SPACE)

    @_("padding SPACE", "padding DOLLAR_COMMENT", "padding COMMENT", 'padding "&"')
    def padding(self, p):
        p[0].append(p[1])
        return p[0]

    @_('"="', "padding", '"=" padding')
    def param_seperator(self, p):
        return self._flush_phrase(p, str)

    @_(
        "KEYWORD param_seperator number_sequence",
        "KEYWORD param_seperator text_phrase",
    )
    def parameter(self, p):
        return p

    @_("parameter", "parameters parameter")
    def parameters(self, p):
        if len(p) == 1:
            params = syntax_node.ParametersNode()
            param = p[0]
        else:
            params = p[0]
            param = p[1]
        params.append(*param[1:])
        return params

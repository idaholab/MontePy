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
        "dont_copy",
    }

    # TODO support function overloading
    def __new__(meta, classname, bases, attributes):
        if classname != "MCNP_Parser":
            for basis in bases:
                MetaBuilder._flatten_rules(classname, basis, attributes)
        cls = super().__new__(meta, classname, bases, attributes)
        return cls

    # TODO use special dict allowing overloading
    @staticmethod
    def _flatten_rules(classname, basis, attributes):
        for attr_name in dir(basis):
            if (
                not attr_name.startswith("_")
                and attr_name not in MetaBuilder.protected_names
                and attr_name not in attributes.get("dont_copy", set())
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
    debugfile = None

    @_("NUMBER", "NUMBER padding")
    def number_phrase(self, p):
        return self._flush_phrase(p, float)

    @_("NUMBER", "NUMBER padding")
    def identifier_phrase(self, p):
        return self._flush_phrase(p, int)

    @_(
        "number_phrase",
        "null_phrase",
        "shortcut_phrase",
        "number_sequence number_phrase",
        "number_sequence shortcut_phrase",
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

    @_("number_phrase", "null_phrase")
    def numerical_phrase(self, p):
        return p[0]

    @_(
        "numerical_phrase REPEAT",
        "numerical_phrase MULTIPLY",
        "numerical_phrase INTERPOLATE padding number_phrase",
        "numerical_phrase LOG_INTERPOLATE padding number_phrase",
        "JUMP",
    )
    def shortcut_sequence(self, p):
        return syntax_node.ShortcutNode(p)

    @_("shortcut_sequence", "shortcut_sequence padding")
    def shortcut_phrase(self, p):
        sequence = p.shortcut_sequence
        if len(p) == 2:
            sequence.end_padding = p.padding
        return sequence

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

    @_("SPACE", "DOLLAR_COMMENT", "COMMENT")
    def padding(self, p):
        if hasattr(p, "DOLLAR_COMMENT") or hasattr(p, "COMMENT"):
            is_comment = True
        else:
            is_comment = False
        return syntax_node.PaddingNode(p[0], is_comment)

    @_("padding SPACE", "padding DOLLAR_COMMENT", "padding COMMENT", 'padding "&"')
    def padding(self, p):
        if hasattr(p, "DOLLAR_COMMENT") or hasattr(p, "COMMENT"):
            is_comment = True
        else:
            is_comment = False
        p[0].append(p[1], is_comment)
        return p[0]

    @_("parameter", "parameters parameter")
    def parameters(self, p):
        if len(p) == 1:
            params = syntax_node.ParametersNode()
            param = p[0]
        else:
            params = p[0]
            param = p[1]
        params.append(param)
        return params

    @_(
        "classifier param_seperator number_sequence",
        "classifier param_seperator text_phrase",
        "classifier param_seperator file_phrase",
    )
    def parameter(self, p):
        return syntax_node.SyntaxNode(
            p.classifier.prefix.value,
            {"classifier": p.classifier, "seperator": p.param_seperator, "data": p[2]},
        )

    @_("TEXT", "FILE_PATH", "file_name TEXT", "file_name FILE_PATH")
    def file_name(self, p):
        ret = p[0]
        if len(p) > 1:
            ret += p[1]
        return ret

    @_("file_name", "file_name padding")
    def file_phrase(self, p):
        return self._flush_phrase(p, str)

    @_('"="', "padding", '"=" padding')
    def param_seperator(self, p):
        return self._flush_phrase(p, str)

    @_(
        "modifier classifier",
        "TEXT",
        "KEYWORD",
        "PARTICLE",
        "classifier NUMBER",
        "classifier PARTICLE_DESIGNATOR",
    )
    def classifier(self, p):
        if hasattr(p, "classifier"):
            classifier = p.classifier
        else:
            classifier = syntax_node.ClassifierNode()

        if hasattr(p, "modifier"):
            classifier.modifier = syntax_node.ValueNode(p.modifier, str)
        if hasattr(p, "TEXT") or hasattr(p, "KEYWORD") or hasattr(p, "PARTICLE"):
            if hasattr(p, "TEXT"):
                text = p.TEXT
            elif hasattr(p, "KEYWORD"):
                text = p.KEYWORD
            else:
                text = p.PARTICLE
            classifier.prefix = syntax_node.ValueNode(text, str)
        if hasattr(p, "NUMBER"):
            classifier.number = syntax_node.ValueNode(p.NUMBER, int)
        if hasattr(p, "PARTICLE_DESIGNATOR"):
            classifier.particles = syntax_node.ParticleNode(
                "data particles", p.PARTICLE_DESIGNATOR
            )

        return classifier

    @_("classifier padding")
    def classifier_phrase(self, p):
        classifier = p.classifier
        classifier.padding = p.padding
        return classifier

    @_('"*"', "PARTICLE_SPECIAL")
    def modifier(self, p):
        if hasattr(p, "PARTICLE_SPECIAL"):
            if p.PARTICLE_SPECIAL == "*":
                return "*"
        return p[0]

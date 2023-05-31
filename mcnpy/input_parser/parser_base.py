from mcnpy.input_parser.tokens import MCNP_Lexer
from mcnpy.input_parser import syntax_node
from sly import Parser
import sly

_dec = sly.yacc._decorator


class MetaBuilder(sly.yacc.ParserMeta):
    """
    Custom MetaClass for allowing subclassing of MCNP_Parser.

    Note: overloading functions is not allowed.
    """

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
    """
    Base class for all MCNP parsers that provides basics.
    """

    tokens = MCNP_Lexer.tokens
    debugfile = None

    precedence = (("left", SPACE), ("left", TEXT))

    @_("NUMBER", "NUMBER padding")
    def number_phrase(self, p):
        """
        A non-zero number with or without padding.

        :returns: a float ValueNode
        :rtype: ValueNode
        """
        return self._flush_phrase(p, float)

    @_("NUMBER", "NUMBER padding")
    def identifier_phrase(self, p):
        """
        A non-zero number with or without padding converted to int.

        :returns: an int ValueNode
        :rtype: ValueNode
        """
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
        """
        A list of numbers.

        :rtype: ListNode
        """
        if len(p) == 1:
            sequence = syntax_node.ListNode("number sequence")
            if isinstance(p[0], syntax_node.ListNode):
                return p[0]
            sequence.append(p[0])
        else:
            sequence = p[0]
            if type(p[1]) == syntax_node.ListNode:
                for node in p[1].nodes:
                    sequence.append(node)
            else:
                sequence.append(p[1])
        return sequence

    @_("number_phrase", "null_phrase")
    def numerical_phrase(self, p):
        """
        Any number, including 0, with its padding.

        :returns: a float ValueNode
        :rtype: ValueNode
        """
        return p[0]

    @_("numerical_phrase", "shortcut_phrase")
    def shortcut_start(self, p):
        return p[0]

    @_(
        "shortcut_start REPEAT",
        "shortcut_start MULTIPLY",
        "shortcut_start INTERPOLATE padding number_phrase",
        "shortcut_start LOG_INTERPOLATE padding number_phrase",
        "JUMP",
    )
    def shortcut_sequence(self, p):
        """
        A shortcut (repeat, multiply, interpolate, or jump).

        :returns: the parsed shortcut.
        :rtype: ShortcutNode
        """
        short_cut = syntax_node.ShortcutNode(p)
        if isinstance(p[0], syntax_node.ShortcutNode):
            list_node = syntax_node.ListNode("next_shortcuts")
            list_node.append(p[0])
            list_node.append(short_cut)
            return list_node
        return short_cut

    @_("shortcut_sequence", "shortcut_sequence padding")
    def shortcut_phrase(self, p):
        """
        A complete shortcut, which should be used, and not shortcut_sequence.

        :returns: the parsed shortcut.
        :rtype: ShortcutNode
        """
        sequence = p.shortcut_sequence
        if len(p) == 2:
            sequence.end_padding = p.padding
        return sequence

    @_("NULL", "NULL padding")
    def null_phrase(self, p):
        """
        A zero number with or without its padding.

        :returns: a float ValueNode
        :rtype: ValueNode
        """
        return self._flush_phrase(p, float)

    @_("NULL", "NULL padding")
    def null_ident_phrase(self, p):
        """
        A zero number with or without its padding, for identification.

        :returns: an int ValueNode
        :rtype: ValueNode
        """
        return self._flush_phrase(p, int)

    @_("TEXT", "TEXT padding")
    def text_phrase(self, p):
        """
        A string with or without its padding.

        :returns: a str ValueNode.
        :rtype: ValueNode
        """
        return self._flush_phrase(p, str)

    def _flush_phrase(self, p, token_type):
        """
        Creates a ValueNode.
        """
        if len(p) > 1:
            padding = p[1]
        else:
            padding = None
        return syntax_node.ValueNode(p[0], token_type, padding)

    @_("SPACE", "DOLLAR_COMMENT", "COMMENT")
    def padding(self, p):
        """
        Anything that is not semantically significant: white space, and comments.

        :returns: All sequential padding.
        :rtype: PaddingNode
        """
        if hasattr(p, "DOLLAR_COMMENT") or hasattr(p, "COMMENT"):
            is_comment = True
        else:
            is_comment = False
        return syntax_node.PaddingNode(p[0], is_comment)

    @_("padding SPACE", "padding DOLLAR_COMMENT", "padding COMMENT", 'padding "&"')
    def padding(self, p):
        """
        Anything that is not semantically significant: white space, and comments.

        :returns: All sequential padding.
        :rtype: PaddingNode
        """
        if hasattr(p, "DOLLAR_COMMENT") or hasattr(p, "COMMENT"):
            is_comment = True
        else:
            is_comment = False
        p[0].append(p[1], is_comment)
        return p[0]

    @_("parameter", "parameters parameter")
    def parameters(self, p):
        """
        A list of the parameters (key, value pairs) for this input.

        :returns: all parameters
        :rtype: ParametersNode
        """
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
    )
    def parameter(self, p):
        """
        A singular Key-value pair.

        :returns: the parameter.
        :rtype: SyntaxNode
        """
        return syntax_node.SyntaxNode(
            p.classifier.prefix.value,
            {"classifier": p.classifier, "seperator": p.param_seperator, "data": p[2]},
        )

    @_("TEXT", "FILE_PATH", "file_name TEXT", "file_name FILE_PATH")
    def file_name(self, p):
        """
        A file name.

        :rtype: str
        """
        ret = p[0]
        if len(p) > 1:
            ret += p[1]
        return ret

    @_("file_name", "file_name padding")
    def file_phrase(self, p):
        """
        A file name with or without its padding.

        :returns: a str ValueNode.
        :rtype: ValueNode
        """
        return self._flush_phrase(p, str)

    @_('"="', "padding", '"=" padding')
    def param_seperator(self, p):
        """
        The seperation between a key and value for a parameter.

        :returns: a str ValueNode
        :rtype: ValueNode
        """
        return self._flush_phrase(p, str)

    @_(
        "modifier classifier",
        "KEYWORD",
        "SOURCE_COMMENT",
        "TALLY_COMMENT",
        "classifier NUMBER",
        "classifier PARTICLE_DESIGNATOR",
    )
    def classifier(self, p):
        """
        The classifier of a data input.

        This represents the first word of the data input.
        E.g.: ``M4``, `IMP:N`, ``F104:p``

        :rtype: ClassifierNode
        """
        if hasattr(p, "classifier"):
            classifier = p.classifier
        else:
            classifier = syntax_node.ClassifierNode()

        if hasattr(p, "modifier"):
            classifier.modifier = syntax_node.ValueNode(p.modifier, str)
        if (
            hasattr(p, "KEYWORD")
            or hasattr(p, "SOURCE_COMMENT")
            or hasattr(p, "TALLY_COMMENT")
        ):
            text = p[0]
            classifier.prefix = syntax_node.ValueNode(text, str)
        if hasattr(p, "NUMBER"):
            classifier.number = syntax_node.ValueNode(p.NUMBER, int)
        if hasattr(p, "PARTICLE_DESIGNATOR"):
            classifier.particles = syntax_node.ParticleNode(
                "data particles", p.PARTICLE_DESIGNATOR
            )

        return classifier

    @_("classifier padding", "classifier")
    def classifier_phrase(self, p):
        """
        A classifier with its padding.

        :rtype: ClassifierNode
        """
        classifier = p.classifier
        if len(p) > 1:
            classifier.padding = p.padding
        return classifier

    @_('"*"', "PARTICLE_SPECIAL")
    def modifier(self, p):
        """
        A character that modifies a classifier, e.g., ``*TR``.

        :returns: the modifier
        :rtype: str
        """
        if hasattr(p, "PARTICLE_SPECIAL"):
            if p.PARTICLE_SPECIAL == "*":
                return "*"
        return p[0]

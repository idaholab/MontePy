# Copyright 2024, Battelle Energy Alliance, LLC All Rights Reserved.
from montepy.input_parser.tokens import MCNP_Lexer
from montepy.input_parser import syntax_node
from sly import Parser
import sly

_dec = sly.yacc._decorator


class MetaBuilder(sly.yacc.ParserMeta):
    """Custom MetaClass for allowing subclassing of MCNP_Parser.

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


class SLY_Supressor:
    """This is a fake logger meant to mostly make warnings dissapear."""

    def __init__(self):
        self._parse_fail_queue = []

    def debug(self, msg, *args, **kwargs):
        pass

    info = debug

    warning = debug

    error = debug

    critical = debug

    def parse_error(self, msg, token=None, lineno=0, index=0):
        """Adds a SLY parsing error to the error queue for being dumped later.

        Parameters
        ----------
        msg : str
            The message to display.
        token : Token
            the token that caused the error if any.
        lineno : int
            the current lineno of the error (from SLY not the file), if
            any.
        """
        self._parse_fail_queue.append(
            {"message": msg, "token": token, "line": lineno, "index": index}
        )

    def clear_queue(self):
        """Clears the error queue and returns all errors.

        Returns a list of dictionaries. The dictionary has the keys: "message", "token", "line.

        Returns
        -------
        list
            A list of the errors since the queue was last cleared.
        """
        ret = self._parse_fail_queue
        self._parse_fail_queue = []
        return ret

    def __len__(self):
        return len(self._parse_fail_queue)


class MCNP_Parser(Parser, metaclass=MetaBuilder):
    """Base class for all MCNP parsers that provides basics."""

    # Remove this if trying to see issues with parser
    log = SLY_Supressor()
    tokens = MCNP_Lexer.tokens
    debugfile = None

    def restart(self):
        """Clears internal state information about the current parse.

        Should be ran before a new object is parsed.
        """
        self.log.clear_queue()
        super().restart()

    def parse(self, token_generator, input=None):
        """Parses the token stream and returns a syntax tree.

        If the parsing fails None will be returned.
        The error queue can be retrieved from ``parser.log.clear_queue()``.

        Parameters
        ----------
        token_generator : generator
            the token generator from ``lexer.tokenize``.
        input : Input
            the input that is being lexed and parsed.

        Returns
        -------
        SyntaxNode
        """
        self._input = input

        # debug every time a token is taken
        def gen_wrapper():
            while True:
                token = next(token_generator, None)
                self._debug_parsing_error(token)
                yield token

        # change to using `gen_wrapper()` to debug
        tree = super().parse(token_generator)
        # treat any previous errors as being fatal even if it recovered.
        if len(self.log) > 0:
            return None
        self.tokens = {}
        return tree

    precedence = (("left", SPACE), ("left", TEXT))

    @_("NUMBER", "NUMBER padding")
    def number_phrase(self, p):
        """A non-zero number with or without padding.

        Returns
        -------
        ValueNode
            a float ValueNode
        """
        return self._flush_phrase(p, float)

    @_("NUMBER", "NUMBER padding")
    def identifier_phrase(self, p):
        """A non-zero number with or without padding converted to int.

        Returns
        -------
        ValueNode
            an int ValueNode
        """
        return self._flush_phrase(p, int)

    @_(
        "numerical_phrase",
        "shortcut_phrase",
        "number_sequence numerical_phrase",
        "number_sequence shortcut_phrase",
    )
    def number_sequence(self, p):
        """A list of numbers.

        Returns
        -------
        ListNode
        """
        if len(p) == 1:
            sequence = syntax_node.ListNode("number sequence")
            if type(p[0]) == syntax_node.ListNode:
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

    @_(
        '"(" number_sequence ")"',
        '"(" number_sequence ")" padding',
        '"(" padding number_sequence ")" padding',
    )
    def number_sequence(self, p):
        sequence = syntax_node.ListNode("parenthetical statement")
        sequence.append(p[0])
        for node in list(p)[1:]:
            if isinstance(node, syntax_node.ListNode):
                for val in node.nodes:
                    sequence.append(val)
            elif isinstance(node, str):
                sequence.append(syntax_node.PaddingNode(node))
            else:
                sequence.append(node)
        return sequence

    @_(
        "numerical_phrase numerical_phrase",
        "shortcut_phrase",
        "even_number_sequence numerical_phrase numerical_phrase",
        "even_number_sequence shortcut_phrase",
    )
    def even_number_sequence(self, p):
        """
        A list of numbers with an even number of elements*.

        * shortcuts will break this.
        """
        if not hasattr(p, "even_number_sequence"):
            sequence = syntax_node.ListNode("number sequence")
            sequence.append(p[0])
        else:
            sequence = p[0]
        if len(p) > 1:
            for idx in range(1, len(p)):
                sequence.append(p[idx])
        return sequence

    @_("number_phrase", "null_phrase")
    def numerical_phrase(self, p):
        """Any number, including 0, with its padding.

        Returns
        -------
        ValueNode
            a float ValueNode
        """
        return p[0]

    @_("numerical_phrase", "shortcut_phrase")
    def shortcut_start(self, p):
        return p[0]

    @_(
        "shortcut_start NUM_REPEAT",
        "shortcut_start REPEAT",
        "shortcut_start NUM_MULTIPLY",
        "shortcut_start MULTIPLY",
        "shortcut_start NUM_INTERPOLATE padding number_phrase",
        "shortcut_start INTERPOLATE padding number_phrase",
        "shortcut_start NUM_LOG_INTERPOLATE padding number_phrase",
        "shortcut_start LOG_INTERPOLATE padding number_phrase",
        "NUM_JUMP",
        "JUMP",
    )
    def shortcut_sequence(self, p):
        """A shortcut (repeat, multiply, interpolate, or jump).

        Returns
        -------
        ShortcutNode
            the parsed shortcut.
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
        """A complete shortcut, which should be used, and not shortcut_sequence.

        Returns
        -------
        ShortcutNode
            the parsed shortcut.
        """
        sequence = p.shortcut_sequence
        if len(p) == 2:
            sequence.end_padding = p.padding
        return sequence

    @_("NULL", "NULL padding")
    def null_phrase(self, p):
        """A zero number with or without its padding.

        Returns
        -------
        ValueNode
            a float ValueNode
        """
        return self._flush_phrase(p, float)

    @_("NULL", "NULL padding")
    def null_ident_phrase(self, p):
        """A zero number with or without its padding, for identification.

        Returns
        -------
        ValueNode
            an int ValueNode
        """
        return self._flush_phrase(p, int)

    @_("TEXT", "TEXT padding")
    def text_phrase(self, p):
        """A string with or without its padding.

        Returns
        -------
        ValueNode
            a str ValueNode.
        """
        return self._flush_phrase(p, str)

    def _flush_phrase(self, p, token_type):
        """Creates a ValueNode."""
        if len(p) > 1:
            padding = p[1]
        else:
            padding = None
        return syntax_node.ValueNode(p[0], token_type, padding)

    @_("SPACE", "DOLLAR_COMMENT", "COMMENT")
    def padding(self, p):
        """Anything that is not semantically significant: white space, and comments.

        Returns
        -------
        PaddingNode
            All sequential padding.
        """
        if hasattr(p, "DOLLAR_COMMENT") or hasattr(p, "COMMENT"):
            is_comment = True
        else:
            is_comment = False
        return syntax_node.PaddingNode(p[0], is_comment)

    @_("padding SPACE", "padding DOLLAR_COMMENT", "padding COMMENT", 'padding "&"')
    def padding(self, p):
        """Anything that is not semantically significant: white space, and comments.

        Returns
        -------
        PaddingNode
            All sequential padding.
        """
        if hasattr(p, "DOLLAR_COMMENT") or hasattr(p, "COMMENT"):
            is_comment = True
        else:
            is_comment = False
        p[0].append(p[1], is_comment)
        return p[0]

    @_("parameter", "parameters parameter")
    def parameters(self, p):
        """A list of the parameters (key, value pairs) for this input.

        Returns
        -------
        ParametersNode
            all parameters
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
        """A singular Key-value pair.

        Returns
        -------
        SyntaxNode
            the parameter.
        """
        return syntax_node.SyntaxNode(
            p.classifier.prefix.value,
            {"classifier": p.classifier, "seperator": p.param_seperator, "data": p[2]},
        )

    @_("file_atom", "file_name file_atom")
    def file_name(self, p):
        """A file name.

        Returns
        -------
        str
        """
        ret = p[0]
        if len(p) > 1:
            ret += p[1]
        return ret

    @_(
        "TEXT",
        "FILE_PATH",
        "NUMBER",
        "PARTICLE",
        "PARTICLE_SPECIAL",
        "INTERPOLATE",
        "JUMP",
        "KEYWORD",
        "LOG_INTERPOLATE",
        "NULL",
        "REPEAT",
        "SURFACE_TYPE",
        "THERMAL_LAW",
        "ZAID",
        "NUMBER_WORD",
    )
    def file_atom(self, p):
        return p[0]

    @_("file_name", "file_name padding")
    def file_phrase(self, p):
        """A file name with or without its padding.

        Returns
        -------
        ValueNode
            a str ValueNode.
        """
        return self._flush_phrase(p, str)

    @_("padding", "equals_sign", "padding equals_sign")
    def param_seperator(self, p):
        """The seperation between a key and value for a parameter.

        Returns
        -------
        ValueNode
            a str ValueNode
        """
        padding = p[0]
        if len(p) > 1:
            padding += p[1]
        return padding

    @_('"="', '"=" padding')
    def equals_sign(self, p):
        """The seperation between a key and value for a parameter.

        Returns
        -------
        ValueNode
            a str ValueNode
        """
        padding = syntax_node.PaddingNode(p[0])
        if hasattr(p, "padding"):
            padding += p.padding
        return padding

    @_('":" part', 'particle_type "," part')
    def particle_type(self, p):
        if hasattr(p, "particle_type"):
            token = p.particle_type.token + "".join(list(p)[1:])
            particle_node = syntax_node.ParticleNode("data particles", token)
        else:
            particle_node = syntax_node.ParticleNode("data particles", "".join(list(p)))

        return particle_node

    @_("PARTICLE", "PARTICLE_SPECIAL")
    def part(self, p):
        return p[0]

    @_(
        "TEXT",
        "KEYWORD",
        "PARTICLE",
        "SOURCE_COMMENT",
        "TALLY_COMMENT",
    )
    def data_prefix(self, p):
        return syntax_node.ValueNode(p[0], str)

    @_(
        "modifier data_prefix",
        "data_prefix",
        "classifier NUMBER",
        "classifier NULL",
        "classifier particle_type",
    )
    def classifier(self, p):
        """The classifier of a data input.

        This represents the first word of the data input.
        E.g.: ``M4``, `IMP:N`, ``F104:p``

        Returns
        -------
        ClassifierNode
        """
        if hasattr(p, "classifier"):
            classifier = p.classifier
        else:
            classifier = syntax_node.ClassifierNode()

        if hasattr(p, "modifier"):
            classifier.modifier = syntax_node.ValueNode(p.modifier, str)
        if hasattr(p, "data_prefix"):
            classifier.prefix = p.data_prefix
        if hasattr(p, "NUMBER") or hasattr(p, "NULL"):
            if hasattr(p, "NUMBER"):
                num = p.NUMBER
            else:
                num = p.NULL
            classifier.number = syntax_node.ValueNode(num, int)
        if hasattr(p, "particle_type"):
            classifier.particles = p.particle_type
        return classifier

    @_("classifier padding", "classifier")
    def classifier_phrase(self, p):
        """A classifier with its padding.

        Returns
        -------
        ClassifierNode
        """
        classifier = p.classifier
        if len(p) > 1:
            classifier.padding = p.padding
        return classifier

    @_('"*"', "PARTICLE_SPECIAL")
    def modifier(self, p):
        """A character that modifies a classifier, e.g., ``*TR``.

        Returns
        -------
        str
            the modifier
        """
        if hasattr(p, "PARTICLE_SPECIAL"):
            if p.PARTICLE_SPECIAL == "*":
                return "*"
        return p[0]

    @_('"("', '"(" padding')
    def lparen_phrase(self, p):
        pad = syntax_node.PaddingNode(p[0])
        if len(p) > 1:
            for node in p.padding.nodes:
                pad.append(node)
        return pad

    @_('")"', '")" padding')
    def rparen_phrase(self, p):
        pad = syntax_node.PaddingNode(p[0])
        if len(p) > 1:
            for node in p.padding.nodes:
                pad.append(node)
        return pad

    def error(self, token):
        """Default error handling.

        Puts the data into a queue that can be pulled out later for one final clear debug.

        Parameters
        ----------
        token : Token
            the token that broke the parsing rules.
        """
        # self._debug_parsing_error(token)
        if token:
            lineno = getattr(token, "lineno", 0)
            if self._input and self._input.lexer:
                lexer = self._input.lexer
                index = lexer.find_column(lexer.text, token)
            else:
                index = 0
            if lineno:
                self.log.parse_error(
                    f"sly: Syntax error at line {lineno}, token={token.type}\n",
                    token,
                    lineno,
                    index,
                )
            else:
                self.log.parse_error(
                    f"sly: Syntax error, token={token.type}", token, lineno
                )
        else:
            self.log.parse_error("sly: Parse error in input. EOF\n")

    def _debug_parsing_error(self, token):  # pragma: no cover
        """A function that should be called from error when debugging a parsing error.

        Call this from the method error. Also you will need the relevant debugfile to be set and saving the parser
        tables to file. e.g.,

        debugfile = 'parser.out'
        """
        print(f"********* New Parsing Error from: {type(self)} ************ ")
        print(f"Token: {token}")
        print(f"State: {self.state}, statestack: {self.statestack}")
        print(f"Symstack: {self.symstack}")
        print(f"Log length: {len(self.log)}")
        print()

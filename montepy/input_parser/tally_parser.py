# Copyright 2024, Battelle Energy Alliance, LLC All Rights Reserved.
from montepy.input_parser.data_parser import DataParser
from montepy.input_parser.tokens import TallyLexer
from montepy.input_parser import syntax_node


class TallyParser(DataParser):
    """A barebone parser for parsing tallies before they are fully implemented.

    Returns
    -------
    SyntaxNode
        a syntax tree for the data input.
    """

    debugfile = None
    _lexer_class = TallyLexer

    @_("introduction tally_specification")
    def tally(self, p):
        ret = {}
        for key, node in p.introduction.nodes.items():
            ret[key] = node
        ret["data"] = p.tally_specification
        return syntax_node.SyntaxNode("data", ret)

    @_("tally_numbers", "tally_numbers end_phrase")
    def tally_specification(self, p):
        if hasattr(p, "end_phrase"):
            text = p.end_phrase
        else:
            text = syntax_node.ValueNode(None, str)

        return syntax_node.SyntaxNode(
            "tally list", {"tally": p.tally_numbers, "end": text}
        )

    @_('"("', '"(" padding', '")"', '")" padding')
    def paren_phrase(self, p):
        """ """
        return self._flush_phrase(p, str)

    @_("PARTICLE", "PARTICLE padding")
    def end_phrase(self, p):
        """A non-zero number with or without padding.

        Returns
        -------
        ValueNode
            a float ValueNode
        """
        return self._flush_phrase(p, str)

    # tally_numbers uses fresh rules (no number_sequence) so that the inherited
    # `number_sequence → "(" number_sequence ")"` production is unreachable from
    # the `tally` start symbol and cannot create a shift/reduce conflict with
    # lparen_phrase inside tally_group.
    @_(
        "tally_flat_item",
        "tally_group",
        "tally_numbers tally_flat_item",
        "tally_numbers tally_group",
    )
    def tally_numbers(self, p):
        if hasattr(p, "tally_numbers"):
            ret = p.tally_numbers
            item = p.tally_flat_item if hasattr(p, "tally_flat_item") else p.tally_group
        else:
            ret = syntax_node.ListNode("tally numbers")
            item = p[0]
        # Preserve ListNode("tally group") intact so grouping structure is not lost.
        # Only flatten other ListNode subclasses (e.g. ShortcutNode).
        if isinstance(item, syntax_node.ListNode) and item.name != "tally group":
            for node in item.nodes:
                ret.append(node)
        else:
            ret.append(item)
        return ret

    @_("number_phrase", "null_phrase", "shortcut_phrase")
    def tally_flat_item(self, p):
        return p[0]

    @_("lparen_phrase tally_group_body rparen_phrase")
    def tally_group(self, p):
        ret = syntax_node.ListNode("tally group")
        ret.append(p.lparen_phrase)
        for node in p.tally_group_body.nodes:
            ret.append(node)
        ret.append(p.rparen_phrase)
        return ret

    @_("tally_group_item", "tally_group_body tally_group_item")
    def tally_group_body(self, p):
        if hasattr(p, "tally_group_body"):
            ret = p.tally_group_body
        else:
            ret = syntax_node.ListNode("tally group body")
        item = p.tally_group_item
        # Only flatten ShortcutNode (e.g. repeat/jump sequences).
        # Preserve lattice_phrase, universe_phrase, and nested tally_group intact.
        if isinstance(item, syntax_node.ShortcutNode):
            for node in item.nodes:
                ret.append(node)
        else:
            ret.append(item)
        return ret

    @_(
        "number_phrase",
        "null_phrase",
        "shortcut_phrase",
        "path_sep",
        "lattice_phrase",
        "universe_phrase",
        "tally_group",
    )
    def tally_group_item(self, p):
        return p[0]

    @_("PARTICLE_SPECIAL", "PARTICLE_SPECIAL padding")
    def path_sep(self, p):
        return self._flush_phrase(p, str)

    @_('"[" lattice_body "]"', '"[" lattice_body "]" padding')
    def lattice_phrase(self, p):
        ret = syntax_node.ListNode("lattice phrase")
        ret.append(syntax_node.PaddingNode(p[0]))
        for node in p.lattice_body.nodes:
            ret.append(node)
        if hasattr(p, "padding"):
            ret.append(syntax_node.PaddingNode(p[2]))
            ret.append(p.padding)
        else:
            ret.append(syntax_node.PaddingNode(p[2]))
        return ret

    @_(
        "lattice_item",
        "lattice_body lattice_item",
        'lattice_body "," lattice_item',
        'lattice_body "," padding lattice_item',
    )
    def lattice_body(self, p):
        if hasattr(p, "lattice_body"):
            ret = p.lattice_body
        else:
            ret = syntax_node.ListNode("lattice body")
        if hasattr(p, "padding"):
            # lattice_body "," padding lattice_item
            ret.append(syntax_node.PaddingNode(p[1]))
            ret.append(p.padding)
        elif len(p) > 1 and isinstance(p[1], str) and p[1] == ",":
            # lattice_body "," lattice_item
            ret.append(syntax_node.PaddingNode(p[1]))
        ret.append(p.lattice_item)
        return ret

    @_(
        "number_phrase",
        "null_phrase",
        'number_phrase ":" number_phrase',
        'null_phrase ":" number_phrase',
        'number_phrase ":" null_phrase',
        'null_phrase ":" null_phrase',
    )
    def lattice_item(self, p):
        if len(p) > 1:
            ret = syntax_node.ListNode("lattice range")
            ret.append(p[0])
            ret.append(syntax_node.PaddingNode(p[1]))
            ret.append(p[2])
            return ret
        return p[0]

    @_("KEYWORD equals_sign number_phrase", "PARTICLE equals_sign number_phrase")
    def universe_phrase(self, p):
        token_val = p.KEYWORD if hasattr(p, "KEYWORD") else p.PARTICLE
        ret = syntax_node.ListNode("universe phrase")
        ret.append(syntax_node.ValueNode(token_val, str))
        ret.append(p.equals_sign)
        ret.append(p.number_phrase)
        return ret

# Copyright 2024, Battelle Energy Alliance, LLC All Rights Reserved.
from montepy.input_parser.data_parser import DataParser
from montepy.input_parser import syntax_node


class TallyParser(DataParser):
    """A barebone parser for parsing tallies before they are fully implemented.

    Returns
    -------
    SyntaxNode
        a syntax tree for the data input.
    """

    debugfile = None

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

    @_(
        "tally_numbers tally_numbers",
        "number_sequence",
        "tally_group",
    )
    def tally_numbers(self, p):
        if hasattr(p, "tally_numbers1"):
            ret = p.tally_numbers1
            for node in p.tally_numbers2.nodes:
                ret.append(node)
            return ret
        else:
            return p[0]

    @_(
        "paren_phrase number_sequence paren_phrase",
    )
    def tally_group(self, p):
        ret = syntax_node.ListNode()
        ret.append(p[0])
        for node in p.number_sequence.nodes:
            ret.append(node)
        ret.append(p[2])
        return ret

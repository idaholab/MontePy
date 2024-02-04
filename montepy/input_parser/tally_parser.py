# Copyright 2024, Battelle Energy Alliance, LLC All Rights Reserved.
from montepy.input_parser.data_parser import DataParser
from montepy.input_parser import syntax_node


class TallyParser(DataParser):
    """ """

    debugfile = None

    @_("introduction tally_specification")
    def tally(self, p):
        ret = {}
        for key, node in p.introduction.nodes.items():
            ret[key] = node
        ret["tally"] = p.tally_specification["tally"]
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

    @_("PARTICLE", "PARTICLE padding")
    def end_phrase(self, p):
        """
        A non-zero number with or without padding.

        :returns: a float ValueNode
        :rtype: ValueNode
        """
        return self._flush_phrase(p, str)

    @_(
        "tally_numbers tally_numbers",
        "number_sequence",
        "paren_number_group",
    )
    def tally_numbers(self, p):
        if hasattr(p, "tally_numbers1"):
            ret = p.tally_numbers0
            for node in p.tally_numbers1.nodes:
                ret.append(node)
            return ret
        else:
            return p[0]

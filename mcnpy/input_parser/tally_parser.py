from mcnpy.input_parser.data_parser import DataParser
from mcnpy.input_parser import syntax_node


class TallyParser(DataParser):
    """ """

    debugfile = None

    @_("introduction tally_specification")
    def tally(self, p):
        ret = {}
        for key, node in p.introduction.nodes.items():
            ret[key] = node
        ret["tally"] = p.tally_specification
        return syntax_node.SyntaxNode("data", ret)

    @_("tally_numbers", "tally_numbers padding end_phrase")
    def tally_specification(self, p):
        if hasattr(p, "end_phrase"):
            text = p.end_phrase
            end_pad = p.padding
        else:
            text = syntax_node.ValueNode(None, str)
            end_pad = syntax_node.PaddingNode(None)

        return syntax_node.SyntaxNode(
            "tally list", {"tally": p.tally_numbers, "end_pad": end_pad, "end": text}
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
        '"(" number_sequence ")"',
        '"(" padding number_sequence ")"',
    )
    def tally_numbers(self, p):
        if hasattr(p, "tally_numbers1"):
            return syntax_node.SyntaxNode("tally tree", {"left": p[0], "right": p[1]})
        else:
            if isinstance(p[0], str):
                left = syntax_node.PaddingNode(p[0])
                if hasattr(p, "padding"):
                    left.append(p.padding)
                right = syntax_node.PaddingNode(p[-1])
            else:
                left = syntax_node.PaddingNode(None)
                right = syntax_node.PaddingNode(None)
            return syntax_node.SyntaxNode(
                "tally set", {"left": left, "tally": p.number_sequence, "right": right}
            )

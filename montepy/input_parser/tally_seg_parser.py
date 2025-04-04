# Copyright 2024, Battelle Energy Alliance, LLC All Rights Reserved.
from montepy.input_parser.data_parser import DataParser
from montepy.input_parser import syntax_node


class TallySegmentParser(DataParser):
    """A barebone parser for parsing tally segment inputs before they are fully implemented.

    .. versionadded:: 0.2.10

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
        ret["tally"] = p.tally_specification
        return syntax_node.SyntaxNode("data", ret)

    @_(
        "tally_numbers",
        "tally_numbers end_phrase",
        "tally_numbers end_phrase end_phrase",
    )
    def tally_specification(self, p):
        if hasattr(p, "end_phrase"):
            text = p.end_phrase
        else:
            text = syntax_node.ValueNode(None, str)

        return syntax_node.SyntaxNode(
            "tally list", {"tally": p.tally_numbers, "end": text}
        )

    @_("PARTICLE", "PARTICLE padding", "TEXT", "TEXT padding")
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
        "tally_numbers padding",
    )
    def tally_numbers(self, p):
        if hasattr(p, "tally_numbers"):
            ret = p.tally_numbers
            ret.nodes["right"] += p.padding
            return ret
        if hasattr(p, "tally_numbers1"):
            return syntax_node.SyntaxNode("tally tree", {"left": p[0], "right": p[1]})
        else:
            left = syntax_node.PaddingNode(None)
            right = syntax_node.PaddingNode(None)
            return syntax_node.SyntaxNode(
                "tally set", {"left": left, "tally": p[0], "right": right}
            )

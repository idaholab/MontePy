# Copyright 2024, Battelle Energy Alliance, LLC All Rights Reserved.
from montepy.input_parser.parser_base import MCNP_Parser
from montepy.input_parser import syntax_node


class ReadParser(MCNP_Parser):
    """
    A parser for handling "read" inputs.

    .. versionadded:: 0.2.0
        This was added with the major parser rework.
    """

    debugfile = None
    dont_copy = {"parameter"}

    @_("KEYWORD padding parameters", "padding KEYWORD padding parameters")
    def read_input(self, p):
        if isinstance(p[0], syntax_node.PaddingNode):
            start_pad = p[0]
            mid_pad = p[2]
        else:
            start_pad = syntax_node.PaddingNode()
            mid_pad = p[1]
        if p.KEYWORD.lower() == "read":
            return syntax_node.SyntaxNode(
                "read",
                {
                    "start_pad": start_pad,
                    "keyword": p.KEYWORD,
                    "padding": mid_pad,
                    "parameters": p.parameters,
                },
            )
        else:
            return False

    @_(
        "classifier param_seperator file_phrase",
    )
    def parameter(self, p):
        return syntax_node.SyntaxNode(
            p.classifier.prefix.value,
            {"classifier": p.classifier, "seperator": p.param_seperator, "data": p[2]},
        )

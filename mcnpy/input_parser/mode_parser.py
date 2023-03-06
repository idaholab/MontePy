from mcnpy.errors import *
from mcnpy.input_parser.data_parser import DataParser
from mcnpy.input_parser import syntax_node


class ModeParser(DataParser):
    debugfile = None

    @_("classifier_phrase particle_sequence")
    def mode(self, p):
        return syntax_node.SyntaxNode(
            "mode", {"classifier": p.classifier_phrase, "data": p.particle_sequence}
        )

    @_("particle_phrase", "particle_sequence particle_phrase")
    def particle_sequence(self, p):
        if len(p) == 1:
            sequence = syntax_node.ListNode("particle sequence")
            sequence.append(p[0])
        else:
            sequence = p[0]
            sequence.append(p[1])
        return sequence

    @_("PARTICLE", "SURFACE_TYPE", "PARTICLE_SPECIAL")
    def particle_text(self, p):
        return p[0]

    @_("particle_text padding", "particle_text")
    def particle_phrase(self, p):
        return self._flush_phrase(p, str)

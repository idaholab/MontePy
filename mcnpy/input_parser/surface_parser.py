from mcnpy.input_parser.parser_base import MCNP_Parser


class SurfaceParser(MCNP_Parser):
    @_("number_phrase SURFACE_TYPE padding number_sequence")
    def surface(self, p):
        return p

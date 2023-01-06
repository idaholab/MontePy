from mcnpy.input_parser.parser_base import MCNP_Parser


class SurfaceParser(MCNP_Parser):
    @_("surface_id SURFACE_TYPE padding number_sequence")
    def surface(self, p):
        return p

    @_("surface_id number_phrase SURFACE_TYPE padding number_sequence")
    def surface(self, p):
        return p

    @_('"*" number_phrase', '"+" number_phrase', "number_phrase")
    def surface_id(self, p):
        return p

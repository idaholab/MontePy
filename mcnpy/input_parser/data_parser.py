from mcnpy.errors import *
from mcnpy.input_parser.parser_base import MCNP_Parser, MetaBuilder


class DataParser(MCNP_Parser, metaclass=MetaBuilder):
    @_(
        "identifier number_sequence",
        "identifier isotope_fractions",
        "data_input parameters",
    )
    def data_input(self, p):
        return p

    @_("TEXT", "TEXT NUMBER", "identifier PARTICLE_DESIGNATOR", "identifier padding")
    def identifier(self, p):
        return p

    @_("zaid_phrase number_phrase")
    def isotope_fraction(self, p):
        return p

    @_("isotope_fraction", "isotope_fractions isotope_fraction")
    def isotope_fractions(self, p):
        return p

    @_("ZAID padding")
    def zaid_phrase(self, p):
        return p

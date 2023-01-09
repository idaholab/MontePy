from mcnpy.input_parser.parser_base import MCNP_Parser


class MaterialParser(MCNP_Parser):
    @_("identifier isotope_fractions", "identifier isotope_fractions parameters")
    def material(self, p):
        return p

    @_("TEXT NUMBER padding")
    def identifier(self, p):
        if p.TEXT.lower() == "m":
            return p

    @_("ZAID padding")
    def zaid_phrase(self, p):
        return p

    @_("zaid_phrase number_phrase")
    def isotope_fraction(self, p):
        return p

    @_("isotope_fraction", "isotope_fractions isotope_fraction")
    def isotope_fractions(self, p):
        return p

    @_("KEYWORD param_seperator NUMBER TEXT padding")
    def parameter(self, p):
        return p

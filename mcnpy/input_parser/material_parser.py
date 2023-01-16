from mcnpy.input_parser.data_parser import DataParser


class MaterialParser(DataParser):
    @_("identifier isotope_fractions", "identifier isotope_fractions parameters")
    def material(self, p):
        return p

    @_("KEYWORD param_seperator NUMBER text_phrase")
    def parameter(self, p):
        return p

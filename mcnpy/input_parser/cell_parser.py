from mcnpy.input_parser.parser_base import MCNP_Parser


class CellParser(MCNP_Parser):
    @_("number_phrase material geometry_expr parameters")
    def cell(self, p):
        return p

    @_("number_phrase material geometry_expr")
    def cell(self, p):
        return p

    @_("null_phrase")
    def material(self, p):
        return p

    @_("number_phrase number_phrase")
    def material(self, p):
        return p

    @_('":"')
    def union(self, p):
        return p

    @_("union padding")
    def union(self, p):
        return p

    @_("geometry_expr union geometry_term")
    def geometry_expr(self, p):
        return p

    @_("geometry_expr padding")
    def geometry_expr(self, p):
        return p

    @_("geometry_term")
    def geometry_expr(self, p):
        return p.geometry_term

    @_("geometry_term padding geometry_factor")
    def geometry_term(self, p):
        return p

    @_("geometry_term padding")
    def geometry_term(self, p):
        return p

    @_("geometry_factor")
    def geometry_term(self, p):
        return p.geometry_factor

    @_("geometry_factory")
    def geometry_factor(self, p):
        return p.geometry_factory

    @_("COMPLEMENT geometry_factory")
    def geometry_factor(self, p):
        return p

    @_("NUMBER")
    def geometry_factory(self, p):
        return p

    @_('"(" geometry_expr ")"')
    def geometry_factory(self, p):
        return p

    @_("parameter")
    def parameters(self, p):
        return p

    @_("parameters parameter")
    def parameters(self, p):
        return p

    @_('KEYWORD "=" number_phrase')
    def parameter(self, p):
        return p

    @_('KEYWORD PARTICLE_DESIGNATOR "=" number_phrase')
    def parameter(self, p):
        return p

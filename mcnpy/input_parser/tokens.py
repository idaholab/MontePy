from mcnpy.utilities import fortran_float
from sly import Lexer


class MCNP_Lexer(Lexer):
    tokens = {DOLLAR_COMMENT, COMMENT, INT, FLOAT, SPACE}

    literals = {"(", ":", ")"}

    DOLLAR_COMMENT = r"\$.*\s"

    @_(r"[cC]\s.*")
    def COMMENT(self, t):
        start = find_column(self.text, t)
        if start <= 5:
            return t
        else:
            raise ValueError("Comment not allowed here")

    @_(r"\s+")
    def SPACE(self, t):
        self.lineno += t.value.count("\n")
        return t

    @_(r"[0-9]+")
    def INT(self, t):
        t.value = int(t.value)
        return t

    @_(r"[0-9]*\.?[0-9]+[eE]?[+\-][0-9]*")
    def FLOAT(self, t):
        t.value = fortran_float(t.value)
        return t


def find_column(text, token):
    last_cr = text.rfind("\n", 0, token.index)
    if last_cr < 0:
        last_cr = 0
    column = token.index - last_cr
    return column

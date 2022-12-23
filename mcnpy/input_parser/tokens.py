from mcnpy.utilities import fortran_float
from sly import Lexer


class MCNP_Lexer(Lexer):
    tokens = {
        DOLLAR_COMMENT,
        COMMENT,
        SOURCE_COMMENT,
        TALLY_COMMENT,
        INT,
        FLOAT,
        NULL,
        SPACE,
        MESSAGE,
        REPEAT,
        MULTIPLY,
        INTERPOLATE,
        JUMP,
        LOG_INTERPOLATE,
    }

    literals = {"(", ":", ")", "&", "#"}

    @_(r"\$.*\s?")
    def DOLLAR_COMMENT(self, t):
        self.lineno += t.value.count("\n")
        return t

    @_(r"[cC]\s.*")
    def COMMENT(self, t):
        self.lineno += t.value.count("\n")
        start = find_column(self.text, t)
        if start <= 5:
            return t
        else:
            raise ValueError("Comment not allowed here")

    @_(r"[sS][cC]\d+.*")
    def SOURCE_COMMENT(self, t):
        self.lineno += t.value.count("\n")
        start = find_column(self.text, t)
        if start <= 5:
            return t
        else:
            raise ValueError("Comment not allowed here")

    @_(r"[fF][cC]\d+.*")
    def TALLY_COMMENT(self, t):
        self.lineno += t.value.count("\n")
        start = find_column(self.text, t)
        if start <= 5:
            return t
        else:
            raise ValueError("Comment not allowed here")

    @_(r"\s+")
    def SPACE(self, t):
        self.lineno += t.value.count("\n")
        return t

    @_(r"[+\-]?[0-9]*\.[0-9]+[eE]?[+\-]?[0-9]*")
    def FLOAT(self, t):
        t.value = fortran_float(t.value)
        return t

    @_(r"[+\-]?[0-9]*[1-9]+[0-9]*")
    def INT(self, t):
        t.value = int(t.value)
        return t

    @_(r"[+\-]?0+")
    def NULL(self, t):
        t.value = 0
        return t

    @_(r"(MESSAGE|message):.*\s")
    def MESSAGE(self, t):
        self.lineno += t.value.count("\n")
        return t

    @_(r"\d*[rR]")
    def REPEAT(self, t):
        try:
            t.repeat_num = int(t.value.lower().replace("r", ""))
        except ValueError:
            t.repeat_num = 1
        return t

    @_(r"\d*[mM]")
    def MULTIPLY(self, t):
        try:
            t.multiply_num = int(t.value.lower().replace("m", ""))
        except ValueError:
            t.multiply_num = 1
        return t

    @_(r"\d*[iI]")
    def INTERPOLATE(self, t):
        try:
            t.interp_num = int(t.value.lower().replace("i", ""))
        except ValueError:
            t.interp_num = 1
        return t

    @_(r"\d*[jJ]")
    def JUMP(self, t):
        try:
            t.jump_num = int(t.value.lower().replace("i", ""))
        except ValueError:
            t.jump_num = 1
        return t

    @_(r"\d*(log|LOG|ilog|ILOG)")
    def LOG_INTERPOLATE(self, t):
        try:
            t.jump_num = int(t.value.lower().replace("i", ""))
        except ValueError:
            t.jump_num = 1
        return t


def find_column(text, token):
    last_cr = text.rfind("\n", 0, token.index)
    if last_cr < 0:
        last_cr = 0
    column = token.index - last_cr
    return column

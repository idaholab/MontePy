from mcnpy.utilities import fortran_float
import re
from sly import Lexer


class MCNP_Lexer(Lexer):
    tokens = {
        COMMENT,
        COMPLEMENT,
        DOLLAR_COMMENT,
        INTERPOLATE,
        JUMP,
        KEYWORD,
        LOG_INTERPOLATE,
        MESSAGE,
        MULTIPLY,
        NUMBER,
        NULL,
        PARTICLE_DESIGNATOR,
        REPEAT,
        SOURCE_COMMENT,
        SPACE,
        SURFACE_TYPE,
        TALLY_COMMENT,
        TEXT,
        ZAID,
    }

    _KEYWORDS = {
        # Cells
        "imp",
        "vol",
        "pwt",
        "ext",
        "fcl",
        "wwn",
        "dxc",
        "nonu",
        "pd",
        "tmp",
        "u",
        "trcl",
        "lat",
        "fill",
        "elpt",
        "cosy",
        "bflcl",
        "unc",
        # materials
        "gas",
        "estep",
        "hstep",
        "nlib",
        "plib",
        "pnlib",
        "elib",
        "hlib",
        "alib",
        "slib",
        "tlib",
        "dlib",
        "cond",
        "refi",
        "refc",
        "refs",
    }

    _SURFACE_TYPES = {
        "p",
        "px",
        "py",
        "pz",
        "so",
        "s",
        "sx",
        "sy",
        "sz",
        "c/x",
        "c/y",
        "c/z",
        "cx",
        "cy",
        "cz",
        "k/x",
        "k/y",
        "k/z",
        "kx",
        "ky",
        "kz",
        "sq",
        "gq",
        "tx",
        "ty",
        "tz",
        "x",
        "y",
        "z",
        "box",
        "rpp",
        "sph",
        "rcc",
        "rhp",
        "hex",
        "rec",
        "trc",
        "ell",
        "wed",
        "arb",
    }

    literals = {"(", ":", ")", "&", "#", "=", "*", "+"}

    COMPLEMENT = r"\#"

    reflags = re.IGNORECASE | re.VERBOSE

    @_(r"\$.*\s?")
    def DOLLAR_COMMENT(self, t):
        self.lineno += t.value.count("\n")
        return t

    @_(r"C\s.*")
    def COMMENT(self, t):
        self.lineno += t.value.count("\n")
        start = find_column(self.text, t)
        if start <= 5:
            return t
        else:
            raise ValueError("Comment not allowed here")

    @_(r"SC\d+.*")
    def SOURCE_COMMENT(self, t):
        self.lineno += t.value.count("\n")
        start = find_column(self.text, t)
        if start <= 5:
            return t
        else:
            raise ValueError("Comment not allowed here")

    @_(r"FC\d+.*")
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

    @_(r"\d{4,6}\.\d{2,3}[a-z]")
    def ZAID(self, t):
        return t

    @_(r"[+\-]?[0-9]+\.?[0-9]*E?[+\-]?[0-9]*")
    def NUMBER(self, t):
        t.value = fortran_float(t.value)
        if t.value == 0:
            t.type = "NULL"
        return t

    NULL = r"0+"

    @_(r":[npe|quvfhl+\-xyo!<>g/zk%^b_~cw@dtsa\*\?\#,]+")
    def PARTICLE_DESIGNATOR(self, t):
        return t

    @_(r"MESSAGE:.*\s")
    def MESSAGE(self, t):
        self.lineno += t.value.count("\n")
        return t

    @_(r"\d*R\s")
    def REPEAT(self, t):
        try:
            t.repeat_num = int(t.value.lower().replace("r", ""))
        except ValueError:
            t.repeat_num = 1
        return t

    @_(r"\d*M\s")
    def MULTIPLY(self, t):
        try:
            t.multiply_num = int(t.value.lower().replace("m", ""))
        except ValueError:
            t.multiply_num = 1
        return t

    @_(r"\d*I\s")
    def INTERPOLATE(self, t):
        try:
            t.interp_num = int(t.value.lower().replace("i", ""))
        except ValueError:
            t.interp_num = 1
        return t

    @_(r"\d*J\s")
    def JUMP(self, t):
        try:
            t.jump_num = int(t.value.lower().replace("i", ""))
        except ValueError:
            t.jump_num = 1
        return t

    @_(r"\d*I?LOG\s")
    def LOG_INTERPOLATE(self, t):
        try:
            t.jump_num = int(t.value.lower().replace("i", ""))
        except ValueError:
            t.jump_num = 1
        return t

    @_(r"[a-z/]+")
    def TEXT(self, t):
        if t.value.lower() in self._KEYWORDS:
            t.type = "KEYWORD"
        elif t.value.lower() in self._SURFACE_TYPES:
            t.type = "SURFACE_TYPE"
        return t

    KEYWORD = r"imp"

    SURFACE_TYPE = r"pz"


def find_column(text, token):
    last_cr = text.rfind("\n", 0, token.index)
    if last_cr < 0:
        last_cr = 0
    column = token.index - last_cr
    return column

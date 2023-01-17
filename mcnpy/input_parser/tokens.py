from mcnpy.input_parser import constants
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
        # read
        "read",
        "noecho",
        "file",
        "decode",
        "encode",
        # Cells
        "like",
        "but",
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
        # volume
        "no",
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
        t.value = t.value.expandtabs(constants.TABSIZE)
        self.lineno += t.value.count("\n")
        return t

    @_(r"\d{4,6}\.\d{2,3}[a-z]")
    def ZAID(self, t):
        return t

    @_(r"[+\-]?[0-9]+\.?[0-9]*E?[+\-]?[0-9]*")
    def NUMBER(self, t):
        if fortran_float(t.value) == 0:
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

    REPEAT = r"\d*R\s"

    MULTIPLY = r"M\s"

    INTERPOLATE = r"\d*I\s"

    JUMP = r"\d*J\s"

    LOG_INTERPOLATE = r"\d*I?LOG\s"

    @_(r"[a-z/\.]+")
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

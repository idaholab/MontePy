# Copyright 2024, Battelle Energy Alliance, LLC All Rights Reserved.
from montepy import constants
from montepy.utilities import fortran_float
import re
from sly import Lexer


class MCNP_Lexer(Lexer):
    """
    Base lexer for all MCNP lexers.

    Provides ~90% of the tokens definition.

    .. versionadded:: 0.2.0
        This was added with the major parser rework.
    """

    tokens = {
        COMMENT,
        COMPLEMENT,
        DOLLAR_COMMENT,
        FILE_PATH,
        INTERPOLATE,
        JUMP,
        KEYWORD,
        LIBRARY_SUFFIX,
        LOG_INTERPOLATE,
        MESSAGE,
        MULTIPLY,
        NUM_INTERPOLATE,
        NUM_JUMP,
        NUM_LOG_INTERPOLATE,
        NUM_MULTIPLY,
        NUM_REPEAT,
        NUMBER,
        NUMBER_WORD,
        NULL,
        PARTICLE,
        PARTICLE_SPECIAL,
        REPEAT,
        SOURCE_COMMENT,
        SPACE,
        SURFACE_TYPE,
        TALLY_COMMENT,
        TEXT,
        THERMAL_LAW,
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
        # sdef
        "cel",
        "sur",
        "erg",
        "tme",
        "dir",
        "vec",
        "nrm",
        "pos",
        "rad",
        "ext",
        "axs",
        "x",
        "y",
        "z",
        "ccc",
        "ara",
        "wgt",
        "tr",
        "eff",
        "par",
        "dat",
        "loc",
        "bem",
        "bap",
    }
    """
    Defines allowed keywords in MCNP.
    """

    literals = {"(", ":", ")", "&", "#", "=", "*", "+", ","}

    COMPLEMENT = r"\#"
    """
    A complement character.
    """

    reflags = re.IGNORECASE | re.VERBOSE

    @_(r"\$.*")
    def DOLLAR_COMMENT(self, t):
        """
        A comment starting with a dollar sign.
        """
        self.lineno += t.value.count("\n")
        return t

    @_(r"C\n", r"C\s.*")
    def COMMENT(self, t):
        """
        A ``c`` style comment.
        """
        self.lineno += t.value.count("\n")
        start = self.find_column(self.text, t)
        if start > 5:
            t.type = "TEXT"
        return t

    @_(r"SC\d+.*")
    def SOURCE_COMMENT(self, t):
        """
        A source comment.
        """
        self.lineno += t.value.count("\n")
        start = self.find_column(self.text, t)
        if start <= 5:
            return t
        else:
            raise ValueError("Comment not allowed here")

    @_(r"FC\d+.*")
    def TALLY_COMMENT(self, t):
        """
        A tally Comment.
        """
        self.lineno += t.value.count("\n")
        start = self.find_column(self.text, t)
        if start <= 5:
            return t
        else:
            raise ValueError("Comment not allowed here")

    @_(r"\s+")
    def SPACE(self, t):
        """
        Any white space.
        """
        t.value = t.value.expandtabs(constants.TABSIZE)
        self.lineno += t.value.count("\n")
        return t

    @_(r"\d{4,6}\.(\d{2}[a-z]|\d{3}[a-z]{2})")
    def ZAID(self, t):
        """
        A ZAID isotope definition in the MCNP format.

        E.g.: ``1001.80c``.
        """
        return t

    # note: / is not escaping - since this doesn't not need escape in this position
    THERMAL_LAW = r"[a-z][a-z\d/-]+\.\d+[a-z]"
    """
    An MCNP formatted thermal scattering law.

    e.g.: ``lwtr.20t``. 
    """

    @_(r"[+\-]?\d+(?!e)[a-z]+")
    def NUMBER_WORD(self, t):
        """
        An integer followed by letters.

        Can be used for library numbers, as well as shortcuts.

        E.g.: ``80c``, or ``15i``.
        """
        if update := self._parse_shortcut(t):
            update.type = f"NUM_{update.type}"
            return update
        return t

    @_(r"[+\-]?[0-9]+\.?[0-9]*E?[+\-]?[0-9]*", r"[+\-]?[0-9]*\.?[0-9]+E?[+\-]?[0-9]*")
    def NUMBER(self, t):
        """
        A float, or int number, including "fortran floats".
        """
        if fortran_float(t.value) == 0:
            t.type = "NULL"
        return t

    @_(r"[+\-]?[0-9]*\.?[0-9]*E?[+\-]?[0-9]*[ijrml]+[a-z\./]*", r"[a-z]+[a-z\./]*")
    def TEXT(self, t):
        """
        General text that covers shortcuts and Keywords.
        """
        if update := self._parse_shortcut(t):
            return update
        if t.value.lower() in self._KEYWORDS:
            t.type = "KEYWORD"
        return t

    NULL = r"0+"
    """
    Zero number.
    """

    @_(r"MESSAGE:.*\s")
    def MESSAGE(self, t):
        """
        A message block.
        """
        self.lineno += t.value.count("\n")
        return t

    _EXPRESSIONS = {
        "INTERPOLATE": re.compile(r"^\d*I$", re.I),
        "JUMP": re.compile(r"^\d*J$", re.I),
        "LOG_INTERPOLATE": re.compile(r"^\d*I?LOG$", re.I),
        "MULTIPLY": re.compile(r"^[+\-]?[0-9]+\.?[0-9]*E?[+\-]?[0-9]*M$", re.I),
        "REPEAT": re.compile(r"^\d*R$", re.I),
    }

    def _parse_shortcut(self, t):
        for token_type, expression in self._EXPRESSIONS.items():
            if expression.match(t.value):
                t.type = token_type
                return t

    INTERPOLATE = r"\d*I"
    """
    An interpolate shortcut.
    """
    NUM_INTERPOLATE = r"\d+I"
    """
    An interpolate shortcut with a number.
    """

    JUMP = r"\d*J"
    """
    A jump shortcut.
    """

    NUM_JUMP = r"\d+J"
    """
    A jump shortcut with a number.
    """

    LOG_INTERPOLATE = r"\d*I?LOG"
    """
    A logarithmic interpolate shortcut.
    """

    NUM_LOG_INTERPOLATE = r"\d+I?LOG"
    """
    A logarithmic interpolate shortcut.
    """

    MULTIPLY = r"[+\-]?[0-9]+\.?[0-9]*E?[+\-]?[0-9]*M"
    """
    A multiply shortcut.
    """

    NUM_MULTIPLY = r"[+\-]?[0-9]+\.?[0-9]*E?[+\-]?[0-9]*M"
    """
    A multiply shortcut with a number.
    """

    REPEAT = r"\d*R"
    """
    A repeat shortcut.
    """

    NUM_REPEAT = r"\d+R"
    """
    A repeat shortcut with a number.
    """

    FILE_PATH = r'[^><:"%,;=&\(\)|?*\s]+'
    """
    A file path that covers basically anything that windows or linux allows.
    """

    @staticmethod
    def find_column(text, token):
        """
        Calculates the column number for the start of this token.

        Uses 0-indexing.

        .. versionadded:: 0.2.0
            This was added with the major parser rework.


        :param text: the text being lexed.
        :type text: str
        :param token: the token currently being processed
        :type token: sly.lex.Token
        """
        last_cr = text.rfind("\n", 0, token.index)
        if last_cr < 0:
            last_cr = 0
        column = token.index - last_cr
        return column


class ParticleLexer(MCNP_Lexer):
    """
    A lexer for lexing an input that has particles in it.

    .. versionadded:: 0.2.0
        This was added with the major parser rework.

    """

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
        NUMBER_WORD,
        NULL,
        PARTICLE,
        PARTICLE_DESIGNATOR,
        REPEAT,
        SOURCE_COMMENT,
        SPACE,
        TALLY_COMMENT,
        TEXT,
        THERMAL_LAW,
        ZAID,
    }

    _PARTICLES = {
        "n",
        "p",
        "e",
        "|",
        "q",
        "u",
        "v",
        "f",
        "h",
        "l",
        "+",
        "-",
        "x",
        "y",
        "o",
        "!",
        "<",
        ">",
        "g",
        "/",
        "z",
        "k",
        "%",
        "^",
        "b",
        "_",
        "~",
        "c",
        "w",
        "@",
        "d",
        "t",
        "s",
        "a",
        "*",
        "?",
        "#",
    }

    @_(r"[+\-]?[0-9]*\.?[0-9]*E?[+\-]?[0-9]*[ijrml]+[a-z\./]*", r"[a-z]+[a-z\./]*")
    def TEXT(self, t):
        t = super().TEXT(t)
        if t.value.lower() in self._KEYWORDS:
            t.type = "KEYWORD"
        elif t.value.lower() in self._PARTICLES:
            t.type = "PARTICLE"
        return t


class CellLexer(ParticleLexer):
    """
    A lexer for cell inputs that allows particles.

    .. versionadded:: 0.2.0
        This was added with the major parser rework.

    """

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
        PARTICLE,
        PARTICLE_DESIGNATOR,
        REPEAT,
        SPACE,
        TEXT,
        THERMAL_LAW,
        ZAID,
    }


class DataLexer(ParticleLexer):
    """
    A lexer for data inputs.

    .. versionadded:: 0.2.0
        This was added with the major parser rework.

    """

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
        PARTICLE,
        PARTICLE_DESIGNATOR,
        REPEAT,
        SOURCE_COMMENT,
        SPACE,
        TALLY_COMMENT,
        TEXT,
        THERMAL_LAW,
        ZAID,
    }

    @_(r"([|+\-!<>/%^_~@\*\?\#]|\#\d*)+")
    def PARTICLE_SPECIAL(self, t):
        """
        Particle designators that are special characters.
        """
        return t


class SurfaceLexer(MCNP_Lexer):
    """
    A lexer for Surface inputs.

    The main difference is that ``p`` will be interpreted as a plane,
    and not a photon.

    .. versionadded:: 0.2.0
        This was added with the major parser rework.

    """

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
        NUMBER_WORD,
        NULL,
        REPEAT,
        SPACE,
        SURFACE_TYPE,
        TEXT,
        THERMAL_LAW,
        ZAID,
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
    """
    All allowed surface types.
    """

    @_(r"[+\-]?[0-9]*\.?[0-9]*E?[+\-]?[0-9]*[ijrml]+[a-z\./]*", r"[a-z]+[a-z\./]*")
    def TEXT(self, t):
        t = super().TEXT(t)
        if t.value.lower() in self._SURFACE_TYPES:
            t.type = "SURFACE_TYPE"
        return t

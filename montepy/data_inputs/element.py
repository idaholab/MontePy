# Copyright 2024, Battelle Energy Alliance, LLC All Rights Reserved.
from montepy.errors import *


class Element:
    """
    Class to represent an element e.g., Aluminum.

    :param Z: the Z number of the element
    :type Z: int
    :raises UnknownElement: if there is no element with that Z number.
    """

    def __init__(self, Z):
        self._Z = Z
        if Z not in self.__Z_TO_SYMBOL:
            raise UnknownElement(f"Z={Z}")

    @property
    def symbol(self):
        """
        The atomic symbol for this Element.

        :returns: the atomic symbol
        :rtype: str
        """
        return self.__Z_TO_SYMBOL[self.Z]

    @property
    def Z(self):
        """
        The atomic number for this Element.

        :returns: the atomic number
        :rtype: int
        """
        return self._Z

    @property
    def name(self):
        """
        The name of the element.

        :returns: the element's name.
        :rtype: str
        """
        return self.__ELEMENT_NAMES[self.symbol]

    def __str__(self):
        return self.name

    def __repr__(self):
        return f"Z={self.Z}, symbol={self.symbol}, name={self.name}"

    def __hash__(self):
        return hash(self.Z)

    def __eq__(self, other):
        return self.Z == other.Z

    @classmethod
    def get_by_symbol(cls, symbol):
        """
        Get an element by it's symbol.

        E.g., get the element with Z=1 from "H".

        :returns: the element with this symbol
        :rtype: Element
        :raises UnknownElement: if there is no element with that symbol.
        """
        try:
            Z = cls.__SYMBOL_TO_Z[symbol]
            return cls(Z)
        except KeyError:
            raise UnknownElement(f"The symbol: {symbol}")

    @classmethod
    def get_by_name(cls, name):
        """
        Get an element by it's name.

        E.g., get the element with Z=1 from "hydrogen".

        :returns: the element with this name
        :rtype: Element
        :raises UnknownElement: if there is no element with that name.
        """
        try:
            symbol = cls.__NAMES_TO_SYMBOLS[name]
            return cls.get_by_symbol(symbol)
        except KeyError:
            raise UnknownElement(f"The name: {name}")

    __Z_TO_SYMBOL = {
        1: "H",
        2: "He",
        3: "Li",
        4: "Be",
        5: "B",
        6: "C",
        7: "N",
        8: "O",
        9: "F",
        10: "Ne",
        11: "Na",
        12: "Mg",
        13: "Al",
        14: "Si",
        15: "P",
        16: "S",
        17: "Cl",
        18: "Ar",
        19: "K",
        20: "Ca",
        21: "Sc",
        22: "Ti",
        23: "V",
        24: "Cr",
        25: "Mn",
        26: "Fe",
        27: "Co",
        28: "Ni",
        29: "Cu",
        30: "Zn",
        31: "Ga",
        32: "Ge",
        33: "As",
        34: "Se",
        35: "Br",
        36: "Kr",
        37: "Rb",
        38: "Sr",
        39: "Y",
        40: "Zr",
        41: "Nb",
        42: "Mo",
        43: "Tc",
        44: "Ru",
        45: "Rh",
        46: "Pd",
        47: "Ag",
        48: "Cd",
        49: "In",
        50: "Sn",
        51: "Sb",
        52: "Te",
        53: "I",
        54: "Xe",
        55: "Cs",
        56: "Ba",
        57: "La",
        58: "Ce",
        59: "Pr",
        60: "Nd",
        61: "Pm",
        62: "Sm",
        63: "Eu",
        64: "Gd",
        65: "Tb",
        66: "Dy",
        67: "Ho",
        68: "Er",
        69: "Tm",
        70: "Yb",
        71: "Lu",
        72: "Hf",
        73: "Ta",
        74: "W",
        75: "Re",
        76: "Os",
        77: "Ir",
        78: "Pt",
        79: "Au",
        80: "Hg",
        81: "Tl",
        82: "Pb",
        83: "Bi",
        84: "Po",
        85: "At",
        86: "Rn",
        87: "Fr",
        88: "Ra",
        89: "Ac",
        90: "Th",
        91: "Pa",
        92: "U",
        93: "Np",
        94: "Pu",
        95: "Am",
        96: "Cm",
        97: "Bk",
        98: "Cf",
        99: "Es",
        100: "Fm",
        101: "Md",
        102: "No",
        103: "Lr",
        104: "Rf",
        105: "Db",
        106: "Sg",
        107: "Bh",
        108: "Hs",
        109: "Mt",
        110: "Ds",
        111: "Rg",
        112: "Cn",
        113: "Nh",
        114: "Fl",
        115: "Mc",
        116: "Lv",
        117: "Ts",
        118: "Og",
    }
    __SYMBOL_TO_Z = {}
    for __Z, __symbol in __Z_TO_SYMBOL.items():
        __SYMBOL_TO_Z[__symbol] = __Z
    del __Z, __symbol
    __ELEMENT_NAMES = {
        "H": "hydrogen",
        "He": "helium",
        "Li": "lithium",
        "Be": "beryllium",
        "B": "boron",
        "C": "carbon",
        "N": "nitrogen",
        "O": "oxygen",
        "F": "fluorine",
        "Ne": "neon",
        "Na": "sodium",
        "Mg": "magnesium",
        "Al": "aluminum",
        "Si": "silicon",
        "P": "phosphorus",
        "S": "sulfur",
        "Cl": "chlorine",
        "Ar": "argon",
        "K": "potassium",
        "Ca": "calcium",
        "Sc": "scandium",
        "Ti": "titanium",
        "V": "vanadium",
        "Cr": "chromium",
        "Mn": "manganese",
        "Fe": "iron",
        "Co": "cobalt",
        "Ni": "nickel",
        "Cu": "copper",
        "Zn": "zinc",
        "Ga": "gallium",
        "Ge": "germanium",
        "As": "arsenic",
        "Se": "selenium",
        "Br": "bromine",
        "Kr": "krypton",
        "Rb": "rubidium",
        "Sr": "strontium",
        "Y": "yttrium",
        "Zr": "zirconium",
        "Nb": "niobium",
        "Mo": "molybdenum",
        "Tc": "technetium",
        "Ru": "ruthenium",
        "Rh": "rhodium",
        "Pd": "palladium",
        "Ag": "silver",
        "Cd": "cadmium",
        "In": "indium",
        "Sn": "tin",
        "Sb": "antimony",
        "Te": "tellurium",
        "I": "iodine",
        "Xe": "xenon",
        "Cs": "cesium",
        "Ba": "barium",
        "La": "lanthanum",
        "Ce": "cerium",
        "Pr": "praseodymium",
        "Nd": "neodymium",
        "Pm": "promethium",
        "Sm": "samarium",
        "Eu": "europium",
        "Gd": "gadolinium",
        "Tb": "terbium",
        "Dy": "dysprosium",
        "Ho": "holmium",
        "Er": "erbium",
        "Tm": "thulium",
        "Yb": "ytterbium",
        "Lu": "lutetium",
        "Hf": "hafnium",
        "Ta": "tantalum",
        "W": "tungsten",
        "Re": "rhenium",
        "Os": "osmium",
        "Ir": "iridium",
        "Pt": "platinum",
        "Au": "gold",
        "Hg": "mercury",
        "Tl": "thallium",
        "Pb": "lead",
        "Bi": "bismuth",
        "Po": "polonium",
        "At": "astatine",
        "Rn": "radon",
        "Fr": "francium",
        "Ra": "radium",
        "Ac": "actinium",
        "Th": "thorium",
        "Pa": "protactinium",
        "U": "uranium",
        "Np": "neptunium",
        "Pu": "plutonium",
        "Am": "americium",
        "Cm": "curium",
        "Bk": "berkelium",
        "Cf": "californium",
        "Es": "einsteinium",
        "Fm": "fermium",
        "Md": "mendelevium",
        "No": "nobelium",
        "Lr": "lawrencium",
        "Rf": "rutherfordium",
        "Db": "dubnium",
        "Sg": "seaborgium",
        "Bh": "bohrium",
        "Hs": "hassium",
        "Mt": "meitnerium",
        "Ds": "darmstradtium",
        "Rg": "roentgenium",
        "Cn": "copernicium",
        "Nh": "nihonium",
        "Fl": "flerovium",
        "Mc": "Moscovium",
        "Lv": "livermorium",
        "Ts": "tenessine",
        "Og": "oganesson",
    }

    __NAMES_TO_SYMBOLS = {}
    for __symbol, __name in __ELEMENT_NAMES.items():
        __NAMES_TO_SYMBOLS[__name] = __symbol
    del __symbol, __name

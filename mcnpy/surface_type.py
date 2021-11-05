from enum import unique, Enum


@unique
class SurfaceType(str, Enum):
    # planes
    P = "P"
    PX = "PX"
    PY = "PY"
    PZ = "PZ"
    # spheres
    SO = "SO"
    S = "S"
    SX = "SX"
    SY = "SY"
    SZ = "SZ"
    # cylinder
    C_X = "C/X"
    C_Y = "C/Y"
    C_Z = "C/Z"
    CX = "CX"
    CY = "CY"
    CZ = "CZ"
    # cone
    K_X = "K/X"
    K_Y = "K/Y"
    K_Z = "K/Z"
    KX = "KX"
    KY = "KY"
    KZ = "KZ"
    # generalized 3D conics
    SQ = "SQ"
    GQ = "GQ"
    # Torus
    TX = "TX"
    TY = "TY"
    TZ = "TZ"
    # by points
    X = "X"
    Y = "Y"
    Z = "Z"
    # macrobodies
    BOX = "BOX"
    RPP = "RPP"
    SPH = "SPH"
    RCC = "RCC"
    RHP = "RHP"
    HEX = "HEX"
    REC = "REC"
    TRC = "TRC"
    ELL = "ELL"
    WED = "WED"
    ARB = "ARB"

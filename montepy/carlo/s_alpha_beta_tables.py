# Copyright 2026, Battelle Energy Alliance, LLC All Rights Reserved.

"""Map OpenMC thermal scattering names to MCNP S(a,b) identifiers using the LANL suffix convention.

AI disclosure:
  Harness:   Claude Desktop (Government)
  Model:     Claude Opus 5.5
  Reasoning: High

Sources:
        LA-UR-17-20709 (legacy, SAB2002, ENDF70SaB, ENDF71SaB)
        LA-UR-20-30460 (ENDF80SaB2)
        LA-UR-25-29086 (ENDF81SaB)
"""

import re

# Old-style names shared by lanl89/tmccs (.0Xt), ENDF70SaB (.1Xt), ENDF71SaB (.2Xt) and SAB2002 (.6Xt)
_LEGACY = {
    "c_Al27": "al27",
    "c_Be": "be",
    "c_BeO": "beo",
    "c_Be_in_BeO": "be/o",
    "c_C6H6": "benz",
    "c_D_in_D2O": "hwtr",
    "c_Fe56": "fe56",
    "c_Graphite": "grph",
    "c_H_in_CH2": "poly",
    "c_H_in_CH4_liquid": "lmeth",
    "c_H_in_CH4_solid": "smeth",
    "c_H_in_H2O": "lwtr",
    "c_H_in_ZrH": "h/zr",
    "c_O_in_BeO": "o/be",
    "c_O_in_UO2": "o2/u",
    "c_SiO2_alpha": "sio2",  # ENDF71SaB only; alpha/beta phase not verified
    "c_U_in_UO2": "u/o2",
    "c_Zr_in_ZrH": "zr/h",
    "c_ortho_D": "dortho",
    "c_ortho_H": "hortho",
    "c_para_D": "dpara",
    "c_para_H": "hpara",
}

_ENDF80 = {
    "c_Al27": "al-27",
    "c_Be": "be-met",
    "c_Be_in_BeO": "be-beo",
    "c_C6H6": "benz",
    "c_C_in_SiC": "c-sic",
    "c_D_in_D2O": "d-d2o",
    "c_Fe56": "fe-56",
    "c_Graphite": "grph",
    "c_Graphite_10p": "grph10",
    "c_Graphite_30p": "grph30",
    "c_H_in_C5O2H8": "h-luci",
    "c_H_in_CH2": "h-poly",
    "c_H_in_CH4_liquid": "lmeth",
    "c_H_in_CH4_solid": "smeth",
    "c_H_in_H2O": "h-h2o",
    "c_H_in_H2O_solid": "h-ice",
    "c_H_in_YH2": "h-yh2",
    "c_H_in_ZrH": "h-zrh",
    "c_N_in_UN": "n-un",
    "c_O_in_BeO": "o-beo",
    "c_O_in_D2O": "o-d2o",
    "c_O_in_H2O_solid": "o-ice",
    "c_O_in_UO2": "o-uo2",
    "c_SiO2_beta": "sio2",
    "c_Si_in_SiC": "si-sic",
    "c_U_in_UN": "u-un",
    "c_U_in_UO2": "u-uo2",
    "c_Y_in_YH2": "y-yh2",
    "c_Zr_in_ZrH": "zr-zrh",
    "c_ortho_D": "orthod",
    "c_ortho_H": "orthoh",
    "c_para_D": "parad",
    "c_para_H": "parah",
}

# ENDF81SaB: ENDF80SaB2 minus the evaluations LANL did not reprocess, plus the VIII.1 additions
_ENDF81 = dict(_ENDF80)
for _key in (
    "c_C6H6",
    "c_H_in_CH4_liquid",
    "c_H_in_CH4_solid",
    "c_H_in_ZrH",
    "c_SiO2_beta",
    "c_Zr_in_ZrH",
):
    del _ENDF81[_key]
_ENDF81.update(
    {
        "c_Al_in_Al2O3": "al-sap",
        "c_Be_distinct": "be-met",
        "c_Be_in_Be2C": "be-bec",
        "c_Be_in_BeF2": "be-bef",
        "c_Be_in_FLiBe": "be-flb",
        "c_C_in_Be2C": "c-bec",
        "c_C_in_C5O2H8": "c-luci",
        "c_C_in_C8H8": "c-styr",
        "c_C_in_CF2": "c-ptfe",
        "c_C_in_ZrC": "c-zrc",
        "c_D_in_7LiD": "d-7ld",
        "c_F_in_Be2": "f-bef",  # OpenMC key is misspelled (should be c_F_in_BeF2)
        "c_F_in_CF2": "f-ptfe",
        "c_F_in_FLiBe": "f-flb",
        "c_F_in_HF": "f-hf",
        "c_F_in_MgF2": "f-mgf",
        "c_Graphite_distinct": "grph",
        "c_Graphite_20p": "grph20",
        "c_H_in_7LiH": "h-7lh",
        "c_H_in_C8H8": "h-styr",
        "c_H_in_HF": "h-hf",
        "c_H_in_ParaffinicOil": "h-poil",
        "c_H_in_UH3": "h-uh3",
        "c_H_in_ZrH2": "h-ezh",
        "c_H_in_ZrHx": "h-dzh",
        "c_Li_in_7LiD": "7l-7ld",
        "c_Li_in_7LiH": "7l-7lh",
        "c_Li_in_FLiBe": "li-flb",
        "c_Mg_in_MgF2": "mg-mgf",
        "c_Mg_in_MgO": "mg-mgo",
        "c_O_in_Al2O3": "o-sap",
        "c_O_in_C5O2H8": "o-luci",
        "c_O_in_MgO": "o-mgo",
        "c_O_in_PuO2": "o-puo",
        "c_O_in_SiO2_alpha": "o-aqu",
        "c_Pu_in_PuO2": "pu-puo",
        "c_Si_in_SiO2_alpha": "si-aqu",
        "c_Zr_in_ZrC": "zr-zrc",
        "c_Zr_in_ZrH2": "zr-ezh",
        "c_Zr_in_ZrHx": "zr-dzh",
    }
)

# ENDF81SaB enrichment index: 1 natural, 2 5%, 3 10%, 4 19.75%, 5 93%, 6 100% U-235.
# Index 1 overwrites the unnumbered ENDF80SaB2 names (u-uo2, o-uo2, u-un, n-un).
for _i, _tag in enumerate(("", "_5p", "_10p", "_HALEU", "_HEU", "_100p"), 1):
    _ENDF81[f"c_C_in_UC{_tag}"] = f"c-uc{_i}"
    _ENDF81[f"c_N_in_UN{_tag}"] = f"n-un{_i}"
    _ENDF81[f"c_O_in_UO2{_tag}"] = f"o-uo{_i}"
    _ENDF81[f"c_U_in_UC{_tag}"] = f"u-uc{_i}"
    _ENDF81[f"c_U_in_UN{_tag}"] = f"u-un{_i}"
    _ENDF81[f"c_U_in_UO2{_tag}"] = f"u-uo{_i}"
    _ENDF81[f"c_U_metal{_tag}"] = f"u-met{_i}"

# ENDF81SaB splits grph and be-met: Sd-effect evaluations first, traditional evaluations second
_ENDF81_SUBRANGES = {
    "c_Be": range(80, 91),
    "c_Be_distinct": range(70, 80),
    "c_Graphite": range(80, 90),
    "c_Graphite_distinct": range(70, 78),
}

_LIBRARIES = (
    (range(0, 29), "lanl89/tmccs/ENDF70SaB/ENDF71SaB", _LEGACY),
    (range(40, 58), "ENDF80SaB2", _ENDF80),
    (range(60, 67), "SAB2002", _LEGACY),
    (range(70, 91), "ENDF81SaB", _ENDF81),
)

_SUFFIX = re.compile(r"^\.?(\d{2})t?$", re.IGNORECASE)


def mcnp_sab_name(openmc_name, suffix):
    """Return the MCNP S(a,b) identifier, e.g. ("c_H_in_H2O", ".40t") -> "h-h2o.40t".

    Raises ValueError for an unrecognized suffix and KeyError when the library has no table for the material.
    The result follows the naming convention only; it does not guarantee the table exists at that temperature index.
    """
    match = _SUFFIX.match(suffix.strip())
    if match is None:
        raise ValueError(f"Invalid S(a,b) suffix: {suffix!r}")
    number = int(match.group(1))
    for numbers, library, table in _LIBRARIES:
        if number in numbers:
            break
    else:
        raise ValueError(
            f"Suffix .{number:02d}t does not belong to a known LANL S(a,b) library"
        )
    if openmc_name not in table:
        raise KeyError(f"{openmc_name} has no table in {library}")
    allowed = _ENDF81_SUBRANGES.get(openmc_name) if table is _ENDF81 else None
    if allowed is not None and number not in allowed:
        raise KeyError(
            f"{openmc_name} in {library} uses .{allowed[0]}t to .{allowed[-1]}t, got .{number:02d}t",
        )
    return f"{table[openmc_name]}.{number:02d}t"

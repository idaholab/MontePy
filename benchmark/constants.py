import montepy

import numpy as np


"""
These data were aggregated from a subset of MCNP models included in the following projects:

Nuclear Energy Agency (2020). Internationl Handbook of Evaluated criticality Safety Benchmark Experiments. 
    Paris, OECD Nuclear Energy Agency.

Nuclear Energy Agency (2023). International Handbook of Evaluated Reactor Physics Benchmark Experiments, 
    Nuclear Energy Agency, Organisation for Economic Co-operation and Development.
"""

SURF_ABOVE_CURVE = lambda: np.random.binomial(1, 0.949)

SURF_TOP_CURVE = lambda x: 1.45 * x**0.93

SURF_BOT_CURVE = lambda x: 12.62 * x**0.40

MATERIAL_CURVE = lambda x: 1.48 * x**0.43

OBJ_NUMBER = lambda: np.random.randint(1, 99_999_999)

ATOM_MASS_DENSITY = lambda: np.random.binomial(1, 0.5)


def MASS_DENSITY():
    sample = np.random.normal(5.0, 1.0)
    return sample if sample > 0.0 else 0.001


def ATOM_DENSITY():
    sample = np.random.normal(0.01, 1e-3)
    return sample if sample > 0.0 else 0.001


GEOM_OP = lambda: np.random.choice(
    [
        montepy.Operator.INTERSECTION,
        montepy.Operator.UNION,
        montepy.Operator.COMPLEMENT,
    ],
    p=[0.9879, 0.004132, 6.1e-4],
)


def N_CELLS_NOISE(n):
    new_n = np.round(np.random.normal(n, 0.05 * n))
    new_n = 1 if new_n < 0 else new_n
    return int(new_n)


_st = montepy.SurfaceType
_p = np.array(
    [
        0.387353,
        0.169831,
        0.127609,
        0.093485,
        0.062539,
        0.053166,
        0.047198,
        0.022552,
        0.006978,
        6.458e-3,
        4.969e-3,
        4.191e-3,
        3.942e-3,
        3.446e-3,
        1.802e-3,
        1.415e-3,
        1.012e-3,
        5.62e-4,
        5.28e-4,
        4.99e-4,
        1.70e-4,
        1.57e-4,
        1.16e-4,
        2.1e-5,
    ]
)
_p = _p / np.sum(_p)
SURF_TYPE = lambda: np.random.choice(
    [
        _st.PZ,
        _st.CZ,
        _st.SO,
        _st.PX,
        _st.PY,
        _st.C_Z,
        _st.RCC,
        _st.P,
        _st.RPP,
        _st.CX,
        _st.C_Y,
        _st.SPH,
        _st.C_X,
        _st.SX,
        _st.Z,
        _st.CY,
        _st.KZ,
        _st.BOX,
        _st.RHP,
        _st.SY,
        _st.SQ,
        _st.SZ,
        _st.TRC,
        _st.S,
    ],
    p=_p,
)

NUM_CONSTANTS = {
    _st.PZ: 1,
    _st.CZ: 1,
    _st.SO: 1,
    _st.PX: 1,
    _st.PY: 1,
    _st.C_Z: 3,
    _st.RCC: 7,
    _st.P: 4,
    _st.RPP: 6,
    _st.CX: 1,
    _st.C_Y: 3,
    _st.SX: 2,
    _st.Z: 9,
    _st.CY: 3,
    _st.KZ: 3,
    _st.BOX: 12,
    _st.RHP: 15,
    _st.SY: 2,
    _st.SQ: 10,
    _st.SZ: 2,
    _st.TRC: 8,
    _st.S: 4,
}
SURFACE_CONSTANT = lambda: np.round(
    np.random.uniform(0.0, 15.0), np.random.randint(1, 8)
)

USES_UNIVERSES = lambda: np.random.binomial(1, 0.3234)

NUM_SURFS_IN_CELL = lambda: np.random.exponential(4.1599)

CELL_GEOM_COMP = lambda: np.random.binomial(1, 7.728e-3)

CELL_GEOM_INTERSECT = lambda: np.random.binomial(1, 0.987911)

CELL_GEOM_SIDE = lambda: np.random.binomial(1, 0.46007)

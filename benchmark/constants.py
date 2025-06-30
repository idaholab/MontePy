import montepy

import numpy as np


"""
These data were aggregated from a subset of MCNP models included in the following projects:

Nuclear Energy Agency (2020). Internationl Handbook of Evaluated criticality Safety Benchmark Experiments. 
    Paris, OECD Nuclear Energy Agency.

Nuclear Energy Agency (2023). International Handbook of Evaluated Reactor Physics Benchmark Experiments, 
    Nuclear Energy Agency, Organisation for Economic Co-operation and Development.
"""

SURF_ABOVE_CURVE = np.random.binomial(1, 0.949)

SURF_TOP_CURVE = lambda x: 1.45 * x**0.93

SURF_BOT_CURVE = lambda x: 12.62 * x**0.40

MATERIAL_CURVE = lambda x: 1.48 * x**0.43

GEOM_OP = lambda: np.random.choice(
    [
        montepy.Operator.INTERSECTION,
        montepy.Operator.UNION,
        montepy.Operator.COMPLEMENT,
    ],
    p=[0.9879, 0.004132, 6.1e-4],
)

_st = montepy.SurfaceType

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
    p=[
        0.3874,
        0.1698,
        0.1276,
        0.0935,
        0.06254,
        0.0532,
        0.0472,
        0.0226,
        0.00698,
        6.46e-3,
        4.97e-3,
        4.19e-3,
        3.943e-3,
        1.80e-3,
        1.42e-3,
        1.01e-3,
        5.62e-4,
        5.28e-4,
        4.99e-4,
        1.7e-4,
        1.57e-4,
        1.16e-4,
        2.1e-5,
    ],
)

USES_UNIVERSES = np.random.binomial(1, 0.3234)

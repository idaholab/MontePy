# Copyright 2025, Battelle Energy Alliance, LLC All Rights Reserved.

import montepy
import pytest
import numpy as np


def test_cell_integral():
    montepy.Cell(number=3)
    montepy.Cell(number=np.uint8(1))
    with pytest.raises(TypeError):
        montepy.Cell(number=5.0)


def test_cell_real():
    c = montepy.Cell()
    c.atom_density = 1
    c.mass_density = np.float32(1.2e-3)


def test_surf_coeff_real():
    cx = montepy.CylinderParAxis()
    cx.coordinates = (0, np.int16(-1.23))

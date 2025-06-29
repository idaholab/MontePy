from montepy._check_value import *

from numbers import Real, Integral
from typing import Annotated


"""
Common types to be used for type annotations.
"""

PositiveInt = Annotated[Integral, positive]
r"""
An integer that is positive, i.e., a member of the set :math:`\mathbb{Z}_{\gt0}`.
"""

NegativeInt = Annotated[Integral, negative]
r"""
An integer that is negative, i.e., a member of the set :math:`\mathbb{Z}_{\lt0}`.
"""

PositiveReal = Annotated[Real, positive]
r"""
A real number that is positive, i.e., a member of the set :math:`\mathbb{R}_{\gt0}`.
"""

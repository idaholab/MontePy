from montepy._check_value import *

from numbers import Real, Integral
from typing import Annotated

type PositiveInt = Annotated[Integral, positive]

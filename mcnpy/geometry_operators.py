from enum import Enum


class Operator(Enum):
    INTERSECTION = "*"
    UNION = ":"
    COMPLEMENT = "#"
    SHIFT = ">"

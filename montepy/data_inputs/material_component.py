# Copyright 2024, Battelle Energy Alliance, LLC All Rights Reserved.


class MaterialComponent:
    """
    A class to represent a single component in a material.

    For example: this may be H-1 in water: like 1001.80c — 0.6667

    :param isotope: the Isotope object representing this isotope
    :type isotope: Isotope
    :param fraction: the fraction of this component in the material
    :type fraction: ValueNode
    """

    def __init__(self, isotope, fraction):
        raise DeprecationWarning(
            f"""MaterialComponent is deprecated, and has been removed in MontePy 1.0.0.
See <https://www.montepy.org/migrations/migrate0_1.html> for more information """,
        )

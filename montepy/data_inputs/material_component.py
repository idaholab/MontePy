# Copyright 2024, Battelle Energy Alliance, LLC All Rights Reserved.
from montepy.data_inputs.isotope import Isotope
from montepy.input_parser.syntax_node import PaddingNode, ValueNode
from montepy.utilities import make_prop_val_node

import warnings


def _enforce_positive(self, val):
    if val <= 0:
        raise ValueError(f"material component fraction must be > 0. {val} given.")


class MaterialComponent:
    """
    A class to represent a single component in a material.

    For example: this may be H-1 in water: like 1001.80c — 0.6667

    .. deprecated:: 0.4.1
        MaterialComponent has been deprecated as part of a redesign for the material
        interface due to a critical bug in how MontePy handles duplicate nuclides.
        See :ref:`migrate 0 1`.

    :param isotope: the Isotope object representing this isotope
    :type isotope: Isotope
    :param fraction: the fraction of this component in the material
    :type fraction: ValueNode
    :param suppress_warning: Whether to suppress the ``DeprecationWarning``.
    :type suppress_warning: bool
    """

    def __init__(self, isotope, fraction, suppress_warning=False):
        if not suppress_warning:
            warnings.warn(
                f"""MaterialComponent is deprecated, and will be removed in MontePy 1.0.0.
See <https://www.montepy.org/migrations/migrate0_1.html> for more information """,
                DeprecationWarning,
            )
        if not isinstance(isotope, Isotope):
            raise TypeError(f"Isotope must be an Isotope. {isotope} given")
        if isinstance(fraction, (float, int)):
            fraction = ValueNode(str(fraction), float, padding=PaddingNode(" "))
        elif not isinstance(fraction, ValueNode) or not isinstance(
            fraction.value, float
        ):
            raise TypeError(f"fraction must be float ValueNode. {fraction} given.")
        self._isotope = isotope
        self._tree = fraction
        if fraction.value < 0:
            raise ValueError(f"Fraction must be > 0. {fraction.value} given.")
        self._fraction = fraction

    @property
    def isotope(self):
        """
        The isotope for this material_component

        :rtype: Isotope
        """
        return self._isotope

    @make_prop_val_node("_fraction", (float, int), float, _enforce_positive)
    def fraction(self):
        """
        The fraction of the isotope for this component

        :rtype: float
        """
        pass

    def __str__(self):
        return f"{self.isotope} {self.fraction}"

    def __repr__(self):
        return f"{self.isotope} {self.fraction}"

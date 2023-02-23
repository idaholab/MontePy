from mcnpy.data_inputs.isotope import Isotope
from mcnpy.input_parser.syntax_node import PaddingNode, ValueNode


class MaterialComponent:
    """
    A class to represent a single component in a material.

    For example: this may be H-1 in water: like 1001.80c -0.6667

    :param isotope: the Isotope object representing this isotope
    :type isotope: Isotope
    :param fraction: the fraction of this component in the material
    :type fraction: ValueNode
    """

    def __init__(self, isotope, fraction):
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

    @property
    def fraction(self):
        """
        The fraction of the isotope for this component

        :rtype: float
        """
        return self._fraction

    def __str__(self):
        return f"{self.isotope} {self.fraction}"

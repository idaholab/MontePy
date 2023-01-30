from mcnpy.data_inputs.isotope import Isotope
from mcnpy.input_parser.syntax_node import ValueNode


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
        if not isinstance(fraction, ValueNode) or not isinstance(fraction.value, float):
            raise TypeError(f"fraction must be float ValueNode. {fraction} given.")
        self._isotope = isotope
        self._tree = fraction
        fraction = fraction.value
        if not isinstance(fraction, float):
            raise TypeError("fraction must be a float")
        self._fraction = abs(fraction)

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

class MaterialComponent:
    """
    A class to represent a single component in a material.

    For example: this may be H-1 in water: like 1001.80c -0.6667

    :param isotope: the Isotope object representing this isotope
    :type isotope: Isotope
    :param fraction: the fraction of this component in the material
    :type fraction: float
    """

    def __init__(self, isotope, fraction):
        self._isotope = isotope
        if not isinstance(fraction, float):
            raise TypeError("fraction must be a float")
        if fraction <= 0:
            raise ValueError("fraction must be > 0.0")
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

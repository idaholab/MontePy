
class MaterialComponent:
    """
    A class to represent a single component in a material.

    For example: this may be H-1 in water: like 1001.80c -0.6667
    """

    def __init__(self, isotope, fraction):
        """
        :param isotope: the Isotope object representing this isotope
        :type isotope: Isotope
        :param fraction: the fraction of this component in the material
        :type fraction: float
        """
        self.__isotope = isotope
        assert isinstance(fraction, float)
        assert fraction > 0
        self.__fraction = fraction

    @property
    def isotope(self):
        """
        The isotope for this material_component
        :rtype: Isotope
        """
        return self.__isotope

    @property
    def fraction(self):
        """
        The fraction of the isotope for this component
        :rtype: float
        """
        return self.__fraction

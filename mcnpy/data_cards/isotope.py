from mcnpy.data_cards.element import Element
from mcnpy.errors import *


class Isotope:
    """
    A class to represent an MCNP isotope
    """

    def __init__(self, ZAID):
        """
        :param ZAID: the MCNP isotope identifier
        :type ZAID: str
        """
        if "." in ZAID:
            parts = ZAID.split(".")
            try:
                assert len(parts) == 2
                int(parts[0])
            except (AssertionError, ValueError) as e:
                raise ValueError(f"ZAID: {ZAID} could not be parsed as a valid isotope")
            self._ZAID = parts[0]
            ZAID = int(parts[0])
            self._Z = int(ZAID / 1000)
            self._element = Element(self.Z)
            self._A = int(ZAID % 1000)
            self._library = parts[1]
        else:
            raise MalformedInputError(ZAID, "Not a valid isotope identifier.")

    @property
    def ZAID(self):
        """
        The ZZZAAA identifier following MCNP convention

        :rtype: str
        """
        return self._ZAID

    @property
    def Z(self):
        """
        The Z number for this isotope.

        :returns: the atomic number.
        :rtype: int
        """
        return self._Z

    @property
    def A(self):
        """
        The A number for this isotope.

        :returns: the isotope's mass.
        :rtype: int
        """
        return self._A

    @property
    def element(self):
        """
        The base element for this isotope.

        :returns: The element for this isotope.
        :rtype: Element
        """
        return self._element

    @property
    def library(self):
        """
         The MCNP library identifier e.g. 80c

        :rtype: str
        """
        return self._library

    @library.setter
    def library(self, library):
        if not isinstance(library, str):
            raise TypeError("library must be a string")
        self._library = library

    def __str__(self):
        return f"{self.element.symbol}-{self.A}.{self._library}"

    def mcnp_str(self):
        """
        Returns an MCNP formatted representation.

        E.g., 1001.80c

        :returns: a string that can be used in MCNP
        :rtype: str
        """
        return f"{self.ZAID}.{self.library}"

    def __repr__(self):
        return f"ZAID={self.ZAID}, Z={self.Z}, A={self.A}, element={self.element}, library={self.library}"

    def __hash__(self):
        return hash(self._ZAID)

    def __lt__(self, other):
        return int(self.ZAID) < int(other.ZAID)

    def __format__(self, format_str):
        return str(self).__format__(format_str)

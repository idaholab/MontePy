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
        return f"{self._ZAID}.{self._library}"

    def __repr__(self):
        return self.__str__()

    def __hash__(self):
        return hash(self._ZAID)

    def __lt__(self, other):
        return int(self.ZAID) < int(other.ZAID)

    def __format__(self, format_str):
        return str(self).__format__(format_str)

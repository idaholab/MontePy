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
            assert len(parts) == 2
            int(parts[0])
            self.__ZAID = parts[0]
            self.__library = parts[1]
        else:
            raise MalformedInputError(ZAID, "Not a valid isotope identifier.")

    @property
    def ZAID(self):
        """
        The ZZZAAA identifier following MCNP convention
        :rtype: str
        """
        return self.__ZAID

    @property
    def library(self):
        """
        The MCNP library identifier e.g. 80c
        :rtype: str
        """
        return self.__library

    @library.setter
    def library(self, library):
        assert isinstance(library, str)
        self.__library = library

    def __str__(self):
        return f"{self.__ZAID}.{self.__library}"

    def __repr__(self):
        return self.__str__()

    def __hash__(self):
        return hash(self.__ZAID)

    def __lt__(self, other):
        return int(self.ZAID) < int(other.ZAID)

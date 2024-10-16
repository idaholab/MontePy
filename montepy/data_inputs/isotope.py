# Copyright 2024, Battelle Energy Alliance, LLC All Rights Reserved.
from montepy.data_inputs.element import Element
from montepy.errors import *
from montepy.input_parser.syntax_node import PaddingNode, ValueNode

import warnings


class Isotope:
    """
    A class to represent an MCNP isotope

    .. deprecated:: 0.4.1
        This will class is deprecated, and will be renamed: ``Nuclde``.
        For more details see the :ref:`migrate 0 1`.

    :param ZAID: the MCNP isotope identifier
    :type ZAID: str
    :param suppress_warning: Whether to suppress the ``FutureWarning``.
    :type suppress_warning: bool
    """

    #                   Cl-52      Br-101     Xe-150      Os-203    Cm-251     Og-296
    _BOUNDING_CURVE = [(17, 52), (35, 101), (54, 150), (76, 203), (96, 251), (118, 296)]
    _STUPID_MAP = {
        "95642": {"_is_metastable": False, "_meta_state": None},
        "95242": {"_is_metastable": True, "_meta_state": 1},
    }
    """
    Points on bounding curve for determining if "valid" isotope
    """

    def __init__(self, ZAID="", node=None, suppress_warning=False):
        if not suppress_warning:
            warnings.warn(
                "montepy.data_inputs.isotope.Isotope is deprecated and will be renamed: Nuclide.\n"
                "See <https://www.montepy.org/migrations/migrate0_1.html> for more information ",
                FutureWarning,
            )

        if node is not None and isinstance(node, ValueNode):
            if node.type == float:
                node = ValueNode(node.token, str, node.padding)
            self._tree = node
            ZAID = node.value
        parts = ZAID.split(".")
        try:
            assert len(parts) <= 2
            int(parts[0])
        except (AssertionError, ValueError) as e:
            raise ValueError(f"ZAID: {ZAID} could not be parsed as a valid isotope")
        self._ZAID = parts[0]
        self.__parse_zaid()
        if len(parts) == 2:
            self._library = parts[1]
        else:
            self._library = ""
        if node is None:
            self._tree = ValueNode(self.mcnp_str(), str, PaddingNode(" "))
        self._handle_stupid_legacy_stupidity()

    def _handle_stupid_legacy_stupidity(self):
        # TODO work on this for mat_redesign
        if self.ZAID in self._STUPID_MAP:
            stupid_overwrite = self._STUPID_MAP[self.ZAID]
            for key, value in stupid_overwrite.items():
                setattr(self, key, value)

    def __parse_zaid(self):
        """
        Parses the ZAID fully including metastable isomers.

        See Table 3-32 of LA-UR-17-29881

        """

        def is_probably_an_isotope(Z, A):
            for lim_Z, lim_A in self._BOUNDING_CURVE:
                if Z <= lim_Z:
                    if A <= lim_A:
                        return True
                    else:
                        return False
                else:
                    continue
            # if you are above Lv it's probably legit.
            return True

        ZAID = int(self._ZAID)
        self._Z = int(ZAID / 1000)
        self._element = Element(self.Z)
        A = int(ZAID % 1000)
        if not is_probably_an_isotope(self.Z, A):
            self._is_metastable = True
            true_A = A - 300
            # only m1,2,3,4 allowed
            found = False
            for i in range(1, 5):
                true_A -= 100
                # assumes that can only vary 40% from A = 2Z
                if is_probably_an_isotope(self.Z, true_A):
                    found = True
                    break
            if found:
                self._meta_state = i
                self._A = true_A
            else:
                raise ValueError(
                    f"ZAID: {ZAID} cannot be parsed as a valid metastable isomer. "
                    "Only isomeric state 1 - 4 are allowed"
                )

        else:
            self._is_metastable = False
            self._meta_state = None
            self._A = A

    @property
    def ZAID(self):
        """
        The ZZZAAA identifier following MCNP convention

        :rtype: int
        """
        # if this is made mutable this cannot be user provided, but must be calculated.
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
    def is_metastable(self):
        """
        Whether or not this is a metastable isomer.

        :returns: boolean of if this is metastable.
        :rtype: bool
        """
        return self._is_metastable

    @property
    def meta_state(self):
        """
        If this is a metastable isomer, which state is it?

        Can return values in the range [1,4] (or None). The exact state
        number is decided by who made the ACE file for this, and not quantum mechanics.
        Convention states that the isomers should be numbered from lowest to highest energy.

        :returns: the metastable isomeric state of this "isotope" in the range [1,4], or None
                if this is a ground state isomer.
        :rtype: int
        """
        return self._meta_state

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

    def __repr__(self):
        return f"{self.__class__.__name__}({repr(self.nuclide_str())})"

    def mcnp_str(self):
        """
        Returns an MCNP formatted representation.

        E.g., 1001.80c

        :returns: a string that can be used in MCNP
        :rtype: str
        """
        return f"{self.ZAID}.{self.library}" if self.library else self.ZAID

    def nuclide_str(self):
        meta_suffix = f"m{self.meta_state}" if self.is_metastable else ""
        suffix = f".{self._library}" if self._library else ""
        return f"{self.element.symbol}-{self.A}{meta_suffix}{suffix}"

    def get_base_zaid(self):
        """
        Get the ZAID identifier of the base isotope this is an isomer of.

        This is mostly helpful for working with metastable isomers.

        :returns: the mcnp ZAID of the ground state of this isotope.
        :rtype: int
        """
        return self.Z * 1000 + self.A

    def __str__(self):
        meta_suffix = f"m{self.meta_state}" if self.is_metastable else ""
        suffix = f" ({self._library})" if self._library else ""
        return f"{self.element.symbol:>2}-{self.A:<3}{meta_suffix:<2}{suffix}"

    def __hash__(self):
        return hash(self._ZAID)

    def __lt__(self, other):
        return int(self.ZAID) < int(other.ZAID)

    def __format__(self, format_str):
        return str(self).__format__(format_str)

# Copyright 2024, Battelle Energy Alliance, LLC All Rights Reserved.
from montepy.constants import MAX_ATOMIC_SYMBOL_LENGTH
from montepy.data_inputs.element import Element
from montepy.errors import *
from montepy.utilities import *
from montepy.input_parser.syntax_node import PaddingNode, ValueNode

import re
import warnings


class Library:
    def __init__(self, library):
        if not isinstance(library, str):
            raise TypeError(f"library must be a str. {library} given.")
        self._library = library

    @property
    def library(self):
        """"""
        return self._library

    def __hash__(self):
        return hash(self._library)

    def __eq__(self, other):
        if not isinstance(other, (type(self), str)):
            raise TypeError(f"Can only compare Library instances.")
        if isinstance(other, type(self)):
            return self.library == other.library
        return self.library == other

    def __str__(self):
        return self.library

    def __repr__(self):
        return str(self)


_ZAID_A_ADDER = 1000


class Nuclide:
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

    _NAME_PARSER = re.compile(
        rf"""(
                (?P<ZAID>\d{4,6})|
                ((?P<element>[a-z]{{1,{MAX_ATOMIC_SYMBOL_LENGTH}}})-?(?P<A>\d*))
            )
            (m(?P<meta>\d+))?
            (\.(?P<library>\d{2,}[a-z]+))?""",
        re.I | re.VERBOSE,
    )
    """"""

    def __init__(
        self,
        ZAID="",
        element=None,
        Z=None,
        A=None,
        meta_state=None,
        library="",
        node=None,
    ):
        self._library = Library("")
        self._ZAID = None

        if node is not None and isinstance(node, ValueNode):
            if node.type == float:
                node = ValueNode(node.token, str, node.padding)
            self._tree = node
            ZAID = node.value
        if ZAID:
            parts = ZAID.split(".")
            try:
                assert len(parts) <= 2
                int(parts[0])
            except (AssertionError, ValueError) as e:
                raise ValueError(f"ZAID: {ZAID} could not be parsed as a valid isotope")
            self._ZAID = parts[0]
            new_vals = self._parse_zaid(int(self._ZAID))
            for key, value in new_vals.items():
                setattr(self, key, value)
            if len(parts) == 2:
                self._library = Library(parts[1])
            else:
                self._library = Library("")
        elif element is not None:
            if not isinstance(element, Element):
                raise TypeError(
                    f"Only type Element is allowed for element argument. {element} given."
                )
            self._element = element
            self._Z = self._element.Z
        elif Z is not None:
            if not isinstance(Z, int):
                raise TypeError(f"Z number must be an int. {Z} given.")
            self._Z = Z
            self._element = Element(Z)
        if node is None:
            self._tree = ValueNode(self.mcnp_str(), str, PaddingNode(" "))
        self._handle_stupid_legacy_stupidity()
        if ZAID:
            return
        if A is not None:
            if not isinstance(A, int):
                raise TypeError(f"A number must be an int. {A} given.")
            self._A = A
        else:
            self._A = 0
        if not isinstance(meta_state, (int, type(None))):
            raise TypeError(f"Meta state must be an int. {meta_state} given.")
        if meta_state:
            self._is_metastable = True
            self._meta_state = meta_state
        else:
            self._is_metastable = False
            self._meta_state = 0
        if not isinstance(library, str):
            raise TypeError(f"Library can only be str. {library} given.")
        self._library = Library(library)
        self._ZAID = str(self.get_full_zaid())

    def _handle_stupid_legacy_stupidity(self):
        # TODO work on this for mat_redesign
        if self.ZAID in self._STUPID_MAP:
            stupid_overwrite = self._STUPID_MAP[self.ZAID]
            for key, value in stupid_overwrite.items():
                setattr(self, key, value)

    @classmethod
    def _parse_zaid(cls, ZAID):
        """
        Parses the ZAID fully including metastable isomers.

        See Table 3-32 of LA-UR-17-29881

        """

        def is_probably_an_isotope(Z, A):
            for lim_Z, lim_A in cls._BOUNDING_CURVE:
                if Z <= lim_Z:
                    if A <= lim_A:
                        return True
                    else:
                        return False
                else:
                    continue
            # if you are above Lv it's probably legit.
            return True

        ret = {}
        ret["_Z"] = int(ZAID / _ZAID_A_ADDER)
        ret["_element"] = Element(ret["_Z"])
        A = int(ZAID % _ZAID_A_ADDER)
        if not is_probably_an_isotope(ret["_Z"], A):
            ret["_is_metastable"] = True
            true_A = A - 300
            # only m1,2,3,4 allowed
            found = False
            for i in range(1, 5):
                true_A -= 100
                # assumes that can only vary 40% from A = 2Z
                if is_probably_an_isotope(ret["_Z"], true_A):
                    found = True
                    break
            if found:
                ret["_meta_state"] = i
                ret["_A"] = true_A
            else:
                raise ValueError(
                    f"ZAID: {ZAID} cannot be parsed as a valid metastable isomer. "
                    "Only isomeric state 1 - 4 are allowed"
                )

        else:
            ret["_is_metastable"] = False
            ret["_meta_state"] = 0
            ret["_A"] = A
        return ret

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

    # TODO verify _update_values plays nice
    @make_prop_pointer("_library", (str, Library), Library)
    def library(self):
        """
         The MCNP library identifier e.g. 80c

        :rtype: str
        """
        pass

    def __repr__(self):
        return f"{self.__class__.__name__}({repr(self.nuclide_str())})"

    def mcnp_str(self):
        """
        Returns an MCNP formatted representation.

        E.g., 1001.80c

        :returns: a string that can be used in MCNP
        :rtype: str
        """
        return f"{self.ZAID}.{self.library}" if str(self.library) else self.ZAID

    def nuclide_str(self):
        meta_suffix = f"m{self.meta_state}" if self.is_metastable else ""
        suffix = f".{self._library}" if str(self._library) else ""
        return f"{self.element.symbol}-{self.A}{meta_suffix}{suffix}"

    def get_base_zaid(self):
        """
        Get the ZAID identifier of the base isotope this is an isomer of.

        This is mostly helpful for working with metastable isomers.

        :returns: the mcnp ZAID of the ground state of this isotope.
        :rtype: int
        """
        return self.Z * _ZAID_A_ADDER + self.A

    def get_full_zaid(self):
        """
        Get the ZAID identifier of this isomer.

        :returns: the mcnp ZAID of this isotope.
        :rtype: int
        """
        meta_adder = 300 + 100 * self.meta_state if self.is_metastable else 0
        return self.Z * _ZAID_A_ADDER + self.A + meta_adder

    @classmethod
    def get_from_fancy_name(cls, identifier):
        """
        :param identifier:
        :type idenitifer: str | int
        """
        if isinstance(identifier, cls):
            return identifier
        if isinstance(identifier, Element):
            element = identifier
        A = 0
        isomer = None
        base_meta = 0
        library = ""
        if isinstance(identifier, (int, float)):
            if identifier > _ZAID_A_ADDER:
                parts = cls._parse_zaid(int(identifier))
                element, A, isomer = (
                    parts["_element"],
                    parts["_A"],
                    parts["_meta_state"],
                )
            else:
                element, A, isomer = Element(int(identifier)), 0, 0
        elif isinstance(identifier, str):
            if match := cls._NAME_PARSER.match(identifier):
                match = match.groupdict()
                if match["ZAID"]:
                    parts = cls._parse_zaid(int(match["ZAID"]))
                    element, A, base_meta = (
                        parts["_element"],
                        parts["_A"],
                        parts["_meta_state"],
                    )

                else:
                    element_name = match["element"]
                    element = Element.get_by_symbol(element_name.capitalize())
                    if match["A"]:
                        A = int(match["A"])
                if match["meta"]:
                    isomer = int(match["meta"])
                    if base_meta:
                        isomer += base_meta
                if match["library"]:
                    library = match["library"]
        else:
            raise TypeError(
                f"Isotope fancy names only supports str, ints, and iterables. {identifier} given."
            )

        return cls(element=element, A=A, meta_state=isomer, library=library)

    def __repr__(self):
        return f"{self.__class__.__name__}({repr(self.nuclide_str())})"

    def __str__(self):
        meta_suffix = f"m{self.meta_state}" if self.is_metastable else ""
        suffix = f" ({self._library})" if str(self._library) else "()"
        return f"{self.element.symbol:>2}-{self.A:<3}{meta_suffix:<2}{suffix:>5}"

    def __hash__(self):
        return hash(self._ZAID)

    def __lt__(self, other):
        return int(self.ZAID) < int(other.ZAID)

    def __format__(self, format_str):
        return str(self).__format__(format_str)

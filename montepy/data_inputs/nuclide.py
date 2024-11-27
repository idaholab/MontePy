# Copyright 2024, Battelle Energy Alliance, LLC All Rights Reserved.
from montepy.constants import MAX_ATOMIC_SYMBOL_LENGTH
from montepy._singleton import SingletonGroup
from montepy.data_inputs.element import Element
from montepy.errors import *
from montepy.utilities import *
from montepy.input_parser.syntax_node import PaddingNode, ValueNode
from montepy.particle import LibraryType

import collections
from functools import total_ordering
import re
from typing import Union
import warnings

DEFAULT_NUCLIDE_WIDTH = 11
"""
How many characters wide a nuclide with spacing should be.
"""


@total_ordering
class Library(SingletonGroup):
    """
    A class to represent an MCNP nuclear data library, e.g., ``80c``.


    Examples
    ^^^^^^^^

    .. testcode:: python

        import montepy
        library = montepy.Library("710nc")
        assert library.library == "710nc"
        assert str(library) == "710nc"
        assert library.library_type == montepy.LibraryType.NEUTRON
        assert library.number == 710
        assert library.suffix == "c"

    .. Note::

        This class is immutable, and hashable, meaning it is suitable as a dictionary key.

    .. versionadded:: 1.0.0

    :param library: The name of the library.
    :type library: str
    :raises TypeErrror: if a string is not provided.
    :raises ValueError: if a valid library is not provided.
    """

    __slots__ = "_library", "_lib_type", "_num", "_suffix"

    _SUFFIX_MAP = {
        "c": LibraryType.NEUTRON,
        "d": LibraryType.NEUTRON,
        "m": LibraryType.NEUTRON,  # coupled neutron photon, invokes `g`
        "g": LibraryType.PHOTO_ATOMIC,
        "p": LibraryType.PHOTO_ATOMIC,
        "u": LibraryType.PHOTO_NUCLEAR,
        "y": LibraryType.NEUTRON,
        "e": LibraryType.ELECTRON,
        "h": LibraryType.PROTON,
        "o": LibraryType.DEUTERON,
        "r": LibraryType.TRITON,
        "s": LibraryType.HELION,
        "a": LibraryType.ALPHA_PARTICLE,
    }
    _LIBRARY_RE = re.compile(r"(\d{2,3})[a-z]?([a-z])", re.I)

    def __init__(self, library: str):
        self._lib_type = None
        self._suffix = ""
        self._num = None
        if not isinstance(library, str):
            raise TypeError(f"library must be a str. {library} given.")
        if library:
            match = self._LIBRARY_RE.fullmatch(library)
            if not match:
                raise ValueError(f"Not a valid library. {library} given.")
            self._num = int(match.group(1))
            extension = match.group(2).lower()
            self._suffix = extension
            try:
                lib_type = self._SUFFIX_MAP[extension]
            except KeyError:
                raise ValueError(
                    f"Not a valid library extension suffix. {library} with extension: {extension} given."
                )
            self._lib_type = lib_type
        self._library = library

    @property
    def library(self) -> str:
        """
        The full name of the library.

        :rtype: str
        """
        return self._library

    @property
    def library_type(self) -> LibraryType:
        """
        The :class:`~montepy.particle.LibraryType` of this library.

        This corresponds to the type of library this would specified
        in a material definition e.g., ``NLIB``, ``PLIB``, etc.

        .. seealso::

            * :manual63:`5.6.1`

        :returns: the type of library this library is.
        :rtype: LibraryType
        """
        return self._lib_type

    @property
    def number(self) -> int:
        """
        The base number in the library.

        For example: this would be ``80`` for the library: ``Library('80c')``.

        :returns: the base number of the library.
        :rtype: int
        """
        return self._num

    @property
    def suffix(self) -> str:
        """
        The suffix of the library, or the final character of its definition.

        For example this would be ``"c"`` for the library: ``Library('80c')``.

        :returns: the suffix of the library.
        :rtype: str
        """
        return self._suffix

    def __hash__(self):
        return hash(self._library.upper())

    def __eq__(self, other):
        if not isinstance(other, (type(self), str)):
            raise TypeError(f"Can only compare Library instances.")
        if not isinstance(other, type(self)):
            return self.library.upper() == other.upper()
        # due to SingletonGroup
        return self.library.upper() == other.library.upper()

    def __bool__(self):
        return bool(self.library)

    def __str__(self):
        return self.library

    def __repr__(self):
        return f"Library('{self.library}')"

    def __lt__(self, other):
        if not isinstance(other, (str, type(self))):
            raise TypeError(f"Can only compare Library instances.")
        if isinstance(other, str):
            other = Library(other)
        if self.suffix == other.suffix:
            return self.number < other.number
        return self.suffix < other.suffix

    def __reduce__(self):
        return (self.__class__, (self._library,))


_ZAID_A_ADDER = 1000
"""
How much to multiply Z by to form a ZAID.
"""


class Nucleus(SingletonGroup):
    """
    A class to represent a nuclide irrespective of the nuclear data being used.

    This is meant to be an immutable representation of the nuclide, no matter what nuclear data
    library is used. ``U-235`` is always ``U-235``.
    Generally users don't need to interact with this much as it is almost always wrapped
    by: :class:`montepy.data_inputs.nuclide.Nuclide`.


    .. Note::

        This class is immutable, and hashable, meaning it is suitable as a dictionary key.

    .. versionadded:: 1.0.0

    :param element: the element this Nucleus is based on.
    :type element: Element
    :param A: The A-number (atomic mass) of the nuclide. If this is elemental this should be 0.
    :type A: int
    :param meta_state: The metastable state if this nuclide is isomer.
    :type meta_state: int

    :raises TypeError: if an parameter is the wrong type.
    :raises ValueError: if non-sensical values are given.
    """

    __slots__ = "_element", "_A", "_meta_state"

    def __init__(
        self,
        element: Element,
        A: int = 0,
        meta_state: int = 0,
    ):
        if not isinstance(element, Element):
            raise TypeError(
                f"Only type Element is allowed for element argument. {element} given."
            )
        self._element = element

        if not isinstance(A, int):
            raise TypeError(f"A number must be an int. {A} given.")
        if A < 0:
            raise ValueError(f"A cannot be negative. {A} given.")
        self._A = A
        if not isinstance(meta_state, (int, type(None))):
            raise TypeError(f"Meta state must be an int. {meta_state} given.")
        if meta_state not in range(0, 5):
            raise ValueError(
                f"Meta state can only be in the range: [0,4]. {meta_state} given."
            )
        self._meta_state = meta_state

    @property
    def ZAID(self) -> int:
        """
        The ZZZAAA identifier following MCNP convention.

        If this is metastable the MCNP convention for ZAIDs for metastable isomers will be used.

        :rtype: int
        """
        meta_adder = 300 + 100 * self.meta_state if self.is_metastable else 0
        temp = self.Z * _ZAID_A_ADDER + self.A + meta_adder
        if temp in Nuclide._STUPID_ZAID_SWAP:
            return Nuclide._STUPID_ZAID_SWAP[temp]
        return temp

    @property
    def Z(self) -> int:
        """
        The Z number for this isotope.

        :returns: the atomic number.
        :rtype: int
        """
        return self._element.Z

    @make_prop_pointer("_A")
    def A(self) -> int:
        """
        The A number for this isotope.

        :returns: the isotope's mass.
        :rtype: int
        """
        pass

    @make_prop_pointer("_element")
    def element(self) -> Element:
        """
        The base element for this isotope.

        :returns: The element for this isotope.
        :rtype: Element
        """
        pass

    @property
    def is_metastable(self) -> bool:
        """
        Whether or not this is a metastable isomer.

        :returns: boolean of if this is metastable.
        :rtype: bool
        """
        return bool(self._meta_state)

    @make_prop_pointer("_meta_state")
    def meta_state(self) -> int:
        """
        If this is a metastable isomer, which state is it?

        Can return values in the range [0,4]. The exact state
        number is decided by who made the ACE file for this, and not quantum mechanics.
        Convention states that the isomers should be numbered from lowest to highest energy.
        The ground state will be 0.

        :returns: the metastable isomeric state of this "isotope" in the range [0,4].
        :rtype: int
        """
        pass

    def __hash__(self):
        return hash((self.element, self.A, self.meta_state))

    def __eq__(self, other):
        if not isinstance(other, type(self)):
            raise TypeError(
                f"Nucleus can only be compared to a Nucleus. {other} of type {type(other)} given."
            )
        # due to SingletonGroup
        return (
            self.element == other.element
            and self.A == other.A
            and self.meta_state == other.meta_state
        )

    def __reduce__(self):
        return (type(self), (self.element, self.A, self._meta_state))

    def __lt__(self, other):
        if not isinstance(other, type(self)):
            raise TypeError("")
        return (self.Z, self.A, self.meta_state) < (self.Z, self.A, self.meta_state)

    def __str__(self):
        meta_suffix = f"m{self.meta_state}" if self.is_metastable else ""
        return f"{self.element.symbol:>2}-{self.A:<3}{meta_suffix:<2}"

    def __repr__(self):
        return f"Nucleus({self.element}, {self.A}, {self.meta_state})"


class Nuclide:
    r"""
    A class to represent an MCNP nuclide with nuclear data library information.

    Nuclide accepts ``name`` as a way of specifying a nuclide.
    This is meant to be more ergonomic than ZAIDs while not going insane with possible formats.
    This accepts ZAID and Atomic_symbol-A format.
    All cases support metastables as m# and a library specification.
    Examples include:

    * ``1001.80c``
    * ``92235m1.80c``
    * ``92635.80c``
    * ``U.80c``
    * ``U-235.80c``
    * ``U-235m1.80c``

    To be specific this must match the regular expression:

    .. testcode:: python

        import re
        parser = re.compile(r\"\"\"
            (\d{4,6}) # ZAID
                |
            ([a-z]{1,2} # or atomic symbol
            -?\d*) # optional A-number
            (m\d+)? # optional metastable
            (\.\d{{2,}}[a-z]+)? # optional library
            \"\"\",
            re.IGNORE_CASE | re.VERBOSE
        )

    .. Note::

        As discussed in :manual63:`5.6.1`:

            To represent a metastable isotope, adjust the AAA value using the
            following convention: AAA’=(AAA+300)+(m × 100), where m is the
            metastable level and m=1, 2, 3, or 4.

        MontePy attempts to apply these rules to determine the isomeric state of the nuclide.
        This requires MontePy to determine if a ZAID is a realistic base isomeric state.

        This is done simply by manually specifying 6 rectangles of realistic ZAIDs.
        MontePy checks if a ZAID is inside of these rectangles.
        These rectangles are defined by their upper right corner as an isotope.
        The lower left corner is defined by the Z-number of the previous isotope and A=0.

        These isotopes are:

        * Cl-52
        * Br-101
        * Xe-150
        * Os-203
        * Cm-251
        * Og-296

    .. Warning::

        Due to legacy reasons the nuclear data for Am-242 and Am-242m1 have been swapped for the nuclear data
        provided by LANL.
        This is documented in :manual631:`1.2.2`:

            As a historical quirk, 242m1Am and 242Am are swapped in the ZAID and SZAID formats, so that the
            former is 95242 and the latter is 95642 for ZAID and 1095242 for SZAID. It is important to verify if a
            data library follows this convention. To date, all LANL-published libraries do. The name format does
            not swap these isomers. As such, Am-242m1 can load a table labeled 95242.

        Due to this MontePy follows the MCNP convention, and swaps these ZAIDs.
        If you have custom generated ACE data for Am-242,
        that does not follow this convention you have a few options:

        #. Do nothing. If you do not need to modify a material in an MCNP input file the ZAID will be written out the same as it was in the original file.

        #. Specify the Nucleus by ZAID. This will have the same effect as before. Note that MontePy will display the wrong metastable state, but will preserve the ZAID.

        #. Open an issue. If this approach doesn't work for you please open an issue so we can develop a better solution.

    .. seealso::

        * :manual62:`107`
        * :manual63:`5.6.1`
        * :manual631:`1.2.2`


    .. versionadded:: 1.0.0

        This was added as replacement for ``montepy.data_inputs.Isotope``.



    :param name: A fancy name way of specifying a nuclide.
    :type name: str
    :param ZAID: The ZAID in MCNP format, the library can be included.
    :type ZAID: str
    :param element: the element this Nucleus is based on.
    :type element: Element
    :param Z: The Z-number (atomic number) of the nuclide.
    :type Z: int
    :param A: The A-number (atomic mass) of the nuclide. If this is elemental this should be 0.
    :type A: int
    :param meta_state: The metastable state if this nuclide is isomer.
    :type meta_state: int
    :param library: the library to use for this nuclide.
    :type library: str
    :param node: The ValueNode to build this off of. Should only be used by MontePy.
    :type node: ValueNode

    :raises TypeError: if an parameter is the wrong type.
    :raises ValueError: if non-sensical values are given.
    """

    _NAME_PARSER = re.compile(
        rf"""(
                (?P<ZAID>\d{{4,6}})|
                ((?P<element>[a-z]{{1,{MAX_ATOMIC_SYMBOL_LENGTH}}})-?(?P<A>\d*))
            )
            (m(?P<meta>\d+))?
            (\.(?P<library>\d{{2,}}[a-z]+))?""",
        re.I | re.VERBOSE,
    )
    """
    Parser for fancy names.
    """

    #                   Cl-52      Br-101     Xe-150      Os-203    Cm-251     Og-296
    _BOUNDING_CURVE = [(17, 52), (35, 101), (54, 150), (76, 203), (96, 251), (118, 296)]
    """
    Points on bounding curve for determining if "valid" isotope
    """
    _STUPID_MAP = {
        "95642": {"_meta_state": 0},
        "95242": {"_meta_state": 1},
    }
    _STUPID_ZAID_SWAP = {95242: 95642, 95642: 95242}

    def __init__(
        self,
        name: Union[str, int, Element, Nucleus] = "",
        element: Element = None,
        Z: int = None,
        A: int = 0,
        meta_state: int = 0,
        library: str = "",
        node: ValueNode = None,
    ):
        self._library = Library("")
        ZAID = ""

        if not isinstance(name, (str, int, Element, Nucleus, Nuclide, type(None))):
            raise TypeError(
                f"Name must be str, int, Element, or Nucleus. {name} of type {type(name)} given."
            )
        if name:
            element, A, meta_state, library = self._parse_fancy_name(name)
        if node is not None and isinstance(node, ValueNode):
            if node.type == float:
                node = ValueNode(node.token, str, node.padding)
            self._tree = node
            ZAID = node.value
        parts = ZAID.split(".")
        if ZAID:
            za_info = self._parse_zaid(int(parts[0]))
            element = za_info["_element"]
            A = za_info["_A"]
            meta_state = za_info["_meta_state"]
        self._nucleus = Nucleus(element, A, meta_state)
        if len(parts) > 1 and library == "":
            library = parts[1]
        if not isinstance(library, str):
            raise TypeError(f"Library can only be str. {library} given.")
        self._library = Library(library)
        if not node:
            padding_num = DEFAULT_NUCLIDE_WIDTH - len(self.mcnp_str())
            if padding_num < 1:
                padding_num = 1
            self._tree = ValueNode(self.mcnp_str(), str, PaddingNode(" " * padding_num))

    @classmethod
    def _handle_stupid_legacy_stupidity(cls, ZAID):
        """
        This handles legacy issues where ZAID are swapped.

        For now this is only for Am-242 and Am-242m1.

        .. seealso::

            * :manual631:`1.2.2`
        """
        ZAID = str(ZAID)
        ret = {}
        if ZAID in cls._STUPID_MAP:
            stupid_overwrite = cls._STUPID_MAP[ZAID]
            for key, value in stupid_overwrite.items():
                ret[key] = value
        return ret

    @classmethod
    def _parse_zaid(cls, ZAID) -> dict[str, object]:
        """
        Parses the ZAID fully including metastable isomers.

        See Table 3-32 of LA-UR-17-29881

        :param ZAID: the ZAID without the library
        :type ZAID: int
        :returns: a dictionary with the parsed information,
            in a way that can be loaded into nucleus. Keys are: _element, _A, _meta_state
        :rtype: dict[str, Object]
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
        Z = int(ZAID / _ZAID_A_ADDER)
        ret["_element"] = Element(Z)
        ret["_A"] = 0
        ret["_meta_state"] = 0
        A = int(ZAID % _ZAID_A_ADDER)
        ret["_A"] = A
        if not is_probably_an_isotope(Z, A):
            true_A = A - 300
            # only m1,2,3,4 allowed
            found = False
            for i in range(1, 5):
                true_A -= 100
                # assumes that can only vary 40% from A = 2Z
                if is_probably_an_isotope(Z, true_A):
                    found = True
                    break
            if found:
                ret["_meta_state"] = i
                ret["_A"] = true_A
            else:
                raise ValueError(
                    f"ZAID: {ZAID} cannot be parsed as a valid metastable isomer. "
                    "Only isomeric state 0 - 4 are allowed"
                )

        ret.update(cls._handle_stupid_legacy_stupidity(ZAID))
        return ret

    @property
    def ZAID(self) -> int:
        """
        The ZZZAAA identifier following MCNP convention

        :rtype: int
        """
        # if this is made mutable this cannot be user provided, but must be calculated.
        return self._nucleus.ZAID

    @property
    def Z(self) -> int:
        """
        The Z number for this isotope.

        :returns: the atomic number.
        :rtype: int
        """
        return self._nucleus.Z

    @property
    def A(self) -> int:
        """
        The A number for this isotope.

        :returns: the isotope's mass.
        :rtype: int
        """
        return self._nucleus.A

    @property
    def element(self) -> Element:
        """
        The base element for this isotope.

        :returns: The element for this isotope.
        :rtype: Element
        """
        return self._nucleus.element

    @make_prop_pointer("_nucleus")
    def nucleus(self) -> Nucleus:
        """
        The base nuclide of this nuclide without the nuclear data library.

        :rtype:Nucleus
        """
        pass

    @property
    def is_metastable(self) -> bool:
        """
        Whether or not this is a metastable isomer.

        :returns: boolean of if this is metastable.
        :rtype: bool
        """
        return self._nucleus.is_metastable

    @property
    def meta_state(self) -> int:
        """
        If this is a metastable isomer, which state is it?

        Can return values in the range [0,4]. 0 corresponds to the ground state.
        The exact state number is decided by who made the ACE file for this, and not quantum mechanics.
        Convention states that the isomers should be numbered from lowest to highest energy.

        :returns: the metastable isomeric state of this "isotope" in the range [0,4]l
        :rtype: int
        """
        return self._nucleus.meta_state

    # TODO verify _update_values plays nice
    @make_prop_pointer("_library", (str, Library), Library)
    def library(self) -> Library:
        """
         The MCNP library identifier e.g. 80c

        :rtype: Library
        """
        pass

    def __repr__(self):
        return f"{self.__class__.__name__}({repr(self.nuclide_str())})"

    def mcnp_str(self) -> str:
        """
        Returns an MCNP formatted representation.

        E.g., 1001.80c

        :returns: a string that can be used in MCNP
        :rtype: str
        """
        return f"{self.ZAID}.{self.library}" if str(self.library) else str(self.ZAID)

    def nuclide_str(self) -> str:
        """
        Creates a human readable version of this nuclide excluding the data library.

        This is of the form Atomic symbol - A [metastable state]. e.g., ``U-235m1``.

        :rtypes: str
        """
        meta_suffix = f"m{self.meta_state}" if self.is_metastable else ""
        suffix = f".{self._library}" if str(self._library) else ""
        return f"{self.element.symbol}-{self.A}{meta_suffix}{suffix}"

    def get_base_zaid(self) -> int:
        """
        Get the ZAID identifier of the base isotope this is an isomer of.

        This is mostly helpful for working with metastable isomers.

        :returns: the mcnp ZAID of the ground state of this isotope.
        :rtype: int
        """
        return self.Z * _ZAID_A_ADDER + self.A

    @classmethod
    def _parse_fancy_name(cls, identifier):
        """
        Parses a fancy name that is a ZAID, a Symbol-A, or nucleus, nuclide, or element.

        :param identifier:
        :type idenitifer: Union[str, int, element, Nucleus, Nuclide]
        :returns: a tuple of element, a, isomer, library
        :rtype: tuple
        """
        if isinstance(identifier, (Nucleus, Nuclide)):
            if isinstance(identifier, Nuclide):
                lib = identifier.library
            else:
                lib = ""
            return (identifier.element, identifier.A, identifier.meta_state, lib)
        if isinstance(identifier, Element):
            element = identifier
        A = 0
        isomer = 0
        library = ""
        if isinstance(identifier, (int, float)):
            if identifier > _ZAID_A_ADDER:
                parts = Nuclide._parse_zaid(int(identifier))
                element, A, isomer = (
                    parts["_element"],
                    parts["_A"],
                    parts["_meta_state"],
                )
            else:
                element = Element(int(identifier))
        elif isinstance(identifier, str):
            if match := cls._NAME_PARSER.fullmatch(identifier):
                match = match.groupdict()
                if match["ZAID"]:
                    parts = cls._parse_zaid(int(match["ZAID"]))
                    element, A, isomer = (
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
                    extra_isomer = int(match["meta"])
                    isomer += extra_isomer
                if match["library"]:
                    library = match["library"]
            else:
                raise ValueError(f"Not a valid nuclide identifier. {identifier} given")
        else:
            raise TypeError(
                f"Isotope fancy names only supports str, ints, and iterables. {identifier} given."
            )

        return (element, A, isomer, library)

    def __repr__(self):
        return f"{self.__class__.__name__}({repr(self.nuclide_str())})"

    def __str__(self):
        meta_suffix = f"m{self.meta_state}" if self.is_metastable else ""
        suffix = f" ({self._library})" if str(self._library) else "()"
        return f"{self.element.symbol:>2}-{self.A:<3}{meta_suffix:<2}{suffix:>5}"

    def __eq__(self, other):
        if not isinstance(other, type(self)):
            raise TypeError(
                f"Cannot compare Nuclide to other values. {other} of type {type(other)}."
            )
        return self.nucleus == other.nucleus and self.library == other.library

    def __lt__(self, other):
        if not isinstance(other, type(self)):
            raise TypeError("")
        return (self.nucleus, str(self.library)) < (self.nucleus, str(self.library))

    def __format__(self, format_str):
        return str(self).__format__(format_str)

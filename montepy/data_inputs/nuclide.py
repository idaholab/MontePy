# Copyright 2024-2025, Battelle Energy Alliance, LLC All Rights Reserved.
from montepy._check_value import args_checked
from montepy.constants import MAX_ATOMIC_SYMBOL_LENGTH
from montepy._singleton import SingletonGroup
from montepy.data_inputs.element import Element
from montepy.utilities import *
from montepy.input_parser.syntax_node import PaddingNode, ValueNode
from montepy.particle import LibraryType
import montepy.types as ty

from functools import total_ordering
import re

type NucleusLike = str | int | Element | Nucleus

type MetaState = ty.Annotated[Integral, ty.cv.greater_than(0, True), ty.cv.less_than(5)]

DEFAULT_NUCLIDE_WIDTH = 11
"""How many characters wide a nuclide with spacing should be."""


@total_ordering
class Library(SingletonGroup):
    """A class to represent an MCNP nuclear data library, e.g., ``80c``.

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

    Parameters
    ----------
    library : str
        The name of the library.

    Raises
    ------
    TypeErrror
        if a string is not provided.
    ValueError
        if a valid library is not provided.
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

    @args_checked
    def __init__(self, library: str):
        self._lib_type = None
        self._suffix = ""
        self._num = None
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
        """The full name of the library.

        Returns
        -------
        str
        """
        return self._library

    @property
    def library_type(self) -> LibraryType:
        """The :class:`~montepy.particle.LibraryType` of this library.

        This corresponds to the type of library this would specified
        in a material definition e.g., ``NLIB``, ``PLIB``, etc.

        See Also
        --------

        * :manual63:`5.6.1`

        Returns
        -------
        LibraryType
            the type of library this library is.
        """
        return self._lib_type

    @property
    def number(self) -> int:
        """The base number in the library.

        For example: this would be ``80`` for the library: ``Library('80c')``.

        Returns
        -------
        int
            the base number of the library.
        """
        return self._num

    @property
    def suffix(self) -> str:
        """The suffix of the library, or the final character of its definition.

        For example this would be ``"c"`` for the library: ``Library('80c')``.

        Returns
        -------
        str
            the suffix of the library.
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
"""How much to multiply Z by to form a ZAID."""


class Nucleus(SingletonGroup):
    """A class to represent a nuclide irrespective of the nuclear data being used.

    This is meant to be an immutable representation of the nuclide, no matter what nuclear data
    library is used. ``U-235`` is always ``U-235``.
    Generally users don't need to interact with this much as it is almost always wrapped
    by: :class:`montepy.data_inputs.nuclide.Nuclide`.

    .. Note::

        This class is immutable, and hashable, meaning it is suitable as a dictionary key.

    .. versionadded:: 1.0.0

    Parameters
    ----------
    element : Element
        the element this Nucleus is based on.
    A : int
        The A-number (atomic mass) of the nuclide. If this is elemental
        this should be 0.
    meta_state : int
        The metastable state if this nuclide is isomer.

    Raises
    ------
    TypeError
        if an parameter is the wrong type.
    ValueError
        if non-sensical values are given.
    """

    __slots__ = "_element", "_A", "_meta_state"

    @args_checked
    def __init__(
        self,
        element: Element,
        A: ty.NonNegativeInt = 0,
        meta_state: MetaState = 0,
    ):
        self._element = element

        self._A = A
        if A == 0 and meta_state != 0:
            raise ValueError(
                f"A metastable elemental state is Non-sensical. A: {A}, meta_state: {meta_state} given."
            )
        self._meta_state = meta_state

    @property
    def ZAID(self) -> int:
        """The ZZZAAA identifier following MCNP convention.

        If this is metastable the MCNP convention for ZAIDs for metastable isomers will be used.

        Returns
        -------
        int
        """
        meta_adder = 300 + 100 * self.meta_state if self.is_metastable else 0
        temp = self.Z * _ZAID_A_ADDER + self.A + meta_adder
        if temp in Nuclide._STUPID_ZAID_SWAP:
            return Nuclide._STUPID_ZAID_SWAP[temp]
        return temp

    @property
    def Z(self) -> int:
        """The Z number for this isotope.

        Returns
        -------
        int
            the atomic number.
        """
        return self._element.Z

    @make_prop_pointer("_A")
    def A(self) -> int:
        """The A number for this isotope.

        Returns
        -------
        int
            the isotope's mass.
        """
        pass

    @make_prop_pointer("_element")
    def element(self) -> Element:
        """The base element for this isotope.

        Returns
        -------
        Element
            The element for this isotope.
        """
        pass

    @property
    def is_metastable(self) -> bool:
        """Whether or not this is a metastable isomer.

        Returns
        -------
        bool
            boolean of if this is metastable.
        """
        return bool(self._meta_state)

    @make_prop_pointer("_meta_state")
    def meta_state(self) -> int:
        """If this is a metastable isomer, which state is it?

        Can return values in the range [0,4]. The exact state
        number is decided by who made the ACE file for this, and not quantum mechanics.
        Convention states that the isomers should be numbered from lowest to highest energy.
        The ground state will be 0.

        Returns
        -------
        int
            the metastable isomeric state of this "isotope" in the range
            [0,4].
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
            raise TypeError(
                f"Can't compare Nuclide to other values. {other} of type {type(other)}."
            )
        return (self.Z, self.A, self.meta_state) < (other.Z, other.A, other.meta_state)

    def __str__(self):
        meta_suffix = f"m{self.meta_state}" if self.is_metastable else ""
        return f"{self.element.symbol:>2}-{self.A:<3}{meta_suffix:<2}"

    def __repr__(self):
        return f"Nucleus({self.element}, {self.A}, {self.meta_state})"


class Nuclide:
    r"""A class to represent an MCNP nuclide with nuclear data library information.

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

    .. code-block::

        import re
        parser = re.compile(\"\"\"
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
        This is documented in `section 1.2.2 of the MCNP 6.3.1 manual <https://www.osti.gov/servlets/purl/2372634>`_ :

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

    See Also
    --------

    * :manual62:`107`
    * :manual63:`5.6.1`


    .. versionadded:: 1.0.0

        This was added as replacement for ``montepy.data_inputs.Isotope``.

    Parameters
    ----------
    name : str
        A fancy name way of specifying a nuclide.
    ZAID : str
        The ZAID in MCNP format, the library can be included.
    element : Element
        the element this Nucleus is based on.
    Z : int
        The Z-number (atomic number) of the nuclide.
    A : int
        The A-number (atomic mass) of the nuclide. If this is elemental
        this should be 0.
    meta_state : int
        The metastable state if this nuclide is isomer.
    library : str
        the library to use for this nuclide.
    node : ValueNode
        The ValueNode to build this off of. Should only be used by
        MontePy.

    Raises
    ------
    TypeError
        if a parameter is the wrong type.
    ValueError
        if non-sensical values are given.
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
    """Parser for fancy names."""

    #                   Cl-52      Br-101     Xe-150      Os-203    Cm-251     Og-296
    _BOUNDING_CURVE = [(17, 52), (35, 101), (54, 150), (76, 203), (96, 251), (118, 296)]
    """Points on bounding curve for determining if "valid" isotope"""
    _STUPID_MAP = {
        "95642": {"_meta_state": 0},
        "95242": {"_meta_state": 1},
    }
    _STUPID_ZAID_SWAP = {95242: 95642, 95642: 95242}

    @args_checked
    def __init__(
        self,
        name: NucleusLike = "",
        element: Element = None,
        Z: ty.PositiveInt = None,
        A: ty.NonNegativeInt = 0,
        meta_state: MetaState = 0,
        library: str = "",
        node: ValueNode = None,
    ):
        self._library = Library("")
        ZAID = ""

        if name:
            element, A, meta_state, new_library = self._parse_fancy_name(name)
            # give library precedence always
            if library == "":
                library = new_library
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
        if Z:
            element = Element(Z)
        if element is None:
            raise ValueError(
                "no elemental information was provided via name, element, or z. "
                f"Given: name: {name}, element: {element}, Z: {Z}"
            )
        self._nucleus = Nucleus(element, A, meta_state)
        if len(parts) > 1 and library == "":
            library = parts[1]
        self._library = Library(library)
        if not node:
            padding_num = DEFAULT_NUCLIDE_WIDTH - len(self.mcnp_str())
            if padding_num < 1:
                padding_num = 1
            self._tree = ValueNode(self.mcnp_str(), str, PaddingNode(" " * padding_num))

    @classmethod
    def _handle_stupid_legacy_stupidity(cls, ZAID):
        """This handles legacy issues where ZAID are swapped.

        For now this is only for Am-242 and Am-242m1.

        See Also
        --------

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
        """Parses the ZAID fully including metastable isomers.

        See Table 3-32 of LA-UR-17-29881

        Parameters
        ----------
        ZAID : int
            the ZAID without the library

        Returns
        -------
        dict[str, Object]
            a dictionary with the parsed information, in a way that can
            be loaded into nucleus. Keys are: _element, _A, _meta_state
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
            # if you are above Og it's probably legit.
            # to reach this state requires new elements to be discovered.
            return True  # pragma: no cover

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
        """The ZZZAAA identifier following MCNP convention

        Returns
        -------
        int
        """
        # if this is made mutable this cannot be user provided, but must be calculated.
        return self._nucleus.ZAID

    @property
    def Z(self) -> int:
        """The Z number for this isotope.

        Returns
        -------
        int
            the atomic number.
        """
        return self._nucleus.Z

    @property
    def A(self) -> int:
        """The A number for this isotope.

        Returns
        -------
        int
            the isotope's mass.
        """
        return self._nucleus.A

    @property
    def element(self) -> Element:
        """The base element for this isotope.

        Returns
        -------
        Element
            The element for this isotope.
        """
        return self._nucleus.element

    @make_prop_pointer("_nucleus")
    def nucleus(self) -> Nucleus:
        """The base nuclide of this nuclide without the nuclear data library.

        Returns
        -------
        Nucleus
        """
        pass

    @property
    def is_metastable(self) -> bool:
        """Whether or not this is a metastable isomer.

        Returns
        -------
        bool
            boolean of if this is metastable.
        """
        return self._nucleus.is_metastable

    @property
    def meta_state(self) -> int:
        """If this is a metastable isomer, which state is it?

        Can return values in the range [0,4]. 0 corresponds to the ground state.
        The exact state number is decided by who made the ACE file for this, and not quantum mechanics.
        Convention states that the isomers should be numbered from lowest to highest energy.

        Returns
        -------
        int
            the metastable isomeric state of this "isotope" in the range
            [0,4]l
        """
        return self._nucleus.meta_state

    @make_prop_pointer("_library", (str, Library), Library)
    def library(self) -> Library:
        """The MCNP library identifier e.g. 80c

        Returns
        -------
        Library
        """
        pass

    def mcnp_str(self) -> str:
        """Returns an MCNP formatted representation.

        E.g., 1001.80c

        Returns
        -------
        str
            a string that can be used in MCNP
        """
        return f"{self.ZAID}.{self.library}" if str(self.library) else str(self.ZAID)

    def nuclide_str(self) -> str:
        """Creates a human readable version of this nuclide excluding the data library.

        This is of the form Atomic symbol - A [metastable state]. e.g., ``U-235m1``.

        Returns
        -------
        str
        """
        meta_suffix = f"m{self.meta_state}" if self.is_metastable else ""
        suffix = f".{self._library}" if str(self._library) else ""
        return f"{self.element.symbol}-{self.A}{meta_suffix}{suffix}"

    def get_base_zaid(self) -> int:
        """Get the ZAID identifier of the base isotope this is an isomer of.

        This is mostly helpful for working with metastable isomers.

        Returns
        -------
        int
            the mcnp ZAID of the ground state of this isotope.
        """
        return self.Z * _ZAID_A_ADDER + self.A

    @classmethod
    def _parse_fancy_name(cls, identifier):
        """Parses a fancy name that is a ZAID, a Symbol-A, or nucleus, nuclide, or element.

        Parameters
        ----------
        identifier
        idenitifer : Union[str, int, element, Nucleus, Nuclide]

        Returns
        -------
        tuple
            a tuple of element, a, isomer, library
        """
        if isinstance(identifier, (Nucleus, Nuclide)):
            if isinstance(identifier, Nuclide):
                lib = identifier.library
            else:
                lib = ""
            return (identifier.element, identifier.A, identifier.meta_state, str(lib))
        if isinstance(identifier, Element):
            element = identifier
            return (element, 0, 0, "")
        A = 0
        isomer = 0
        library = ""
        if isinstance(identifier, Real):
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
            raise TypeError(
                f"Cannot compare Nuclide to other values. {other} of type {type(other)}."
            )
        return (self.nucleus, self.library) < (other.nucleus, other.library)

    def __format__(self, format_str):
        return str(self).__format__(format_str)

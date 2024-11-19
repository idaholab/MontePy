# Copyright 2024, Battelle Energy Alliance, LLC All Rights Reserved.
from montepy.constants import MAX_ATOMIC_SYMBOL_LENGTH
from montepy._singleton import SingletonGroup
from montepy.data_inputs.element import Element
from montepy.errors import *
from montepy.utilities import *
from montepy.input_parser.syntax_node import PaddingNode, ValueNode
from montepy.particle import LibraryType

import collections
import re
import warnings


class Singleton:

    _instances = collections.defaultdict(dict)

    def __new__(cls, *args, **kwargs):
        kwargs_t = tuple([(k, v) for k, v in kwargs.items()])
        try:
            return cls._instances[cls][args + kwargs_t]
        except KeyError:
            cls._instances[cls][args + kwargs_t] = super().__new__(
                cls,
            )
            cls._instances[cls][args + kwargs_t].__init__(*args, **kwargs)
            return cls._instances[cls][args + kwargs_t]


class Library(Singleton):
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

    def __init__(self, library):
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
        else:
            self._lib_type = None
        self._library = library

    __slots__ = "_library", "_lib_type", "_num", "_suffix"

    _SUFFIX_MAP = {
        "c": LibraryType.NEUTRON,
        "d": LibraryType.NEUTRON,
        "m": LibraryType.NEUTRON,  # coupled neutron photon, invokes `g`
        # TODO do we need to handle this edge case?
        "g": LibraryType.PHOTO_ATOMIC,
        "p": LibraryType.PHOTO_ATOMIC,
        "u": LibraryType.PHOTO_NUCLEAR,
        "y": LibraryType.NEUTRON,  # TODO is this right?
        "e": LibraryType.ELECTRON,
        "h": LibraryType.PROTON,
        "o": LibraryType.DEUTERON,
        "r": LibraryType.TRITON,
        "s": LibraryType.HELION,
        "a": LibraryType.ALPHA_PARTICLE,
    }
    _LIBRARY_RE = re.compile(r"(\d{2,3})[a-z]?([a-z])", re.I)

    @property
    def library(self):
        """
        The full name of the library.

        :rtype: str
        """
        return self._library

    @property
    def library_type(self):
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
    def number(self):
        """
        The base number in the library.

        For example: this would be ``80`` for the library: ``Library('80c')``.

        :returns: the base number of the library.
        :rtype: int
        """
        return self._num

    @property
    def suffix(self):
        """
        The suffix of the library, or the final character of its definition.

        For example this would be ``"c"`` for the library: ``Library('80c')``.

        :returns: the suffix of the library.
        :rtype: str
        """
        return self._suffix

    def __hash__(self):
        return hash(self._library)

    def __eq__(self, other):
        if not isinstance(other, (type(self), str)):
            raise TypeError(f"Can only compare Library instances.")
        if not isinstance(other, type(self)):
            return self.library == other
        # due to SingletonGroup
        return self is other

    def __str__(self):
        return self.library

    def __repr__(self):
        return str(self)

    def __lt__(self, other):
        if not isinstance(other, type(self)):
            raise TypeError(f"Can only compare Library instances.")
        if self.suffix == other.suffix:
            return self.number < other.number
        return self.suffix < other.suffix


_ZAID_A_ADDER = 1000
"""
How much to multiply Z by to form a ZAID.
"""


class Nucleus(metaclass=SingletonGroup):
    """
    A class to represent a nuclide irrespective of the nuclear data being used.

    This is meant to be an immutable representation of the nuclide, no matter what nuclear data
    library is used. ``U-235`` is always ``U-235``.
    Generally users don't need to interact with this much as it is almost always wrapped
    by: :class:`montepy.data_inputs.nuclide.Nuclide`.


    .. Note::

        This class is immutable, and hashable, meaning it is suitable as a dictionary key.

    .. versionadded:: 1.0.0

    :param ZAID: hi
    """

    __slots__ = "_element", "_A", "_meta_state"

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
        ZAID="",
        element=None,
        Z=None,
        A=None,
        meta_state=None,
    ):
        if ZAID:
            # TODO simplify this. Should never get library
            parts = ZAID.split(".")
            try:
                assert len(parts) <= 2
                ZAID = int(parts[0])
            except (AssertionError, ValueError) as e:
                raise ValueError(f"ZAID: {ZAID} could not be parsed as a valid isotope")
            new_vals = self._parse_zaid(int(ZAID))
            for key, value in new_vals.items():
                setattr(self, key, value)
        elif element is not None:
            if not isinstance(element, Element):
                raise TypeError(
                    f"Only type Element is allowed for element argument. {element} given."
                )
            self._element = element

        elif Z is not None:
            if not isinstance(Z, int):
                raise TypeError(f"Z number must be an int. {Z} given.")
            self._element = Element(Z)
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
            self._meta_state = meta_state
        else:
            self._meta_state = 0

    @classmethod
    def _handle_stupid_legacy_stupidity(cls, ZAID):
        # TODO work on this for mat_redesign
        ZAID = str(ZAID)
        ret = {}
        if ZAID in cls._STUPID_MAP:
            stupid_overwrite = cls._STUPID_MAP[ZAID]
            for key, value in stupid_overwrite.items():
                ret[key] = value
        return ret

    @property
    def ZAID(self):
        """
        The ZZZAAA identifier following MCNP convention

        :rtype: int
        """
        meta_adder = 300 + 100 * self.meta_state if self.is_metastable else 0
        temp = self.Z * _ZAID_A_ADDER + self.A + meta_adder
        if temp in self._STUPID_ZAID_SWAP:
            return self._STUPID_ZAID_SWAP[temp]
        return temp

    @property
    def Z(self):
        """
        The Z number for this isotope.

        :returns: the atomic number.
        :rtype: int
        """
        return self._element.Z

    @make_prop_pointer("_A")
    def A(self):
        """
        The A number for this isotope.

        :returns: the isotope's mass.
        :rtype: int
        """
        pass

    @make_prop_pointer("_element")
    def element(self):
        """
        The base element for this isotope.

        :returns: The element for this isotope.
        :rtype: Element
        """
        pass

    @property
    def is_metastable(self):
        """
        Whether or not this is a metastable isomer.

        :returns: boolean of if this is metastable.
        :rtype: bool
        """
        return bool(self._meta_state)

    @make_prop_pointer("_meta_state")
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
        pass

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
        Z = int(ZAID / _ZAID_A_ADDER)
        ret["_element"] = Element(Z)
        A = int(ZAID % _ZAID_A_ADDER)
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
                    "Only isomeric state 1 - 4 are allowed"
                )

        else:
            ret["_meta_state"] = 0
            ret["_A"] = A
        ret.update(cls._handle_stupid_legacy_stupidity(ZAID))
        return ret

    def __hash__(self):
        return hash((self.element, self.A, self.meta_state))

    def __eq__(self, other):
        if not isinstance(other, type(self)):
            raise TypeError("")
        # due to SingletonGroup
        return self is other

    def __lt__(self, other):
        if not isinstance(other, type(self)):
            raise TypeError("")
        return (self.Z, self.A, self.meta_state) < (self.Z, self.A, self.meta_state)

    def __str__(self):
        meta_suffix = f"m{self.meta_state}" if self.is_metastable else ""
        return f"{self.element.symbol:>2}-{self.A:<3}{meta_suffix:<2}"


class Nuclide:
    """
    A class to represent an MCNP isotope

    .. versionadded:: 1.0.0

        This was added as replacement for ``montepy.data_inputs.Isotope``.

    :param ZAID: the MCNP isotope identifier
    :type ZAID: str
    :param suppress_warning: Whether to suppress the ``FutureWarning``.
    :type suppress_warning: bool
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
    """"""

    def __init__(
        self,
        name="",
        element=None,
        Z=None,
        A=None,
        meta_state=None,
        library="",
        node=None,
    ):
        self._library = Library("")
        ZAID = ""

        if not isinstance(name, (str, int, Element, Nucleus)):
            raise TypeError(f"")
        if name:
            element, A, meta_state, library = self._parse_fancy_name(name)
        if node is not None and isinstance(node, ValueNode):
            if node.type == float:
                node = ValueNode(node.token, str, node.padding)
            self._tree = node
            ZAID = node.value
        self._nucleus = Nucleus(ZAID, element, Z, A, meta_state)
        parts = ZAID.split(".")
        if len(parts) > 1 and library == "":
            library = parts[1]
        if not isinstance(library, str):
            raise TypeError(f"Library can only be str. {library} given.")
        self._library = Library(library)
        if not node:
            self._tree = ValueNode(self.mcnp_str(), str)

    @property
    def ZAID(self):
        """
        The ZZZAAA identifier following MCNP convention

        :rtype: int
        """
        # if this is made mutable this cannot be user provided, but must be calculated.
        return self._nucleus.ZAID

    @property
    def Z(self):
        """
        The Z number for this isotope.

        :returns: the atomic number.
        :rtype: int
        """
        return self._nucleus.Z

    @property
    def A(self):
        """
        The A number for this isotope.

        :returns: the isotope's mass.
        :rtype: int
        """
        return self._nucleus.A

    @property
    def element(self):
        """
        The base element for this isotope.

        :returns: The element for this isotope.
        :rtype: Element
        """
        return self._nucleus.element

    @make_prop_pointer("_nucleus")
    def nucleus(self):
        """ """

    @property
    def is_metastable(self):
        """
        Whether or not this is a metastable isomer.

        :returns: boolean of if this is metastable.
        :rtype: bool
        """
        return self._nucleus.is_metastable

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
        return self._nucleus.meta_state

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
        return f"{self.ZAID}.{self.library}" if str(self.library) else str(self.ZAID)

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

    @classmethod
    def _parse_fancy_name(cls, identifier):
        """
        :param identifier:
        :type idenitifer: str | int
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
                parts = Nucleus._parse_zaid(int(identifier))
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
                    parts = Nucleus._parse_zaid(int(match["ZAID"]))
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
            raise TypeError("")
        return self.nucleus == other.nucleus and self.library == other.library

    def __lt__(self, other):
        if not isinstance(other, type(self)):
            raise TypeError("")
        return (self.nucleus, str(self.library)) < (self.nucleus, str(self.library))

    def __format__(self, format_str):
        return str(self).__format__(format_str)

# Copyright 2024-2025, Battelle Energy Alliance, LLC All Rights Reserved.
from __future__ import annotations
import collections as co
import copy
import math
from numbers import Integral, Real
from typing import Generator, Union
import weakref

import montepy
from montepy.data_inputs import data_input, thermal_scattering
from montepy.data_inputs.nuclide import Library, Nucleus, Nuclide
from montepy.data_inputs.element import Element
from montepy.input_parser import syntax_node
from montepy.input_parser.material_parser import MaterialParser
from montepy.numbered_mcnp_object import Numbered_MCNP_Object, InitInput
from montepy.exceptions import *
from montepy.utilities import *
from montepy.particle import LibraryType


MAX_PRINT_ELEMENTS: int = 5
"""
The maximum number of elements to print in a material string descripton.
"""

DEFAULT_INDENT: int = 6
"""
The default number of spaces to indent on a new line by.

This is used for adding new material components.
By default all components made from scratch are added to their own line with this many leading spaces.
"""

NuclideLike = Union[Nuclide, Nucleus, Element, str, Integral]


class _DefaultLibraries:
    """A dictionary wrapper for handling the default libraries for a material.

    The default libraries are those specified by keyword, e.g., ``nlib=80c``.

    Parameters
    ----------
    parent_mat : Material
        the material that this default library is associated with.
    """

    __slots__ = "_libraries", "_parent"

    def __init__(self, parent_mat: Material):
        self._libraries = {}
        self._parent = weakref.ref(parent_mat)

    def __getitem__(self, key):
        key = self._validate_key(key)
        try:
            return Library(self._libraries[key]["data"].value)
        except KeyError:
            return None

    def update(self, other=None, **kwargs):
        """Update the default libraries with the key/value pairs from other, overwriting existing keys.
        
        Parameters
        ----------
        other : dict or dict-like
            Another dict or dict-like object to update from
        **kwargs
            Additional key-value pairs to update
        """
        if other is not None:
            if hasattr(other, "items"):
                for key, value in other.items():
                    self[key] = value
            else:
                for key, value in other:
                    self[key] = value
        for key, value in kwargs.items():
            self[key] = value

    def __setitem__(self, key, value):
        key = self._validate_key(key)
        if value is None:
            # Setting to None means unset/delete the library
            try:
                del self[key]
            except KeyError:
                pass  # Already unset, nothing to do
            return
        if not isinstance(value, (Library, str)):
            raise TypeError("Default library value must be a Library, str, or None")
        if isinstance(value, str):
            value = Library(value)
        try:
            node = self._libraries[key]
        except KeyError:
            node = self._generate_default_node(key, str(value))
            self._parent()._append_param_lib(node)
            self._libraries[key] = node
        node["data"].value = str(value)

    def __delitem__(self, key):
        key = self._validate_key(key)
        node = self._libraries.pop(key)
        self._parent()._delete_param_lib(node)

    def __str__(self):
        return "\n".join([f"{key} = {value}" for key, value in self.items()])

    def __iter__(self):
        return iter(self._libraries)

    def items(self):
        for lib_type, node in self._libraries.items():
            yield (lib_type, node["data"].value)

    @staticmethod
    def _validate_key(key):
        if not isinstance(key, (str, LibraryType)):
            raise TypeError("")
        if not isinstance(key, LibraryType):
            key = LibraryType(key.upper())
        return key

    @staticmethod
    def _generate_default_node(key: LibraryType, val: str):
        classifier = syntax_node.ClassifierNode()
        classifier.prefix = key.value
        ret = {
            "classifier": classifier,
            "seperator": syntax_node.PaddingNode(" = "),
            "data": syntax_node.ValueNode(val, str),
        }
        return syntax_node.SyntaxNode("mat library", ret)

    def _load_node(self, key: Union[str, LibraryType], node: syntax_node.SyntaxNode):
        key = self._validate_key(key)
        self._libraries[key] = node

    def __getstate__(self):
        return {"_libraries": self._libraries}

    def __setstate__(self, state):
        self._libraries = state["_libraries"]

    def _link_to_parent(self, parent_mat: Material):
        self._parent = weakref.ref(parent_mat)


class _MatCompWrapper:
    """A wrapper that allows unwrapping Nuclide and fractions"""

    __slots__ = "_parent", "_index", "_setter"

    def __init__(self, parent, index, setter):
        self._parent = parent
        self._index = index
        self._setter = setter

    def __iter__(self):

        def generator():
            for component in self._parent:
                yield component[self._index]

        return generator()

    def __getitem__(self, idx):
        return self._parent[idx][self._index]

    def __setitem__(self, idx, val):
        new_val = self._setter(self._parent[idx], val)
        self._parent[idx] = new_val


class Material(data_input.DataInputAbstract, Numbered_MCNP_Object):
    """A class to represent an MCNP material.

    Examples
    --------

    First it might be useful to load an example problem:

    .. testcode::

        import montepy
        problem = montepy.read_input("foo.imcnp")
        mat = problem.materials[1]
        print(mat)

    .. testoutput::

        MATERIAL: 1, ['hydrogen', 'oxygen']

    Materials are iterable
    ^^^^^^^^^^^^^^^^^^^^^^

    Materials look like a list of tuples, and is iterable.
    Whether or not the material is defined in mass fraction or atom fraction
    is stored for the whole material in :func:`~montepy.data_inputs.material.Material.is_atom_fraction`.
    The fractions (atom or mass) of the componenets are always positive,
    because MontePy believes in physics.

    .. testcode::

        assert mat.is_atom_fraction # ensures it is in atom_fraction

        for nuclide, fraction in mat:
            print("nuclide", nuclide, fraction)

    This would display:

    .. testoutput::

        nuclide  H-1     (80c) 2.0
        nuclide  O-16    (80c) 1.0

    As a list, Materials can be indexed:

    .. testcode::

        oxygen, ox_frac = mat[1]
        mat[1] = (oxygen, ox_frac + 1e-6)
        del mat[1]

    If you need just the nuclides or just the fractions of components in this material see: :func:`nuclides` and
    :func:`values`.

    You can check if a Nuclide is in a Material
    ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

    You can check if a :class:`~montepy.data_inputs.nuclide.Nuclide` or :class:`~montepy.data_input.element.Element` is
    in a Material with ``in``.

    .. doctest::

        >>> montepy.Nuclide("H-1") in mat
        True
        >>> "H-1" in mat
        True
        >>> montepy.Element(1) in mat
        True
        >>> montepy.Element(92) in mat
        False

    Add New Component
    ^^^^^^^^^^^^^^^^^

    The easiest way to add new components to a material is with
    :func:`~montepy.data_inputs.material.Material.add_nuclide`.

    .. testcode::

        # add boric acid to water
        boric_acid_frac = 1e-6
        mat[0]
        # Add by nuclide object
        mat.add_nuclide(oxygen, ox_frac + 3 * boric_acid_frac)
        # add by nuclide Name or ZAID
        mat.add_nuclide("B-10.80c", 1e-6)
        print(mat)

    .. testoutput::

        MATERIAL: 1, ['hydrogen', 'oxygen', 'boron']

    Default Libraries
    ^^^^^^^^^^^^^^^^^

    Also materials have the concept of :func:`~montepy.data_inputs.material.Material.default_libraries`.
    These are the libraries set by ``NLIB``, ``PLIB``, etc.,
    which are used when a library of the correct :class:`~montepy.particle.LibraryType` is not provided with the
    nuclide.
    :func:`~montepy.data_inputs.material.Material.default_libraries` acts like a dictionary,
    and can accept a string or a :class:`~montepy.particle.LibraryType` as keys.

    To clear a default library, assign ``None``:

    .. testcode::

        print(mat.default_libraries["plib"])
        mat.default_libraries[montepy.LibraryType.NEUTRON] = "00c"
        print(mat.default_libraries["nlib"])
        # Clear/unset the plib default
        mat.default_libraries["plib"] = None
        print(mat.default_libraries["plib"])

    .. testoutput::

        80p
        00c
        None

    See Also
    --------

    * :manual631:`5.6.1`
    * :manual63:`5.6.1`
    * :manual62:`106`


    .. versionchanged:: 1.0.0

        * Added number parameter to constructor.
        * This was the primary change for this release. For more details on what changed see :ref:`migrate 0 1`.
            * Switched to list-like data-structure
            * Added ability to search by Nuclide
            * Added Support for default libraries (e.g., ``nlib=80c``).

    Parameters
    ----------
    input : Union[Input, str]
        The Input syntax object this will wrap and parse.
    number : int
        The number to set for this object.
    """

    _parser = MaterialParser()
    _NEW_LINE_STR = "\n" + " " * DEFAULT_INDENT

    def __init__(
        self,
        input: InitInput = None,
        number: int = None,
    ):
        self._components = []
        self._thermal_scattering = None
        self._is_atom_fraction = True
        self._number = self._generate_default_node(int, -1, None)
        self._number.never_pad = True
        self._elements = set()
        self._nuclei = set()
        self._default_libs = _DefaultLibraries(self)
        super().__init__(input)
        self._load_init_num(number)
        if input:
            num = self._input_number
            self._old_number = copy.deepcopy(num)
            self._number = num
            set_atom_frac = False
            isotope_fractions = self._tree["data"]
            is_first = True
            for group in isotope_fractions:
                if len(group) == 2:
                    self._grab_isotope(*group, is_first=is_first)
                    is_first = False
                else:
                    self._grab_default(*group)
        else:
            self._create_default_tree()

    def _grab_isotope(
        self, nuclide: Nuclide, fraction: syntax_node.ValueNode, is_first: bool = False
    ):
        """Grabs and parses the nuclide and fraction from the init function, and loads it."""
        isotope = Nuclide(node=nuclide)
        fraction.is_negatable_float = True
        if is_first:
            self._is_atom_fraction = not fraction.is_negative
        else:
            # if switching fraction formatting
            if fraction.is_negative == self._is_atom_fraction:
                raise MalformedInputError(
                    input,
                    f"Material definitions for material: {self.number} cannot use atom and mass fraction at the same time",
                )
        self._elements.add(isotope.element)
        self._nuclei.add(isotope.nucleus)
        self._components.append((isotope, fraction))

    def _grab_default(self, param: syntax_node.SyntaxNode):
        """Grabs and parses default libraris from init process."""
        try:
            lib_type = LibraryType(param["classifier"].prefix.value.upper())
            self._default_libs._load_node(lib_type, param)
        # skip extra parameters
        except ValueError:
            pass

    def _create_default_tree(self):
        classifier = syntax_node.ClassifierNode()
        classifier.number = self._number
        classifier.number.never_pad = True
        classifier.prefix = syntax_node.ValueNode("M", str, never_pad=True)
        classifier.padding = syntax_node.PaddingNode(" ")
        mats = syntax_node.MaterialsNode("mat stuff")
        self._tree = syntax_node.SyntaxNode(
            "mats",
            {
                "start_pad": syntax_node.PaddingNode(),
                "classifier": classifier,
                "data": mats,
            },
        )

    def _append_param_lib(self, node: syntax_node.SyntaxNode):
        """Adds the given syntax node to this Material's data list.

        This is called from _DefaultLibraries.
        """
        self._ensure_has_ending_padding()
        self._tree["data"].append_param(node)

    def _delete_param_lib(self, node: syntax_node.SyntaxNode):
        """Deletes the given syntax node from this Material's data list.

        This is called from _DefaultLibraries.
        """
        self._tree["data"].nodes.remove((node,))

    @make_prop_val_node("_old_number")
    def old_number(self) -> int:
        """The material number that was used in the read file

        Returns
        -------
        int
        """
        pass

    @make_prop_pointer("_is_atom_fraction", bool)
    def is_atom_fraction(self) -> bool:
        """If true this constituent is in atom fraction, not weight fraction.

        .. versionchanged:: 1.0.0

            This property is now settable.

        Returns
        -------
        bool
        """
        pass

    @property
    def material_components(self):  # pragma: no cover
        """The internal dictionary containing all the components of this material.

        .. deprecated:: 0.4.1
            MaterialComponent has been deprecated as part of a redesign for the material
            interface due to a critical bug in how MontePy handles duplicate nuclides.
            See :ref:`migrate 0 1`.

        Raises
        ------
        DeprecationWarning
            This has been fully deprecated and cannot be used.
        """
        raise DeprecationWarning(
            f"""material_components is deprecated, and has been removed in MontePy 1.0.0.
See <https://www.montepy.org/migrations/migrate0_1.html> for more information """
        )

    @make_prop_pointer("_default_libs")
    def default_libraries(self):
        """The default libraries that are used when a nuclide doesn't have a relevant library specified.

        Default Libraries
        ^^^^^^^^^^^^^^^^^

        Also materials have the concept of :func:`~montepy.data_inputs.material.Material.default_libraries`.
        These are the libraries set by ``NLIB``, ``PLIB``, etc.,
        which are used when a library of the correct :class:`~montepy.particle.LibraryType` is not provided with the
        nuclide.
        :func:`~montepy.data_inputs.material.Material.default_libraries` acts like a dictionary,
        and can accept a string or a :class:`~montepy.particle.LibraryType` as keys.

        To clear a default library, assign ``None``:

        .. testcode::

            print(mat.default_libraries["plib"])
            mat.default_libraries[montepy.LibraryType.NEUTRON] = "00c"
            print(mat.default_libraries["nlib"])
            # Clear/unset the plib default
            mat.default_libraries["plib"] = None
            print(mat.default_libraries["plib"])

        .. testoutput::

            None
            00c
            None

        .. versionadded:: 1.0.0

        """
        pass

    def get_nuclide_library(
        self, nuclide: Nuclide, library_type: LibraryType
    ) -> Union[Library, None]:
        """Figures out which nuclear data library will be used for the given nuclide in this
        given material in this given problem.

        This follows the MCNP lookup process and returns the first Library to meet these rules.

        #. The library extension for the nuclide. For example if the nuclide is ``1001.80c`` for ``LibraryType("nlib")``, ``Library("80c")`` will be returned.

        #. Next if a relevant nuclide library isn't provided the :func:`~montepy.data_inputs.material.Material.default_libraries` will be used.

        #. Finally if the two other options failed ``M0`` will be checked. These are stored in :func:`montepy.materials.Materials.default_libraries`.

        Notes
        -----

        The final backup is that MCNP will use the first matching library in ``XSDIR``.
        Currently MontePy doesn't support reading an ``XSDIR`` file and so it will return none in this case.


        .. versionadded:: 1.0.0

        Parameters
        ----------
        nuclide : Union[Nuclide, str]
            the nuclide to check.
        library_type : LibraryType
            the LibraryType to check against.

        Returns
        -------
        Union[Library, None]
            the library that will be used in this scenario by MCNP.

        Raises
        ------
        TypeError
            If arguments of the wrong type are given.
        """
        if not isinstance(nuclide, (Nuclide, str)):
            raise TypeError(f"nuclide must be a Nuclide. {nuclide} given.")
        if isinstance(nuclide, str):
            nuclide = Nuclide(nuclide)
        if not isinstance(library_type, (str, LibraryType)):
            raise TypeError(
                f"Library_type must be a LibraryType. {library_type} given."
            )
        if not isinstance(library_type, LibraryType):
            library_type = LibraryType(library_type.upper())
        if nuclide.library.library_type == library_type:
            return nuclide.library
        lib = self.default_libraries[library_type]
        if lib:
            return lib
        if self._problem:
            return self._problem.materials.default_libraries[library_type]
        return None

    def __getitem__(self, idx):
        """"""
        if not isinstance(idx, (Integral, slice)):
            raise TypeError(f"Not a valid index. {idx} given.")
        if isinstance(idx, Integral):
            comp = self._components[idx]
            return self.__unwrap_comp(comp)
        # else it's a slice
        return [self.__unwrap_comp(comp) for comp in self._components[idx]]

    @staticmethod
    def __unwrap_comp(comp):
        return (comp[0], comp[1].value)

    def __iter__(self):
        def gen_wrapper():
            for comp in self._components:
                yield self.__unwrap_comp(comp)

        return gen_wrapper()

    def __setitem__(self, idx, newvalue):
        """"""
        if not isinstance(idx, (Integral, slice)):
            raise TypeError(f"Not a valid index. {idx} given.")
        old_vals = self._components[idx]
        self._check_valid_comp(newvalue)
        node_idx = self._tree["data"].nodes.index((old_vals[0]._tree, old_vals[1]), idx)
        # grab fraction
        old_vals[1].value = newvalue[1]
        self._tree["data"].nodes[node_idx] = (newvalue[0]._tree, old_vals[1])
        self._components[idx] = (newvalue[0], old_vals[1])

    def __len__(self):
        return len(self._components)

    def _check_valid_comp(self, newvalue: tuple[Nuclide, Real]):
        """Checks valid compositions and raises an error if needed."""
        if not isinstance(newvalue, tuple):
            raise TypeError(
                f"Invalid component given. Must be tuple of Nuclide, fraction. {newvalue} given."
            )
        if len(newvalue) != 2:
            raise ValueError(
                f"Invalid component given. Must be tuple of Nuclide, fraction. {newvalue} given."
            )
        if not isinstance(newvalue[0], Nuclide):
            raise TypeError(f"First element must be an Nuclide. {newvalue[0]} given.")
        if not isinstance(newvalue[1], Real):
            raise TypeError(
                f"Second element must be a fraction greater than 0. {newvalue[1]} given."
            )
        if newvalue[1] < 0.0:
            raise ValueError(
                f"Second element must be a fraction greater than 0. {newvalue[1]} given."
            )

    def __delitem__(self, idx):
        if not isinstance(idx, (Integral, slice)):
            raise TypeError(f"Not a valid index. {idx} given.")
        if isinstance(idx, Integral):
            self.__delitem(idx)
            return
        # else it's a slice
        end = idx.start if idx.start is not None else 0
        start = idx.stop if idx.stop is not None else len(self) - 1
        step = -idx.step if idx.step is not None else -1
        for i in range(start, end, step):
            self.__delitem(i)
        if end == 0:
            self.__delitem(0)

    def __delitem(self, idx):
        comp = self._components[idx]
        element = self[idx][0].element
        nucleus = self[idx][0].nucleus
        found_el = False
        found_nuc = False
        # keep indices positive for testing.
        if idx < 0:
            idx += len(self)
        # determine if other components use this element and nucleus
        for i, (nuclide, _) in enumerate(self):
            if i == idx:
                continue
            if nuclide.element == element:
                found_el = True
            if nuclide.nucleus == nucleus:
                found_nuc = True
            if found_el and found_nuc:
                break
        if not found_el:
            self._elements.remove(element)
        if not found_nuc:
            self._nuclei.remove(nucleus)
        self._tree["data"].nodes.remove((comp[0]._tree, comp[1]))
        del self._components[idx]

    def __contains__(self, nuclide):
        if not isinstance(nuclide, (Nuclide, Nucleus, Element, str, Integral)):
            raise TypeError(
                f"Can only check if a Nuclide, Nucleus, Element, or str is in a material. {nuclide} given."
            )
        if isinstance(nuclide, (str, Integral)):
            nuclide = Nuclide(nuclide)
        # switch to elemental
        if isinstance(nuclide, (Nucleus, Nuclide)) and nuclide.A == 0:
            nuclide = nuclide.element
        # switch to nucleus if no library.
        if isinstance(nuclide, Nuclide) and not nuclide.library:
            nuclide = nuclide.nucleus
        if isinstance(nuclide, (Nucleus, Nuclide)):
            if isinstance(nuclide, Nuclide):
                if nuclide.nucleus not in self._nuclei:
                    return False
                for self_nuc, _ in self:
                    if self_nuc == nuclide:
                        return True
                return False
            if isinstance(nuclide, Nucleus):
                return nuclide in self._nuclei
        if isinstance(nuclide, Element):
            element = nuclide
            return element in self._elements

    def append(self, nuclide_frac_pair: tuple[Nuclide, float]):
        """Appends the tuple to this material.

        .. versionadded:: 1.0.0

        Parameters
        ----------
        nuclide_frac_pair : tuple[Nuclide, float]
            a tuple of the nuclide and the fraction to add.
        """
        self._check_valid_comp(nuclide_frac_pair)
        self._elements.add(nuclide_frac_pair[0].element)
        self._nuclei.add(nuclide_frac_pair[0].nucleus)
        # node for fraction
        node = self._generate_default_node(
            float, str(nuclide_frac_pair[1]), self._NEW_LINE_STR
        )
        syntax_node.ValueNode(str(nuclide_frac_pair[1]), float)
        node.is_negatable_float = True
        nuclide_frac_pair = (nuclide_frac_pair[0], node)
        node.is_negative = not self._is_atom_fraction
        self._components.append(nuclide_frac_pair)
        self._ensure_has_ending_padding()
        self._tree["data"].append_nuclide(("_", nuclide_frac_pair[0]._tree, node))

    def _ensure_has_ending_padding(self):
        def get_last_val_node():
            last_vals = self._tree["data"].nodes[-1][-1]
            if isinstance(last_vals, syntax_node.ValueNode):
                return last_vals
            return last_vals["data"]

        if len(self._tree["data"]) == 0:
            return
        padding = get_last_val_node().padding

        def add_new_line_padding():
            if padding is None:
                get_last_val_node().padding = syntax_node.PaddingNode(
                    self._NEW_LINE_STR
                )
            else:
                padding.append(self._NEW_LINE_STR)

        if padding:
            padding.check_for_graveyard_comments(True)
        add_new_line_padding()

    def change_libraries(self, new_library: Union[str, Library]):
        """Change the library for all nuclides in the material.

        .. versionadded:: 1.0.0

        Parameters
        ----------
        new_library : Union[str, Library]
            the new library to set all Nuclides to use.
        """
        if not isinstance(new_library, (Library, str)):
            raise TypeError(
                f"new_library must be a Library or str. {new_library} given."
            )
        if isinstance(new_library, str):
            new_library = Library(new_library)
        for nuclide, _ in self:
            nuclide.library = new_library

    def add_nuclide(self, nuclide: NuclideLike, fraction: float):
        """Add a new component to this material of the given nuclide, and fraction.

        .. versionadded:: 1.0.0

        Parameters
        ----------
        nuclide : Nuclide, str, int
            The nuclide to add, which can be a string Identifier, or
            ZAID.
        fraction : float
            the fraction of this component being added.
        """
        if not isinstance(nuclide, (Nuclide, str, Integral)):
            raise TypeError(
                f"Nuclide must of type Nuclide, str, or int. {nuclide} of type {type(nuclide)} given."
            )
        nuclide = self._promote_nuclide(nuclide, True)
        self.append((nuclide, fraction))

    def contains_all(
        self,
        *nuclides: NuclideLike,
        threshold: float = 0.0,
        strict: bool = False,
    ) -> bool:
        """Checks if this material contains of all of the given nuclides.

        A boolean "and" is used for this comparison.
        That is this material must contain all nuclides at or above the given threshold
        in order to return true.

        Examples
        ^^^^^^^^

        .. testcode::

            import montepy
            problem = montepy.read_input("tests/inputs/test.imcnp")

            # try to find LEU materials
            for mat in problem.materials:
                if mat.contains_all("U-235", threshold=0.02):
                    # your code here
                    pass

            # try to find a uranium
            for mat in problem.materials:
                if mat.contains_all("U"):
                    pass

        Notes
        -----

        The difference between :func:`contains_all` and :func:`contains_any` is only for how they
        handle being given multiple nuclides. This does not impact how given Elements will match
        daughter Nuclides. This is handled instead by ``strict``.

        Notes
        -----

        For details on how to use the ``strict`` argument see the examples in: :func:`find`.


        .. versionadded:: 1.0.0

        Parameters
        ----------
        *nuclides : Union[Nuclide, Nucleus, Element, str, int]
            a plurality of nuclides to check for.
        threshold : float
            the minimum concentration of a nuclide to be considered. The
            material components are not first normalized.
        strict : bool
            If True this does not let an elemental nuclide match all
            child isotopes, isomers, nor will an isotope match all
            isomers, nor will a blank library match all libraries.

        Returns
        -------
        bool
            whether or not this material contains all components given
            above the threshold.

        Raises
        ------
        TypeError
            if any argument is of the wrong type.
        ValueError
            if the fraction is not positive or zero, or if nuclide
            cannot be interpreted as a Nuclide.
        """
        return self._contains_arb(
            *nuclides, bool_func=all, threshold=threshold, strict=strict
        )

    def contains_any(
        self,
        *nuclides: NuclideLike,
        threshold: float = 0.0,
        strict: bool = False,
    ) -> bool:
        """Checks if this material contains any of the given nuclide.

        A boolean "or" is used for this comparison.
        That is, this material must contain any nuclides at or above the given threshold
        in order to return true.

        Examples
        ^^^^^^^^

        .. testcode::

            import montepy
            problem = montepy.read_input("tests/inputs/test.imcnp")

            # try to find any fissile materials
            for mat in problem.materials:
                if mat.contains_any("U-235", "U-233", "Pu-239", threshold=1e-6):
                    pass

        Notes
        -----

        For details on how to use the ``strict`` argument see the examples in: :func:`find`.


        .. versionadded:: 1.0.0

        Parameters
        ----------
        *nuclides : Union[Nuclide, Nucleus, Element, str, int]
            a plurality of nuclides to check for.
        threshold : float
            the minimum concentration of a nuclide to be considered. The
            material components are not first normalized.
        strict : bool
            If True this does not let an elemental nuclide match all
            child isotopes, isomers, nor will an isotope match all
            isomers, nor will a blank library match all libraries.

        Returns
        -------
        bool
            whether or not this material contains all components given
            above the threshold.

        Raises
        ------
        TypeError
            if any argument is of the wrong type.
        ValueError
            if the fraction is not positive or zero, or if nuclide
            cannot be interpreted as a Nuclide.
        """
        return self._contains_arb(
            *nuclides, bool_func=any, threshold=threshold, strict=strict
        )

    @staticmethod
    def _promote_nuclide(nuclide, strict):
        # This is necessary for python 3.9
        if not isinstance(nuclide, (Nuclide, Nucleus, Element, str, Integral)):
            raise TypeError(
                f"Nuclide must be a type that can be converted to a Nuclide. The allowed types are: "
                f"Nuclide, Nucleus, str, int. {nuclide} given."
            )
        if isinstance(nuclide, (str, Integral)):
            nuclide = Nuclide(nuclide)
        # treat elemental as element
        if isinstance(nuclide, (Nucleus, Nuclide)) and nuclide.A == 0 and not strict:
            nuclide = nuclide.element
        if isinstance(nuclide, Nuclide) and not str(nuclide.library) and not strict:
            nuclide = nuclide.nucleus
        return nuclide

    def _contains_arb(
        self,
        *nuclides: Union[Nuclide, Nucleus, Element, str, Integral],
        bool_func: co.abc.Callable[co.abc.Iterable[bool]] = None,
        threshold: float = 0.0,
        strict: bool = False,
    ) -> bool:
        nuclide_finders = []
        if not isinstance(threshold, Real):
            raise TypeError(
                f"Threshold must be a float. {threshold} of type: {type(threshold)} given"
            )
        if threshold < 0.0:
            raise ValueError(f"Threshold must be positive or zero. {threshold} given.")
        if not isinstance(strict, bool):
            raise TypeError(
                f"Strict must be bool. {strict} of type: {type(strict)} given."
            )
        for nuclide in nuclides:
            nuclide_finders.append(self._promote_nuclide(nuclide, strict))

        # fail fast
        if bool_func == all:
            for nuclide in nuclide_finders:
                if nuclide not in self and bool_func == all:
                    return False

        nuclides_search = {}
        nuclei_search = {}
        element_search = {}
        for nuclide in nuclide_finders:
            if isinstance(nuclide, Element):
                element_search[nuclide] = 0.0
            if isinstance(nuclide, Nucleus):
                nuclei_search[nuclide] = 0.0
            if isinstance(nuclide, Nuclide):
                nuclides_search[str(nuclide).lower()] = 0.0

        for nuclide, fraction in self:
            if str(nuclide).lower() in nuclides_search:
                nuclides_search[str(nuclide).lower()] += fraction
            if nuclide.nucleus in nuclei_search:
                nuclei_search[nuclide.nucleus] += fraction
            if nuclide.element in element_search:
                element_search[nuclide.element] += fraction

        threshold_check = lambda x: x > threshold
        return bool_func(
            (
                bool_func(map(threshold_check, nuclides_search.values())),
                bool_func(map(threshold_check, nuclei_search.values())),
                bool_func(map(threshold_check, element_search.values())),
            )
        )

    def clear(self):
        """Clears all nuclide components from this material.

        .. versionadded:: 1.0.0
        """
        for _ in range(len(self)):
            del self[0]

    def normalize(self):
        """Normalizes the components fractions so that they sum to 1.0.

        .. versionadded:: 1.0.0
        """
        total_frac = sum(self.values)
        for _, val_node in self._components:
            val_node.value /= total_frac

    @property
    def values(self):
        """Get just the fractions, or values from this material.

        This acts like a list. It is iterable, and indexable.

        Examples
        ^^^^^^^^

        .. testcode::

            import montepy
            mat = montepy.Material()
            mat.number = 5
            enrichment = 0.04

            # define UO2 with enrichment of 4.0%
            mat.add_nuclide("8016.00c", 2/3)
            mat.add_nuclide("U-235.00c", 1/3 * enrichment)
            mat.add_nuclide("U-238.00c", 2/3 * (1 - enrichment))

            for val in mat.values:
                print(val)
            # iterables can be used with other functions
            max_frac = max(mat.values)
            print("max", max_frac)

        This would print:

        .. testoutput::

            0.6666666666666666
            0.013333333333333332
            0.6399999999999999
            max 0.6666666666666666

        .. testcode::

            # get value by index
            print(mat.values[0])

            # set the value, and double enrichment
            mat.values[1] *= 2.0
            print(mat.values[1])

        This would print:

        .. testoutput::

            0.6666666666666666
            0.026666666666666665

        .. versionadded:: 1.0.0

        Returns
        -------
        Generator[float]
        """

        def setter(old_val, new_val):
            if not isinstance(new_val, Real):
                raise TypeError(
                    f"Value must be set to a float. {new_val} of type {type(new_val)} given."
                )
            if new_val < 0.0:
                raise ValueError(
                    f"Value must be greater than or equal to 0. {new_val} given."
                )
            return (old_val[0], new_val)

        return _MatCompWrapper(self, 1, setter)

    @property
    def nuclides(self):
        """Get just the fractions, or values from this material.

        This acts like a list. It is iterable, and indexable.

        Examples
        ^^^^^^^^

        .. testcode::

            import montepy
            mat = montepy.Material()
            mat.number = 5
            enrichment = 0.04

            # define UO2 with enrichment of 4.0%
            mat.add_nuclide("8016.00c", 2/3)
            mat.add_nuclide("U-235.00c", 1/3 * enrichment)
            mat.add_nuclide("U-238.00c", 2/3 * (1 - enrichment))

            for nuc in mat.nuclides:
                print(repr(nuc))
            # iterables can be used with other functions
            max_zaid = max(mat.nuclides)

        this would print:

        .. testoutput::

            Nuclide('O-16.00c')
            Nuclide('U-235.00c')
            Nuclide('U-238.00c')

        .. testcode::

            # get value by index
            print(repr(mat.nuclides[0]))

            # set the value, and double enrichment
            mat.nuclides[1] = montepy.Nuclide("U-235.80c")

        .. testoutput::

                 Nuclide('O-16.00c')

        .. versionadded:: 1.0.0

        Returns
        -------
        Generator[Nuclide]
        """

        def setter(old_val, new_val):
            if not isinstance(new_val, Nuclide):
                raise TypeError(
                    f"Nuclide must be set to a Nuclide. {new_val} of type {type(new_val)} given."
                )
            return (new_val, old_val[1])

        return _MatCompWrapper(self, 0, setter)

    def __prep_element_filter(self, filter_obj):
        """Makes a filter function for an element.

        For use by find
        """
        if isinstance(filter_obj, str):
            filter_obj = Element.get_by_symbol(filter_obj).Z
        if isinstance(filter_obj, Element):
            filter_obj = filter_obj.Z
        wrapped_filter = self.__prep_filter(filter_obj, "Z")
        return wrapped_filter

    def __prep_filter(self, filter_obj, attr=None):
        """Makes a filter function wrapper"""
        if filter_obj is None:
            return lambda _: True

        if isinstance(filter_obj, slice):

            def slicer(val):
                if attr is not None:
                    val = getattr(val, attr)
                if filter_obj.start:
                    start = filter_obj.start
                    if val < filter_obj.start:
                        return False
                else:
                    start = 0
                if filter_obj.stop:
                    if val >= filter_obj.stop:
                        return False
                if filter_obj.step:
                    if (val - start) % filter_obj.step != 0:
                        return False
                return True

            return slicer
        if attr:
            return lambda val: getattr(val, attr) == filter_obj
        return lambda val: val == filter_obj

    def find(
        self,
        name: str = None,
        element: Union[Element, str, Integral, slice] = None,
        A: Union[int, slice] = None,
        meta_state: Union[int, slice] = None,
        library: Union[str, slice] = None,
        strict: bool = False,
    ) -> Generator[tuple[int, tuple[Nuclide, float]]]:
        """Finds all components that meet the given criteria.

        The criteria are additive, and a component must match all criteria.
        That is the boolean and operator is used.
        Slices can be specified at most levels allowing to search by a range of values.
        For numerical quantities slices are rather intuitive, and follow the same rules that list indices do.
        For elements slices are by Z number only.
        For the library the slicing is done using string comparisons.

        Examples
        --------

        .. testcode::

            import montepy
            mat = montepy.Material()
            mat.number = 1

            # make non-sense material
            for nuclide in ["U-235.80c", "U-238.70c", "Pu-239.00c", "O-16.00c", "C-0", "C-12.00c", "Fe-56"]:
                mat.add_nuclide(nuclide, 0.1)

            print("Get all uranium nuclides.")
            print(list(mat.find(element = "U")))

            print("Get all transuranics")
            print(list(mat.find(element = slice(92, 100))))

            print("Get all ENDF/B-VIII.0")
            print(list(mat.find(library = slice("00c", "09c"))))

        This would print:

        .. testoutput::

            Get all uranium nuclides.
            [(0, (Nuclide('U-235.80c'), 0.1)), (1, (Nuclide('U-238.70c'), 0.1))]
            Get all transuranics
            [(0, (Nuclide('U-235.80c'), 0.1)), (1, (Nuclide('U-238.70c'), 0.1)), (2, (Nuclide('Pu-239.00c'), 0.1))]
            Get all ENDF/B-VIII.0
            [(2, (Nuclide('Pu-239.00c'), 0.1)), (3, (Nuclide('O-16.00c'), 0.1)), (5, (Nuclide('C-12.00c'), 0.1))]

        Strict (Explicit) Matching
        ^^^^^^^^^^^^^^^^^^^^^^^^^^

        Generally this functions treats ambiguity implicitly, and will match as many nuclides as possible.
        This is generally useful, but not always.
        By default when only an element is given all daughter nuclides match, as seen above.
        However, MCNP does provide some "natural" or "elemental" nuclear data,
        and it would be helpful to find these sometimes.
        For instance, you may want to find all instances of elemental nuclides,
        and replace them with explicit isotopes (for instance migrating from ENDF/B-VII.1 to ENDF/B-VIII).
        In these cases the ``strict`` argument is needed.
        When ``strict`` is True an ambiguous ``A`` will only match elemental data:

        .. testcode::

            print("Strict: False", list(mat.find(element="C")))
            print("Strict: True", list(mat.find(element="C", strict=True)))

        will print:

        .. testoutput::

            Strict: False [(4, (Nuclide('C-0'), 0.1)), (5, (Nuclide('C-12.00c'), 0.1))]
            Strict: True [(4, (Nuclide('C-0'), 0.1))]

        Similarly to find nuclides with no library defined you can use strict:

        .. testcode::

            print("Strict: False", list(mat.find(library=None)))
            print("Strict: True", list(mat.find(library=None, strict=True)))

        This would print:

        .. testoutput::

            Strict: False [(0, (Nuclide('U-235.80c'), 0.1)), (1, (Nuclide('U-238.70c'), 0.1)), (2, (Nuclide('Pu-239.00c'), 0.1)), (3, (Nuclide('O-16.00c'), 0.1)), (4, (Nuclide('C-0'), 0.1)), (5, (Nuclide('C-12.00c'), 0.1)), (6, (Nuclide('Fe-56'), 0.1))]
            Strict: True [(4, (Nuclide('C-0'), 0.1)), (6, (Nuclide('Fe-56'), 0.1))]

        .. versionadded:: 1.0.0

        Parameters
        ----------
        name : str
            The name to pass to Nuclide to search by a specific Nuclide.
            If an element name is passed this will only match elemental
            nuclides.
        element : Element, str, int, slice
            the element to filter by, slices must be slices of integers.
            This will match all nuclides that are based on this element.
            e.g., "U" will match U-235 and U-238.
        A : int, slice
            the filter for the nuclide A number.
        meta_state : int, slice
            the metastable isomer filter.
        library : str, slice
            the libraries to limit the search to.
        strict : bool
            When true this will strictly match elements as only elements
            (when no A is given), and only match blank libraries when no
            library is given.

        Returns
        -------
        Generator[tuple[int, tuple[Nuclide, float]]]
            a generator of all matching nuclides, as their index and
            then a tuple of their nuclide, and fraction pairs that
            match.
        """
        # nuclide type enforcement handled by `Nuclide`
        if not isinstance(element, (Element, str, Integral, slice, type(None))):
            raise TypeError(
                f"Element must be only Element, str, int or slice types. {element} of type{type(element)} given."
            )
        if not isinstance(A, (Integral, slice, type(None))):
            raise TypeError(
                f"A must be an int or a slice. {A} of type {type(A)} given."
            )
        if not isinstance(meta_state, (Integral, slice, type(None))):
            raise TypeError(
                f"meta_state must an int or a slice. {meta_state} of type {type(meta_state)} given."
            )
        if not isinstance(library, (str, slice, type(None))):
            raise TypeError(
                f"library must a str or a slice. {library} of type {type(library)} given."
            )
        if not isinstance(strict, bool):
            raise TypeError(
                f"strict must be a bool. {strict} of type {type(strict)} given."
            )
        if name:
            fancy_nuclide = Nuclide(name)
            if fancy_nuclide.A == 0 and not strict:
                element = fancy_nuclide.element
                fancy_nuclide = None
        else:
            fancy_nuclide = None
        if fancy_nuclide and not fancy_nuclide.library:
            first_filter = self.__prep_filter(fancy_nuclide.nucleus, "nucleus")
        else:
            first_filter = self.__prep_filter(fancy_nuclide)

        # create filter for defaults if strict
        if strict:
            # if strict and element switch to A=0
            if element and A is None:
                A = 0
            if library is None:
                library = ""
        filters = [
            first_filter,
            self.__prep_element_filter(element),
            self.__prep_filter(A, "A"),
            self.__prep_filter(meta_state, "meta_state"),
            self.__prep_filter(library, "library"),
        ]
        for idx, component in enumerate(self):
            for filt in filters:
                found = filt(component[0])
                if not found:
                    break
            if found:
                yield idx, component

    def find_vals(
        self,
        name: str = None,
        element: Union[Element, str, int, slice] = None,
        A: Union[int, slice] = None,
        meta_state: Union[int, slice] = None,
        library: Union[str, slice] = None,
        strict: bool = False,
    ) -> Generator[float]:
        """A wrapper for :func:`find` that only returns the fractions of the components.

        For more examples see that function.

        Examples
        ^^^^^^^^

        .. testcode::

            import montepy
            mat = montepy.Material()
            mat.number = 1

            # make non-sense material
            for nuclide in ["U-235.80c", "U-238.70c", "Pu-239.00c", "O-16.00c"]:
                mat.add_nuclide(nuclide, 0.1)

            # get fraction that is uranium
            print(sum(mat.find_vals(element= "U")))

        which would intuitively print:

        .. testoutput::

            0.2

        .. versionadded:: 1.0.0

        Parameters
        ----------
        name : str
            The name to pass to Nuclide to search by a specific Nuclide.
            If an element name is passed this will only match elemental
            nuclides.
        element : Element, str, int, slice
            the element to filter by, slices must be slices of integers.
            This will match all nuclides that are based on this element.
            e.g., "U" will match U-235 and U-238.
        A : int, slice
            the filter for the nuclide A number.
        meta_state : int, slice
            the metastable isomer filter.
        library : str, slice
            the libraries to limit the search to.
        strict : bool
            whether to strictly match elements as only elements (when no
            A is given), and only match blank libraries when no library
            is given.

        Returns
        -------
        Generator[float]
            a generator of fractions whose nuclide matches the criteria.
        """
        for _, (_, fraction) in self.find(
            name, element, A, meta_state, library, strict
        ):
            yield fraction

    def __bool__(self):
        return bool(self._components)

    @make_prop_pointer("_thermal_scattering", thermal_scattering.ThermalScatteringLaw)
    def thermal_scattering(self) -> thermal_scattering.ThermalScatteringLaw:
        """The thermal scattering law for this material

        Returns
        -------
        ThermalScatteringLaw
        """
        return self._thermal_scattering

    @property
    def cells(self) -> Generator[montepy.cell.Cell]:
        """A generator of the cells that use this material.

        Returns
        -------
        Generator[Cell]
            an iterator of the Cell objects which use this.
        """
        if self._problem:
            for cell in self._problem.cells:
                if cell.material == self:
                    yield cell

    def format_for_mcnp_input(self, mcnp_version):
        lines = super().format_for_mcnp_input(mcnp_version)
        if self.thermal_scattering is not None:
            lines += self.thermal_scattering.format_for_mcnp_input(mcnp_version)
        return lines

    def _update_values(self):
        for nuclide, fraction in self._components:
            node = nuclide._tree
            parts = node.value.split(".")
            fraction.is_negative = not self.is_atom_fraction
            if (
                len(parts) > 1
                and parts[-1] != str(nuclide.library)
                or (len(parts) == 1 and str(nuclide.library))
            ):
                node.value = nuclide.mcnp_str()

    def add_thermal_scattering(self, law):
        """Adds thermal scattering law to the material

        Parameters
        ----------
        law : str
            the law that is mcnp formatted
        """
        if not isinstance(law, str):
            raise TypeError(
                f"Thermal Scattering law for material {self.number} must be a string"
            )
        self._thermal_scattering = thermal_scattering.ThermalScatteringLaw(
            material=self
        )
        self._thermal_scattering.add_scattering_law(law)

    def update_pointers(self, data_inputs: list[montepy.data_inputs.DataInput]):
        """Updates pointer to the thermal scattering data

        Parameters
        ----------
        data_inputs : list[DataInput]
            a list of the data inputs in the problem
        """
        pass

    @staticmethod
    def _class_prefix():
        return "m"

    @staticmethod
    def _has_number():
        return True

    @staticmethod
    def _has_classifier():
        return 0

    def __repr__(self):
        ret = f"MATERIAL: {self.number} fractions: "
        if self.is_atom_fraction:
            ret += "atom\n"
        else:
            ret += "mass\n"

        for component in self:
            ret += f"{component[0]} {component[1]}\n"
        if self.thermal_scattering:
            ret += f"Thermal Scattering: {self.thermal_scattering}"

        return ret

    def __str__(self):
        elements = self.get_material_elements()
        print_el = []
        if len(elements) > MAX_PRINT_ELEMENTS:
            print_elements = elements[0:MAX_PRINT_ELEMENTS]
            print_elements.append("...")
            print_elements.append(elements[-1])
        else:
            print_elements = elements
        print_elements = [
            element.name if isinstance(element, Element) else element
            for element in print_elements
        ]
        return f"MATERIAL: {self.number}, {print_elements}"

    def get_material_elements(self):
        """Get the elements that are contained in this material.

        This is sorted by the most common element to the least common.

        Returns
        -------
        list[Element]
            a sorted list of elements by total fraction
        """
        element_frac = co.Counter()
        for nuclide, fraction in self:
            element_frac[nuclide.element] += fraction
        element_sort = sorted(element_frac.items(), key=lambda p: p[1], reverse=True)
        elements = [p[0] for p in element_sort]
        return elements

    def validate(self):
        if len(self._components) == 0 and self.number != 0:
            raise IllegalState(
                f"Material: {self.number} does not have any components defined."
            )

    def __eq__(self, other):
        if not isinstance(other, Material):
            return False
        if self.number != other.number:
            return False
        if len(self) != len(other):
            return False
        my_comp = sorted(self, key=lambda c: c[0])
        other_comp = sorted(other, key=lambda c: c[0])
        for mine, yours in zip(my_comp, other_comp):
            if mine[0] != yours[0]:
                return False
            if not math.isclose(mine[1], yours[1]):
                return False
        return True

    def __setstate__(self, state):
        super().__setstate__(state)
        self._default_libs._link_to_parent(self)

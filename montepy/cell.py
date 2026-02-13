# Copyright 2024-2025, Battelle Energy Alliance, LLC All Rights Reserved.
from __future__ import annotations

import copy
import itertools
import sly
import warnings

import montepy
from montepy.cells import Cells
from montepy.data_inputs import importance, fill, lattice_input, universe_input, volume
from montepy.data_inputs.data_parser import PREFIX_MATCHES
from montepy.data_inputs.material import Material
from montepy.geometry_operators import Operator
from montepy.input_parser import syntax_node
from montepy.input_parser.cell_parser import CellParser
from montepy.numbered_mcnp_object import Numbered_MCNP_Object, InitInput
from montepy.surface_collection import Surfaces
from montepy.surfaces.half_space import HalfSpace, UnitHalfSpace
from montepy.surfaces.surface import Surface
from montepy.universe import Universe
from montepy.exceptions import *
from montepy.utilities import *
import montepy.types as ty


def _link_geometry_to_cell(self, geom):
    geom._cell = self
    geom._add_new_children_to_cell(geom)


def _lattice_deprecation_warning():
    warnings.warn(
        message="Cell.lattice is deprecated in favor of Cell.lattice_type",
        category=DeprecationWarning,
    )


class Cell(Numbered_MCNP_Object):
    """Object to represent a single MCNP cell defined in CSG.

    Examples
    ^^^^^^^^

    First the cell needs to be initialized.

    .. testcode:: python

        import montepy
        cell = montepy.Cell()

    Then a number can be set.
    By default the cell is voided:

    .. doctest:: python

        >>> cell.number = 5
        >>> print(cell.material)
        None
        >>> mat = montepy.Material()
        >>> mat.number = 20
        >>> mat.add_nuclide("1001.80c", 1.0)
        >>> cell.material = mat
        >>> # mass and atom density are different
        >>> cell.mass_density = 0.1

    Cells can be inverted with ``~`` to make a geometry definition that is a compliment of
    that cell.

    .. testcode:: python

        complement = ~cell

    See Also
    --------

    * :manual631sec:`5.2`
    * :manual63sec:`5.2`
    * :manual62:`55`


    .. versionchanged:: 1.0.0

        Added number parameter

    Parameters
    ----------
    input : Input | str
        The Input syntax object this will wrap and parse.
    number : int
        The number to set for this object.
    """

    _ALLOWED_KEYWORDS = {
        "IMP",
        "VOL",
        "PWT",
        "EXT",
        "FCL",
        "WWN",
        "DXC",
        "NONU",
        "PD",
        "TMP",
        "U",
        "TRCL",
        "LAT",
        "FILL",
        "ELPT",
        "COSY",
        "BFLCL",
        "UNC",
    }
    _INPUTS_TO_PROPERTY = {
        importance.Importance: ("_importance", False),
        volume.Volume: ("_volume", True),
        universe_input.UniverseInput: ("_universe", True),
        lattice_input.LatticeInput: ("_lattice", True),
        fill.Fill: ("_fill", True),
    }

    _parser = CellParser()

    @args_checked
    def __init__(
        self,
        input: montepy.mcnp_object.InitInput = None,
        number: ty.PositiveInt = None,
    ):
        self._BLOCK_TYPE = montepy.input_parser.block_type.BlockType.CELL
        self._CHILD_OBJ_MAP = {
            "material": Material,
            "surfaces": Surface,
            "complements": Cell,
            "_fill_transform": montepy.data_inputs.transform.Transform,
        }
        self._material = None
        self._old_number = self._generate_default_node(int, -1)
        self._load_blank_modifiers()
        self._old_mat_number = self._generate_default_node(int, -1)
        self._density_node = self._generate_default_node(float, None)
        self._surfaces = Surfaces()
        self._complements = Cells()
        try:
            super().__init__(input, self._parser, number)
        # Add more information to issue that parser can't access
        except UnsupportedFeature as e:
            base_mesage = e.message
            token = sly.lex.Token()
            token.value = ""
            lineno = 0
            index = 0
            for lineno, line in enumerate(input.input_lines):
                if "like" in line.lower():
                    index = line.lower().index("like")
                    # get real capitalization
                    token.value = line[index : index + 5]
                    break
            err = {"message": "", "token": token, "line": lineno + 1, "index": index}

            raise UnsupportedFeature(base_mesage, input, [err]) from e

        if not input:
            self._generate_default_tree(number)
        self._old_number = copy.deepcopy(self._tree["cell_num"])
        self._number = self._tree["cell_num"]
        mat_tree = self._tree["material"]
        self._old_mat_number = mat_tree["mat_number"]
        self._density_node = mat_tree["density"]
        self._density_node.is_negatable_float = True
        if self.old_mat_number != 0:
            self._is_atom_dens = not self._density_node.is_negative
        else:
            self._is_atom_dens = None
        self._parse_geometry()
        self._parse_keyword_modifiers()

    def _parse_geometry(self):
        """Parses the cell's geometry definition, and stores it"""
        geometry = self._tree["geometry"]
        if geometry is not None:
            self._geometry = HalfSpace.parse_input_node(geometry)
        else:
            self._geometry = None

    def _parse_keyword_modifiers(self):
        """Parses the parameters to make the object and load as an attribute"""
        found_class_prefixes = set()
        for key, value in self.parameters.nodes.items():
            for input_class in PREFIX_MATCHES:
                prefix = input_class._class_prefix()
                if input_class in Cell._INPUTS_TO_PROPERTY and prefix in key.lower():
                    attr, ban_repeat = Cell._INPUTS_TO_PROPERTY[input_class]
                    key = str(value["classifier"]).lower()
                    found_class_prefixes.add(value["classifier"].prefix.value.lower())
                    input = input_class(in_cell_block=True, key=key, value=value)
                    if not getattr(self, attr).set_in_cell_block:
                        setattr(self, attr, input)
                    else:
                        if not ban_repeat:
                            getattr(self, attr).merge(
                                input_class(in_cell_block=True, key=key, value=value)
                            )
        # Add defaults to tree
        for input_class, (attr, _) in self._INPUTS_TO_PROPERTY.items():
            has_imp = False
            class_pref = input_class._class_prefix()
            if class_pref in found_class_prefixes:
                continue
            if class_pref == "imp":
                for key in self._tree["parameters"].nodes.keys():
                    if class_pref in key:
                        has_imp = True
                        break
            if (class_pref == "imp" and not has_imp) or class_pref != "imp":
                tree = getattr(self, attr)._tree
                self._tree["parameters"].append(tree, True)

    def _load_blank_modifiers(self):
        """Goes through and populates all the modifier attributes"""
        for input_class, (attr, _) in self._INPUTS_TO_PROPERTY.items():
            setattr(self, attr, input_class(in_cell_block=True))

    @property
    def importance(self):
        """The importances for this cell for various particle types.

        Each particle's importance is a property of Importance.
        e.g., ``cell.importance.photon = 1.0``.

        Deleting an importance resets it to the default value (1.0).
        e.g., ``del cell.importance.neutron``.

        .. versionchanged:: 1.2.0

            Default importance value changed from 0.0 to 1.0 to match MCNP defaults.

        Returns
        -------
        Importance
            the importance for the Cell.
        """
        return self._importance

    @property
    def universe(self):
        """The Universe that this cell is in.

        Returns
        -------
        Universe
            the Universe the cell is in.
        """
        return self._universe.universe

    @universe.setter
    @args_checked
    def universe(self, value: montepy.Universe):
        self._universe.universe = value

    @property
    def fill(self):
        """the Fill object representing how this cell is filled.

        This not only describes the universe that is filling this,
        but more complex things like transformations, and matrix fills.

        Returns
        -------
        Fill
            The Fill object of how this cell is to be filled.
        """
        return self._fill

    @property
    def _fill_transform(self):
        """A simple wrapper to get the transform of the fill or None."""
        if self.fill:
            return self.fill.transform
        return None  # pragma: no cover

    @property
    def not_truncated(self):
        """Indicates if this cell has been marked as not being truncated for optimization.

        See Note 1 from section 3.3.1.5.1 of the user manual (LA-UR-17-29981).

        Note this can be set to True iff that this cell is not in Universe 0.

            Note 1. A problem will run faster by preceding the U card entry with a minus sign for any
            cell that is not truncated by the boundary of any higher-level cell. (The minus sign indicates
            that calculating distances to boundary in higher-level cells can be omitted.) Use this
            capability with EXTREME CAUTION; MCNP6 cannot detect errors in this feature because
            the logic that enables detection is omitted by the presence of the negative universe. Extremely
            wrong answers can be quietly calculated. Plot several views of the geometry or run with the
            VOID card to check for errors.

            -- LA-UR-17-29981.

        Returns
        -------
        bool
            True if this cell has been marked as not being truncated by
            the parent filled cell.
        """
        if self.universe.number == 0:
            return False
        return self._universe.not_truncated

    @property
    def not_truncated(self):
        if self.universe.number == 0:
            return False
        return self._universe.not_truncated

    @not_truncated.setter
    @args_checked
    def not_truncated(self, value: bool):
        if self.universe.number == 0 and value:
            raise ValueError("can't specify if cell is truncated for universe 0")
        self._universe._not_truncated = value

    @property
    def old_universe_number(self):
        """The original universe number read in from the input file.

        Returns
        -------
        int
            the number of the Universe for the cell in the input file.
        """
        return self._universe.old_number

    @property
    def lattice_type(self):
        """The type of lattice being used by the cell.

        Returns
        -------
        LatticeType
            the type of lattice being used
        """
        return self._lattice.lattice

    @lattice_type.setter
    def lattice_type(self, value: montepy.LatticeType = None):
        self._lattice.lattice = value

    @lattice_type.deleter
    def lattice_type(self):
        self._lattice.lattice = None

    @property
    def lattice(self):
        """
        .. deprecated:: 1.0.0

            Use :func:`lattice_type` instead.
        """
        _lattice_deprecation_warning()
        return self.lattice_type

    @lattice.setter
    @args_checked
    def lattice(self, value: montepy.LatticeType):
        _lattice_deprecation_warning()
        self.lattice_type = value

    @lattice.deleter
    def lattice(self):
        _lattice_deprecation_warning()
        self.lattice_type = None

    @property
    def volume(self):
        """The volume for the cell.

        Will only return a number if the volume has been manually set.

        Returns
        -------
        float, None
            the volume that has been manually set or None.
        """
        return self._volume.volume

    @volume.setter
    def volume(self, value: ty.PositiveReal):
        self._volume.volume = value

    @volume.deleter
    def volume(self):
        del self._volume.volume

    @property
    def volume_mcnp_calc(self):
        """Indicates whether or not MCNP will attempt to calculate the cell volume.

        This can be disabled by either manually setting the volume or disabling
        this calculation globally.
        This does not guarantee that MCNP will able to calculate the volume.
        Complex geometries may make this impossible.

        See :func:`~montepy.cells.Cells.allow_mcnp_volume_calc`

        Returns
        -------
        bool
            True iff MCNP will try to calculate the volume for this
            cell.
        """
        return self._volume.is_mcnp_calculated

    @property
    def volume_is_set(self):
        """Whether or not the volume for this cell has been set.

        Returns
        -------
        bool
            true if the volume is manually set.
        """
        return self._volume.set

    @make_prop_val_node("_old_number")
    def old_number(self):
        """The original cell number provided in the input file

        Returns
        -------
        int
        """
        pass

    @make_prop_pointer("_material", (Material, type(None)), deletable=True)
    def material(self):
        """The Material object for the cell.

        If the material is None this is considered to be voided.

        Returns
        -------
        Material
        """
        pass

    @make_prop_pointer("_geometry", HalfSpace, validator=_link_geometry_to_cell)
    def geometry(self):
        """The Geometry for this problem.

        The HalfSpace tree that is able to represent this cell's geometry.
        MontePy's geometry is based upon dividers, which includes both Surfaces, and cells.
        A half-space is created by choosing one side of the divider.
        A divider will always create two half-spaces; only one of which can be finite.

        For instance a plane creates two infinite half-spaces, one above and one below.
        A finite cell also creates two half-spaces; inside, and outside.

        These halfspaces can then be combined with set-logic to make a new half-space.

        To generate a halfspace from a surface you must specify the positive or negative side:

        .. code-block:: python

            half_space = +plane

        To complement a cell you must invert it:

        .. code-block:: python

           half_space = ~cell

        To create more complex geometry you can use binary and ``&`` as an intersection, and binary or ``|`` as a
        union:

        .. code-block:: python

            half_space = -cylinder & + bottom & - top

        For better documentation please refer to `OpenMC
        <https://docs.openmc.org/en/stable/usersguide/geometry.html>`_.

        Returns
        -------
        HalfSpace
            this cell's geometry
        """
        pass

    @make_prop_val_node(
        "_density_node", (float, int, type(None)), base_type=float, deletable=True
    )
    def _density(self):
        """This is a wrapper to allow using the prop_val_node with mass_density and atom_density."""
        pass

    @property
    def atom_density(self) -> float:
        """The atom density of the material in the cell, in a/b-cm.

        Returns
        -------
        float, None
            the atom density. If no density is set or it is in mass
            density will return None.
        """
        if self._density and not self._is_atom_dens:
            raise AttributeError(f"Cell {self.number} is in mass density.")
        return self._density

    @atom_density.setter
    @args_checked
    def atom_density(self, density: ty.PositiveReal):
        self._is_atom_dens = True
        self._density = float(density)

    @atom_density.deleter
    def atom_density(self):
        self._density = None

    @property
    def mass_density(self) -> float:
        """The mass density of the material in the cell, in g/cc.

        Returns
        -------
        float, None
            the mass density. If no density is set or it is in atom
            density will return None.
        """
        if self._density and self._is_atom_dens:
            raise AttributeError(f"Cell {self.number} is in atom density.")
        return self._density

    @mass_density.setter
    @args_checked
    def mass_density(self, density: ty.PositiveReal):
        self._is_atom_dens = False
        self._density = float(density)

    @mass_density.deleter
    def mass_density(self):
        self._density = None

    @property
    def is_atom_dens(self):
        """Whether or not the density is in atom density [a/b-cm].

        True means it is in atom density, False means mass density [g/cc].

        Returns
        -------
        bool
        """
        return self._is_atom_dens

    @make_prop_val_node("_old_mat_number")
    def old_mat_number(self):
        """The material number provided in the original input file

        Returns
        -------
        int
        """
        pass

    @make_prop_pointer("_surfaces")
    def surfaces(self):
        """List of the Surface objects associated with this cell.

        This list does not convey any of the CGS Boolean logic

        Returns
        -------
        Surfaces
        """
        return self._surfaces

    @property
    def parameters(self):
        """A dictionary of the additional parameters for the object.

        e.g.: ``1 0 -1 u=1 imp:n=0.5`` has the parameters
        ``{"U": "1", "IMP:N": "0.5"}``

        Returns
        -------
        unknown
            a dictionary of the key-value pairs of the parameters.


        :rytpe: dict
        """
        return self._parameters

    @parameters.setter
    @args_checked
    def parameters(self, params: dict):
        self._parameters = params

    @property
    def complements(self):
        """The Cell objects that this cell is a complement of

        :rytpe: :class:`montepy.cells.Cells`
        """
        return self._complements

    @property
    def cells_complementing_this(self):
        """The cells which are a complement of this cell.

        This returns a generator.

        Returns
        -------
        generator
        """
        if self._problem:
            for cell in self._problem.cells:
                if cell != self:
                    if self in cell.complements:
                        yield cell

    def update_pointers(
        self,
        cells: montepy.cells.Cells,
        materials: montepy.materials.Materials,
        surfaces: montepy.surface_collection.Surfaces,
    ):
        """Attaches this object to the appropriate objects for surfaces and materials.

        Parameters
        ----------
        cells : Cells
            a Cells collection of the cells in the problem.
        materials : Materials
            a materials collection of the materials in the problem
        surfaces : Surfaces
            a surfaces collection of the surfaces in the problem
        """
        self._surfaces = Surfaces()
        self._complements = Cells()
        if self.old_mat_number is not None:
            if self.old_mat_number > 0:
                try:
                    self._material = materials[self.old_mat_number]
                except KeyError:
                    raise BrokenObjectLinkError(
                        "Cell", self.number, "Material", self.old_mat_number
                    )
            else:
                self._material = None
        if self.geometry:
            self._geometry.update_pointers(cells, surfaces, self)

    @args_checked
    def remove_duplicate_surfaces(self, deleting_dict: dict):
        """Updates old surface numbers to prepare for deleting surfaces.

        .. versionchanged:: 1.0.0

            The form of the deleting_dict was changed as :class:`~montepy.surfaces.Surface` is no longer hashable.

        Parameters
        ----------
        deleting_dict : dict[int, tuple[Surface, Surface]]
            a dict of the surfaces to delete, mapping the old surface to
            the new surface to replace it. The keys are the number of
            the old surface. The values are a tuple of the old surface,
            and then the new surface.
        """
        new_deleting_dict = {}

        def get_num(obj):
            if isinstance(obj, ty.Integral):
                return obj
            return obj.number

        for num, (dead_surface, new_surface) in deleting_dict.items():
            if dead_surface in self.surfaces:
                new_deleting_dict[get_num(dead_surface)] = (dead_surface, new_surface)
        if len(new_deleting_dict) > 0:
            self.geometry.remove_duplicate_surfaces(new_deleting_dict)
            for dead_surface, _ in new_deleting_dict.values():
                self.surfaces.remove(dead_surface)

    def _update_values(self):
        if self.material is not None:
            mat_num = self.material.number
            self._tree["material"]["density"].is_negative = not self.is_atom_dens
        else:
            mat_num = 0
        self._tree["material"]["mat_number"].value = mat_num
        self._geometry._update_values()
        self._tree.nodes["geometry"] = self.geometry.node
        for input_class, (attr, _) in self._INPUTS_TO_PROPERTY.items():
            getattr(self, attr)._update_values()

    def _generate_default_tree(self, number: ty.Integral = None):
        material = syntax_node.SyntaxNode(
            "material",
            {
                "mat_number": self._generate_default_node(int, 0),
                "density": self._generate_default_node(float, None),
            },
        )
        geom_node = self._generate_default_node(int, -1)
        self._tree = syntax_node.SyntaxNode(
            "cell",
            {
                "cell_num": self._generate_default_node(int, number),
                "material": material,
                "geometry": None,
                "parameters": syntax_node.ParametersNode(),
            },
        )

    def validate(self):
        """Validates that the cell is in a usable state."""
        if self._density and self.material is None:
            raise IllegalState(f"Cell {self.number} has a density set but no material")
        if self.material is not None and not self._density:
            raise IllegalState(
                f"Cell {self.number} has a non-void material but no density"
            )
        if self.geometry is None or len(self.geometry) == 0:
            raise IllegalState(f"Cell {self.number} has no geometry defined.")

    @args_checked
    def link_to_problem(self, problem: montepy.MCNP_Problem = None):
        super().link_to_problem(problem)
        self.complements.link_to_problem(problem)
        self.surfaces.link_to_problem(problem)
        for attr, _ in Cell._INPUTS_TO_PROPERTY.values():
            input = getattr(self, attr, None)
            if input:
                input.link_to_problem(problem)

    def __str__(self):
        if self.material:
            mat_num = self.material.number
        else:
            mat_num = 0
        if self._density:
            if self.is_atom_dens:
                units = "atom/b-cm"
            else:
                units = "g/cm3"
            dens_str = f"DENS: {self._density} {units}"
        else:
            dens_str = "DENS: None"
        ret = f"CELL: {self.number}, mat: {mat_num}, {dens_str}"
        if self.universe and self.universe.number != 0:
            ret += f", universe: {self.universe.number}"
        if self.fill.universe:
            ret += f", filled by: {self.fill.universe}"

        return ret

    def __repr__(self):
        ret = f"CELL: {self.number} \n"
        if self.material:
            ret += str(self.material) + "\n"
        else:
            ret += "Void material \n"
        if self._density:
            ret += f"density: {self._density} "
            if self._is_atom_dens:
                ret += "atom/b-cm\n"
            else:
                ret += "g/cc\n"
        ret += "\n".join([str(s) for s in self.surfaces])
        return ret

    def __lt__(self, other):
        return self.number < other.number

    def __invert__(self):
        if not self.number:
            raise IllegalState(
                f"Cell number must be set for a cell to be used in a geometry definition."
            )
        base_node = UnitHalfSpace(self, True, True)
        return HalfSpace(base_node, Operator.COMPLEMENT)

    def format_for_mcnp_input(
        self, mcnp_version: tuple[ty.Integral, ty.Integral, ty.Integral]
    ) -> list[str]:
        """Creates a string representation of this MCNP_Object that can be
        written to file.

        Parameters
        ----------
        mcnp_version : tuple
            The tuple for the MCNP version that must be exported to.

        Returns
        -------
        list
            a list of strings for the lines that this input will occupy.
        """
        self.validate()
        self._update_values()
        self._tree.check_for_graveyard_comments()
        modifier_keywords = {
            cls._class_prefix(): cls for cls in self._INPUTS_TO_PROPERTY.keys()
        }

        def cleanup_last_line(ret):
            last_line = ret.splitlines()[-1]
            # check if adding to end of comment
            if last_line.lower().startswith("c ") and last_line[-1] != "\n":
                return ret + "\n" + " " * BLANK_SPACE_CONTINUE
            if not last_line[-1].isspace():
                return ret + " "
            return ret

        ret = ""
        with warnings.catch_warnings(record=True) as ws:

            for key, node in self._tree.nodes.items():
                if key != "parameters":
                    ret += node.format()
                else:
                    printed_importance = False
                    final_param = next(reversed(node.nodes.values()))
                    for param in node.nodes.values():
                        if (
                            param["classifier"].prefix.value.lower()
                            in modifier_keywords
                        ):
                            cls = modifier_keywords[
                                param["classifier"].prefix.value.lower()
                            ]
                            attr, _ = self._INPUTS_TO_PROPERTY[cls]
                            if attr == "_importance":
                                if printed_importance:
                                    continue
                                printed_importance = True
                            # add trailing space to comment if necessary
                            ret = cleanup_last_line(ret)
                            ret += "\n".join(
                                getattr(self, attr).format_for_mcnp_input(
                                    mcnp_version, param is not final_param
                                )
                            )
                        else:
                            # add trailing space to comment if necessary
                            ret = cleanup_last_line(ret)
                            ret += param.format()
            # check for accidental empty lines from subsequent cell modifiers that didn't print
        self._flush_line_expansion_warning(ret, ws)
        ret = "\n".join([l for l in ret.splitlines() if l.strip()])
        return self.wrap_string_for_mcnp(ret, mcnp_version, True)

    @args_checked
    def clone(
        self,
        clone_material: bool = False,
        clone_region: bool = False,
        starting_number: ty.PositiveInt = None,
        step: ty.PositiveInt = None,
        add_collect: bool = True,
    ):
        """Create a new almost independent instance of this cell with a new number.

        This relies mostly on ``copy.deepcopy``.
        All properties and attributes will be a deep copy unless otherwise requested.
        The one exception is this will still be internally linked to the original problem.
        Even if ``clone_region`` is ``True`` the actual region object will be a copy.
        This means that changes to the new cell's geometry will be independent, but may or may not
        refer to the original surfaces.

        .. versionadded:: 0.5.0

        Parameters
        ----------
        clone_material : bool
            Whether to create a new clone of the material.
        clone_region : bool
            Whether to clone the underlying objects (Surfaces, Cells) of
            this cell's region.
        starting_number : int
            The starting number to request for a new cell number.
        step : int
            the step size to use to find a new valid number.

        Returns
        -------
        Cell
            a cloned copy of this cell.
        """
        if starting_number is None:
            starting_number = (
                self._problem.cells.starting_number if self._problem else 1
            )
        if step is None:
            step = self._problem.cells.step if self._problem else 1
        # get which properties to copy over
        keys = set(vars(self))
        keys.remove("_material")
        result = Cell.__new__(Cell)
        if clone_material:
            if self.material is not None:
                result._material = self._material.clone()
            else:
                result._material = None
        else:
            result._material = self._material
        special_keys = {"_surfaces", "_complements"}
        keys -= special_keys
        memo = {}

        def num(obj):
            if isinstance(obj, ty.Integral):
                return obj
            return obj.number

        # copy simple stuff
        for key in keys:
            attr = getattr(self, key)
            setattr(result, key, copy.deepcopy(attr, memo))
        # Clear collection ref so cloned cell isn't linked to original collection
        # This prevents number conflict checks against the original collection
        # The clone will be properly linked when added to a collection
        result._collection_ref = None
        # copy geometry
        for special in special_keys:
            new_objs = []
            collection = getattr(self, special)
            region_change_map = {}
            # get starting number
            if not self._problem:
                child_starting_number = starting_number
            else:
                child_starting_number = None
            # ensure the new geometry gets mapped to the new surfaces
            for obj in collection:
                if clone_region:
                    new_obj = obj.clone(
                        starting_number=child_starting_number, step=step
                    )
                    # avoid num collision of problem isn't handling this.
                    if child_starting_number:
                        child_starting_number = new_obj.number + step
                else:
                    new_obj = obj
                region_change_map[num(obj)] = (obj, new_obj)
                new_objs.append(new_obj)
            setattr(result, special, type(collection)(new_objs))
            if self.geometry:
                result.geometry.remove_duplicate_surfaces(region_change_map)
        if self._problem:
            result.number = self._problem.cells.request_number(starting_number, step)
            if add_collect:
                self._problem.cells.append(result)
        else:
            for number in itertools.count(starting_number, step):
                result.number = number
                if number != self.number:
                    break
        return result

# Copyright 2024, Battelle Energy Alliance, LLC All Rights Reserved.
import copy
from montepy.cells import Cells
from montepy.constants import BLANK_SPACE_CONTINUE
from montepy.data_inputs import importance, fill, lattice_input, universe_input, volume
from montepy.data_inputs.data_parser import PREFIX_MATCHES
from montepy.input_parser.cell_parser import CellParser
from montepy.input_parser import syntax_node
from montepy.errors import *
from montepy.numbered_mcnp_object import Numbered_MCNP_Object
from montepy.data_inputs.material import Material
from montepy.geometry_operators import Operator
from montepy.surfaces.half_space import HalfSpace, UnitHalfSpace
from montepy.surfaces.surface import Surface
from montepy.surface_collection import Surfaces
from montepy.universe import Universe
from montepy.utilities import *
import numbers


def _number_validator(self, number):
    if number <= 0:
        raise ValueError("number must be > 0")
    if self._problem:
        self._problem.cells.check_number(number)


def _link_geometry_to_cell(self, geom):
    geom._cell = self
    geom._add_new_children_to_cell(geom)


class Cell(Numbered_MCNP_Object):
    """
    Object to represent a single MCNP cell defined in CSG.

    .. versionchanged:: 0.2.0
        Removed the ``comments`` argument due to overall simplification of init process.


    :param input: the input for the cell definition
    :type input: Input

    .. seealso::

            * :manual63sec:`5.2`
            * :manual62:`55`
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

    def __init__(self, input=None):
        self._material = None
        self._old_number = self._generate_default_node(int, -1)
        self._load_blank_modifiers()
        self._old_mat_number = self._generate_default_node(int, -1)
        self._density_node = self._generate_default_node(float, None)
        self._surfaces = Surfaces()
        self._complements = Cells()
        self._number = self._generate_default_node(int, -1)
        super().__init__(input, self._parser)
        if not input:
            self._generate_default_tree()
        self._old_number = copy.deepcopy(self._tree["cell_num"])
        self._number = self._tree["cell_num"]
        mat_tree = self._tree["material"]
        self._old_mat_number = mat_tree["mat_number"]
        self._density_node = mat_tree["density"]
        self._density_node.is_negatable_float = True
        if self.old_mat_number != 0:
            self._is_atom_dens = not self._density_node.is_negative
        self._parse_geometry()
        self._parse_keyword_modifiers()

    def _parse_geometry(self):
        """
        Parses the cell's geometry definition, and stores it
        """
        geometry = self._tree["geometry"]
        if geometry is not None:
            self._geometry = HalfSpace.parse_input_node(geometry)
        else:
            self._geometry = None

    def _parse_keyword_modifiers(self):
        """
        Parses the parameters to make the object and load as an attribute
        """
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
                self._tree["parameters"].append(tree)

    def _load_blank_modifiers(self):
        """
        Goes through and populates all the modifier attributes
        """
        for input_class, (attr, _) in self._INPUTS_TO_PROPERTY.items():
            setattr(self, attr, input_class(in_cell_block=True))

    @property
    def importance(self):
        """
        The importances for this cell for various particle types.

        Each particle's importance is a property of Importance.
        e.g., ``cell.importance.photon = 1.0``.

        :returns: the importance for the Cell.
        :rtype: Importance
        """
        return self._importance

    @property
    def universe(self):
        """
        The Universe that this cell is in.

        :returns: the Universe the cell is in.
        :rtype: Universe
        """
        return self._universe.universe

    @property
    def fill(self):
        """
        the Fill object representing how this cell is filled.

        This not only describes the universe that is filling this,
        but more complex things like transformations, and matrix fills.

        :returns: The Fill object of how this cell is to be filled.
        :rtype: Fill
        """
        return self._fill

    @universe.setter
    def universe(self, value):
        if not isinstance(value, Universe):
            raise TypeError("universe must be set to a Universe")
        self._universe.universe = value

    @property
    def not_truncated(self):
        """
        Indicates if this cell has been marked as not being truncated for optimization.

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

        :rtype: bool
        :returns: True if this cell has been marked as not being truncated by the parent filled cell.
        """
        if self.universe.number == 0:
            return False
        return self._universe.not_truncated

    @not_truncated.setter
    def not_truncated(self, value):
        if not isinstance(value, bool):
            raise TypeError("not_truncated_by_parent must be a bool")
        if self.universe.number == 0 and value:
            raise ValueError("can't specify if cell is truncated for universe 0")
        self._universe._not_truncated = value

    @property
    def old_universe_number(self):
        """
        The original universe number read in from the input file.

        :returns: the number of the Universe for the cell in the input file.
        :rtype: int
        """
        return self._universe.old_number

    @property
    def lattice(self):
        """
        The type of lattice being used by the cell.

        :returns: the type of lattice being used
        :rtype: Lattice
        """
        return self._lattice.lattice

    @lattice.setter
    def lattice(self, value):
        self._lattice.lattice = value

    @lattice.deleter
    def lattice(self):
        self._lattice.lattice = None

    @property
    def volume(self):
        """
        The volume for the cell.

        Will only return a number if the volume has been manually set.

        :returns: the volume that has been manually set or None.
        :rtype: float, None
        """
        return self._volume.volume

    @volume.setter
    def volume(self, value):
        self._volume.volume = value

    @volume.deleter
    def volume(self):
        del self._volume.volume

    @property
    def volume_mcnp_calc(self):
        """
        Indicates whether or not MCNP will attempt to calculate the cell volume.

        This can be disabled by either manually setting the volume or disabling
        this calculation globally.
        This does not guarantee that MCNP will able to calculate the volume.
        Complex geometries may make this impossible.

        See :func:`~montepy.cells.Cells.allow_mcnp_volume_calc`

        :returns: True iff MCNP will try to calculate the volume for this cell.
        :rtype: bool
        """
        return self._volume.is_mcnp_calculated

    @property
    def volume_is_set(self):
        """
        Whether or not the volume for this cell has been set.

        :returns: true if the volume is manually set.
        :rtype: bool
        """
        return self._volume.set

    @make_prop_val_node("_old_number")
    def old_number(self):
        """
        The original cell number provided in the input file

        :rtype: int
        """
        pass

    @make_prop_val_node("_number", int, validator=_number_validator)
    def number(self):
        """
        The current cell number that will be written out to a new input.

        :rtype: int
        """
        pass

    @make_prop_pointer("_material", (Material, type(None)), deletable=True)
    def material(self):
        """
        The Material object for the cell.

        If the material is None this is considered to be voided.

        :rtype: Material
        """
        pass

    @make_prop_pointer("_geometry", HalfSpace, validator=_link_geometry_to_cell)
    def geometry(self):
        """
        The Geometry for this problem.

        .. versionadded:: 0.2.0
            Added with the new ability to represent true CSG geometry logic.

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

        :returns: this cell's geometry
        :rtype: HalfSpace
        """
        pass

    @property
    def geometry_logic_string(self):  # pragma: no cover
        """
        The original geoemtry input string for the cell.

        .. warning::
            .. deprecated:: 0.2.0
                This was removed to allow for :func:`geometry` to truly implement CSG geometry.

        :raise DeprecationWarning: Will always be raised as an error (which will cause program to halt).
        """
        raise DeprecationWarning(
            "Geometry_logic_string has been removed from cell. Use Cell.geometry instead."
        )

    @make_prop_val_node(
        "_density_node", (float, int, type(None)), base_type=float, deletable=True
    )
    def _density(self):
        """
        This is a wrapper to allow using the prop_val_node with mass_density and atom_density.
        """
        pass

    @property
    def atom_density(self) -> float:
        """
        The atom density of the material in the cell, in a/b-cm.

        :returns: the atom density. If no density is set or it is in mass density will return None.
        :rtype: float, None
        """
        if self._density and not self._is_atom_dens:
            raise AttributeError(f"Cell {self.number} is in mass density.")
        return self._density

    @atom_density.setter
    def atom_density(self, density: float):
        if not isinstance(density, numbers.Number):
            raise TypeError("Atom density must be a number.")
        elif density < 0:
            raise ValueError("Atom density must be a positive number.")
        self._is_atom_dens = True
        self._density = float(density)

    @atom_density.deleter
    def atom_density(self):
        self._density = None

    @property
    def mass_density(self) -> float:
        """
        The mass density of the material in the cell, in g/cc.

        :returns: the mass density. If no density is set or it is in atom density will return None.
        :rtype: float, None
        """
        if self._density and self._is_atom_dens:
            raise AttributeError(f"Cell {self.number} is in atom density.")
        return self._density

    @mass_density.setter
    def mass_density(self, density: float):
        if not isinstance(density, numbers.Number):
            raise TypeError("Mass density must be a number.")
        elif density < 0:
            raise ValueError("Mass density must be a positive number.")
        self._is_atom_dens = False
        self._density = float(density)

    @mass_density.deleter
    def mass_density(self):
        self._density = None

    @property
    def is_atom_dens(self):
        """
        Whether or not the density is in atom density [a/b-cm].

        True means it is in atom density, False means mass density [g/cc].

        :rtype: bool
        """
        return self._is_atom_dens

    @make_prop_val_node("_old_mat_number")
    def old_mat_number(self):
        """
        The material number provided in the original input file

        :rtype: int
        """
        pass

    @make_prop_pointer("_surfaces")
    def surfaces(self):
        """
        List of the Surface objects associated with this cell.

        This list does not convey any of the CGS Boolean logic

        :rtype: Surfaces
        """
        return self._surfaces

    @property
    def parameters(self):
        """
        A dictionary of the additional parameters for the object.

        e.g.: ``1 0 -1 u=1 imp:n=0.5`` has the parameters
        ``{"U": "1", "IMP:N": "0.5"}``

        :returns: a dictionary of the key-value pairs of the parameters.
        :rytpe: dict
        """
        return self._parameters

    @parameters.setter
    def parameters(self, params):
        if not isinstance(params, dict):
            raise TypeError("parameters must be a dict")
        self._parameters = params

    @property
    def complements(self):
        """
        The Cell objects that this cell is a complement of

        :rytpe: :class:`montepy.cells.Cells`
        """
        return self._complements

    @property
    def cells_complementing_this(self):
        """The cells which are a complement of this cell.

        This returns a generator.

        :rtype: generator
        """
        if self._problem:
            for cell in self._problem.cells:
                if cell != self:
                    if self in cell.complements:
                        yield cell

    def update_pointers(self, cells, materials, surfaces):
        """
        Attaches this object to the appropriate objects for surfaces and materials.

        :param cells: a Cells collection of the cells in the problem.
        :type cells: Cells
        :param materials: a materials collection of the materials in the problem
        :type materials: Materials
        :param surfaces: a surfaces collection of the surfaces in the problem
        :type surfaces: Surfaces
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
        self._geometry.update_pointers(cells, surfaces, self)

    def remove_duplicate_surfaces(self, deleting_dict):
        """Updates old surface numbers to prepare for deleting surfaces.

        :param deleting_dict: a dict of the surfaces to delete.
        :type deleting_dict: dict
        """
        new_deleting_dict = {}
        for dead_surface, new_surface in deleting_dict.items():
            if dead_surface in self.surfaces:
                new_deleting_dict[dead_surface] = new_surface
        if len(new_deleting_dict) > 0:
            self.geometry.remove_duplicate_surfaces(new_deleting_dict)
            for dead_surface in new_deleting_dict:
                self.surfaces.remove(dead_surface)

    def _update_values(self):
        if self.material:
            mat_num = self.material.number
            self._tree["material"]["density"].is_negative = not self.is_atom_dens
        else:
            mat_num = 0
        self._tree["material"]["mat_number"].value = mat_num
        self._geometry._update_values()
        self._tree.nodes["geometry"] = self.geometry.node
        for input_class, (attr, _) in self._INPUTS_TO_PROPERTY.items():
            getattr(self, attr)._update_values()

    def _generate_default_tree(self):
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
                "cell_num": self._generate_default_node(int, None),
                "material": material,
                "geometry": None,
                "parameters": syntax_node.ParametersNode(),
            },
        )

    def validate(self):
        """
        Validates that the cell is in a usable state.

        :raises: IllegalState if any condition exists that make the object incomplete.
        """
        if self._density and self.material is None:
            raise IllegalState(f"Cell {self.number} has a density set but no material")
        if self.material is not None and not self._density:
            raise IllegalState(
                f"Cell {self.number} has a non-void material but no density"
            )
        if self.geometry is None or len(self.geometry) == 0:
            raise IllegalState(f"Cell {self.number} has no geometry defined.")

    def link_to_problem(self, problem):
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
        for surface in self._surfaces:
            ret += str(surface) + "\n"
        ret += "\n"
        return ret

    def __lt__(self, other):
        return self.number < other.number

    def __invert__(self):
        base_node = UnitHalfSpace(self, True, True)
        return HalfSpace(base_node, Operator.COMPLEMENT)

    def format_for_mcnp_input(self, mcnp_version):
        """
        Creates a string representation of this MCNP_Object that can be
        written to file.

        :param mcnp_version: The tuple for the MCNP version that must be exported to.
        :type mcnp_version: tuple
        :return: a list of strings for the lines that this input will occupy.
        :rtype: list
        """
        self.validate()
        self._update_values()
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
        for key, node in self._tree.nodes.items():
            if key != "parameters":
                ret += node.format()
            else:
                printed_importance = False
                for param in node.nodes.values():
                    if param["classifier"].prefix.value.lower() in modifier_keywords:
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
                            getattr(self, attr).format_for_mcnp_input(mcnp_version)
                        )
                    else:
                        # add trailing space to comment if necessary
                        ret = cleanup_last_line(ret)
                        ret += param.format()
        return self.wrap_string_for_mcnp(ret, mcnp_version, True)

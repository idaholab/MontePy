from mcnpy.cells import Cells
from mcnpy.data_inputs import importance, fill, lattice_input, universe_input, volume
from mcnpy.data_inputs.data_parser import PREFIX_MATCHES
from mcnpy.input_parser.cell_parser import CellParser
from mcnpy.errors import *
from mcnpy.numbered_mcnp_object import Numbered_MCNP_Object
from mcnpy.data_inputs.material import Material
from mcnpy.surfaces.surface import Surface
from mcnpy.surface_collection import Surfaces
from mcnpy.universe import Universe
from mcnpy.utilities import *
import numbers


def _number_validator(self, number):
    if number <= 0:
        raise ValueError("number must be > 0")
    if self._problem:
        self._problem.cells.check_number(number)


class Cell(Numbered_MCNP_Object):
    """
    Object to represent a single MCNP cell defined in CGS.

    :param input: the input for the cell definition
    :type input: Input
    :param comments: the Comments block that preceded and are in the cell block if any.
    :type comments: list
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

    def __init__(self, input=None, comments=None):
        self._material = None
        self._old_number = self._generate_default_node(int, -1)
        self._load_blank_modifiers()
        self._old_mat_number = self._generate_default_node(int, -1)
        self._density_node = self._generate_default_node(float, None)
        self._surfaces = Surfaces()
        self._old_surface_numbers = set()
        self._complements = Cells()
        self._old_complement_numbers = set()
        self._number = self._generate_default_node(int, -1)
        super().__init__(input, self._parser, comments)
        if input:
            self._old_number = self._tree["cell_num"]
            # TODO break link
            self._number = self._old_number
            mat_tree = self._tree["material"]
            self._old_mat_number = mat_tree["mat_number"]
            if self.old_mat_number != 0:
                self._density_node = mat_tree["density"]
                self._is_atom_dens = mat_tree.get_value("density") >= 0
                self._density_node.value = abs(self._density)
            self._parse_geometry()
            self._parse_keyword_modifiers()

    def _parse_geometry(self):
        """
        Parses the cell's geometry definition, and stores it

        :returns: a tuple of j, param_found, j+ i = the index of the first non-geometry word,
                and param_found is True is cell parameter inputs are found
        """
        geometry = self._tree["geometry"]
        surfs, cells = geometry.get_geometry_identifiers()
        self._old_surface_numbers = surfs
        self._old_complement_numbers = cells

    def _parse_keyword_modifiers(self):
        """
        Parses the parameters to make the object and load as an attribute
        """
        for key, value in self.parameters.nodes.items():
            for input_class in PREFIX_MATCHES:
                prefix = input_class._class_prefix()
                if input_class in Cell._INPUTS_TO_PROPERTY and prefix in key.lower():
                    attr, ban_repeat = Cell._INPUTS_TO_PROPERTY[input_class]
                    # TODO how to do this without messing up tree
                    # del self._parameters[key]
                    input = input_class(in_cell_block=True, key=key, value=value)
                    if not getattr(self, attr).set_in_cell_block:
                        setattr(self, attr, input)
                    else:
                        if not ban_repeat:
                            getattr(self, attr).merge(
                                input_class(in_cell_block=True, key=key, value=value)
                            )

    def _load_blank_modifiers(self):
        """
        Goes through and populates all the modifier attributes
        """
        for input_class, (attr, foo) in self._INPUTS_TO_PROPERTY.items():
            setattr(self, attr, input_class(in_cell_block=True))

    @property
    def allowed_keywords(self):
        return Cell._ALLOWED_KEYWORDS

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
        self._mutated = True
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
        self._mutated = True
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
        Indicates whether or not the cell volume will attempt to be calculated by MCNP.

        This can be disabled by either manually setting the volume or disabling
        this calculation globally.
        This does not guarantee that MCNP will able to do so.
        Complex geometries may make this impossible.

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

    @make_prop_val_node(
        "_density_node", (float, int, type(None)), base_type=float, deletable=True
    )
    def _density(self):
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
        self._mutated = True
        self._is_atom_dens = True
        self._density = float(density)

    @atom_density.deleter
    def atom_density(self):
        self._mutated = True
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
        self._mutated = True
        self._is_atom_dens = False
        self._density = float(density)

    @mass_density.deleter
    def mass_density(self):
        self._mutated = True
        self._density = None

    @property
    def is_atom_dens(self):
        """
        Whether or not the density is in atom density [a/b-cm].

        True means it is in atom density, false means mass density [g/cc].

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

    @make_prop_pointer("_surfaces", (Surfaces, list), base_type=Surfaces)
    def surfaces(self):
        """
        List of the Surface objects associated with this cell.

        This list does not convey any of the CGS Boolean logic

        :rtype: Surfaces
        """
        return self._surfaces

    # TODO
    @surfaces.setter
    def surfaces(self, surfs):
        if type(surfs) not in [Surfaces, list]:
            raise TypeError("surfaces must be an instance of list or Surfaces")
        if isinstance(surfs, list):
            for surf in surfs:
                if not isinstance(surf, Surface):
                    raise TypeError(f"the surfaces element {surf} is not a Surface")
            surfs = Surfaces(surfs)
        self._mutated = True
        self._surfaces = surfs
        if self._problem:
            self._surfaces.link_to_problem(self._problem)

    @property
    def old_surface_numbers(self):
        """
        List of the surface numbers specified in the original input file.

        :rtype: list
        """
        return self._old_surface_numbers

    @property
    def old_complement_numbers(self):
        """
        List of the cell numbers that this is a complement of.

        :rtype: list
        """
        return self._old_complement_numbers

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
        self._mutated = True

    @property
    def complements(self):
        """
        The Cell objects that this cell is a complement of

        :rytpe: :class:`mcnpy.cells.Cells`
        """
        return self._complements

    @complements.setter
    def complements(self, complements):
        if type(complements) not in (Cells, list):
            raise TypeError("complements must be an instance of list or Cells")
        if isinstance(complements, list):
            for cell in complements:
                if not isinstance(cell, Cell):
                    raise TypeError(f"complements component {cell} is not a Cell")
            complements = Cells(complements)
        self._mutated = True
        self._complements = complements
        if self._problem:
            self._complements.link_to_problem(self._problem)

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

        if self._old_surface_numbers:
            for surface_number in self.old_surface_numbers:
                try:
                    surf = surfaces[surface_number]
                    if surf not in self.surfaces:
                        self._surfaces.append(surf)
                except KeyError:
                    raise BrokenObjectLinkError(
                        "Cell", self.number, "Surface", surface_number
                    )

        if self._old_complement_numbers:
            for complement_number in self.old_complement_numbers:
                try:
                    complement = cells[complement_number]
                    if complement not in self.complements:
                        self._complements.append(complement)
                except KeyError:
                    raise BrokenObjectLinkError(
                        "Cell", self.number, "Complement Cell", complement_number
                    )

    def remove_duplicate_surfaces(self, deleting_dict):
        """Updates old surface numbers to prepare for deleting surfaces.

        Note: update_pointers must be ran again.
        For the deleting_dict the key is the old surface,
        and the value is the new one.

        :param deleting_dict: a dict of the surfaces to delete.
        :type deleting_dict: dict
        """
        will_update = False
        for dead_surface in deleting_dict:
            if dead_surface in self.surfaces:
                will_update = True
                break
        if will_update:
            self._mutated = True
            # force logic string to known state
            self.update_geometry_logic_string()
            matching_surfaces = {}
            for dead_surface in deleting_dict:
                if dead_surface in self.surfaces:
                    matching_surfaces[dead_surface.number] = deleting_dict[
                        dead_surface
                    ].number
                    old_old = dead_surface.old_number
                    new_old = deleting_dict[dead_surface].old_number
                    self._old_surface_numbers = [
                        new_old if item == old_old else item
                        for item in self._old_surface_numbers
                    ]
            self._update_geometry_logic_by_map(matching_surfaces, {})

    @property
    def modifier_block_print_changed(self):
        """
        Whether or not the print style of the cell modifiers has changed.

        For instance if the file had importances in the cell block, but the user
        changed that to print in the data block. This would return True in that situation.

        :rtype: bool
        """
        for attr, _ in Cell._CARDS_TO_PROPERTY.values():
            if hasattr(self, attr):
                if getattr(self, attr).has_changed_print_style:
                    return True
        return False

    def _update_values(self):
        if self.material:
            mat_num = self.material.number
        else:
            mat_num = 0
        self._tree["material"]["mat_number"].value = mat_num

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
        if len(self.surfaces) == 0 and len(self.complements) == 0:
            raise IllegalState(
                f"Cell {self.number} has no surfaces nor complemented cells attached to it"
            )

    def format_for_mcnp_input(self, mcnp_version):
        self.validate()
        self._update_values()
        return self.wrap_string_for_mcnp(self._tree.format(), mcnp_version, True)

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
                units = "g/cm3"
            else:
                units = "atom/b-cm"
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

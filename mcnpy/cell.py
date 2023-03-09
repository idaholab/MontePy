import itertools
from mcnpy.cells import Cells
from mcnpy.data_cards import fill, importance, lattice_card, universe_card, volume
from mcnpy.data_cards.data_parser import PREFIX_MATCHES
from mcnpy.errors import *
from mcnpy.numbered_mcnp_card import Numbered_MCNP_Card
from mcnpy.data_cards.material import Material
from mcnpy.num_limits import CELL_MAX_NUM
from mcnpy.surfaces.surface import Surface
from mcnpy.surface_collection import Surfaces
from mcnpy.universe import Universe
from mcnpy.utilities import *
import re
import numbers


class Cell(Numbered_MCNP_Card):
    """
    Object to represent a single MCNP cell defined in CGS.

    :param input_card: the Card input for the cell definition
    :type input_card: Card
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
    _CARDS_TO_PROPERTY = {
        importance.Importance: ("_importance", False),
        volume.Volume: ("_volume", True),
        universe_card.UniverseCard: ("_universe", True),
        lattice_card.LatticeCard: ("_lattice", True),
        fill.Fill: ("_fill", True),
    }

    def __init__(self, input_card=None, comment=None):
        super().__init__(input_card, comment)
        self._material = None
        self._old_cell_number = None
        self._load_blank_modifiers()
        self._old_mat_number = None
        self._geometry_logic_string = None
        self._density = None
        self._surfaces = Surfaces()
        self._old_surface_numbers = set()
        self._complements = Cells()
        self._old_complement_numbers = set()
        self._cell_number = -1
        if input_card:
            words = input_card.words
            i = 0
            # cell number
            try:
                cell_num = int(words[i])
                Cell._check_number(cell_num)
                self._old_cell_number = cell_num
                self._cell_number = cell_num
                i += 1
            except ValueError:
                raise MalformedInputError(
                    input_card, f"{words[0]} can not be parsed as a cell number."
                )
            if words[i].lower() == "like":
                raise UnsupportedFeature(
                    "Currently the LIKE option in cell cards is unsupported"
                )
            # material
            try:
                mat_num = int(words[i])
                self._old_mat_number = mat_num
                i += 1

            except ValueError:
                raise MalformedInputError(
                    input_card, f"{words[1]} can not be parsed as a material number."
                )
            # density
            if mat_num > 0:
                try:
                    density = fortran_float(words[i])
                    self._density = abs(density)
                    i += 1
                    if density > 0:
                        self._is_atom_dens = True
                    else:
                        self._is_atom_dens = False

                except ValueError:
                    raise MalformedInputError(
                        input_card,
                        f"{words[2]} can not be parsed as a material density.",
                    )
            self._parse_geometry(i, words)
            self._parse_keyword_modifiers()

    def _parse_geometry(self, i, words):
        """
        Parses the cell's geometry definition, and stores it

        :param words: list of the input card words
        :type words: list
        :param i: the index of the first geometry word
        :type i: int
        :returns: a tuple of j, param_found, j+ i = the index of the first non-geometry word,
                and param_found is True is cell parameter inputs are found
        """
        non_surface_finder = re.compile(r"[a-zA-Z]")
        surface_finder = re.compile(r"[^#]*?(\d+)")
        cell_finder = re.compile(r"#(\d+)")
        geometry_string = ""
        for j, word in enumerate(words[i:]):
            if non_surface_finder.search(word):
                break
            else:
                geometry_string += word + " "
                match = cell_finder.search(word)
                if match:
                    self._old_complement_numbers.add(int(match.group(1)))
                else:
                    for surface in surface_finder.findall(word):
                        self._old_surface_numbers.add(int(surface))
        self._geometry_logic_string = geometry_string

    def _parse_keyword_modifiers(self):
        """
        Parses the parameters to make the object and load as an attribute
        """
        for key, value in dict(self._parameters).items():
            for prefix, card_class in PREFIX_MATCHES.items():
                if (
                    card_class in Cell._CARDS_TO_PROPERTY
                    and prefix.upper() in key.upper()
                ):
                    attr, ban_repeat = Cell._CARDS_TO_PROPERTY[card_class]
                    del self._parameters[key]
                    card = card_class(in_cell_block=True, key=key, value=value)
                    if not getattr(self, attr).set_in_cell_block:
                        setattr(self, attr, card)
                    else:
                        if not ban_repeat:
                            getattr(self, attr).merge(
                                card_class(in_cell_block=True, key=key, value=value)
                            )

    def _load_blank_modifiers(self):
        """
        Goes through and populates all the modifier attributes
        """
        for card_class, (attr, foo) in self._CARDS_TO_PROPERTY.items():
            setattr(self, attr, card_class(in_cell_block=True))

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

    @property
    def old_number(self):
        """
        The original cell number provided in the input file

        :rtype: int
        """
        return self._old_cell_number

    @property
    def number(self):
        """
        The current cell number that will be written out to a new input.

        :rtype: int
        """
        return self._cell_number

    @number.setter
    def number(self, number):
        Cell._check_number(number)
        if self._problem:
            self._problem.cells.check_number(number)
        self._mutated = True
        self._cell_number = number

    @classmethod
    def _check_number(cls, number):
        if not isinstance(number, int):
            raise TypeError("number must be an int")
        if number <= 0 or number > CELL_MAX_NUM:
            raise NumberUnallowedError("Cell", number)

    @property
    def material(self):
        """
        The Material object for the cell.

        If the material is None this is considered to be voided.

        :rtype: Material
        """
        return self._material

    @material.setter
    def material(self, mat=None):
        if mat:
            if not isinstance(mat, Material):
                raise TypeError("material must be a Material instance")
        self._mutated = True
        self._material = mat

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

    @property
    def old_mat_number(self):
        """
        The material number provided in the original input file

        :rtype: int
        """
        return self._old_mat_number

    @property
    def surfaces(self):
        """
        List of the Surface objects associated with this cell.

        This list does not convey any of the CGS Boolean logic

        :rtype: Surfaces
        """
        return self._surfaces

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
    def geometry_logic_string(self):
        """
        The original geoemtry input string for the cell.

        .. warning::
            This will be deprecated and completely removed in version 0.1.5.

        :returns: the geometry logic string for this cell.
        :rtype: str
        """
        return self._geometry_logic_string

    @geometry_logic_string.setter
    def geometry_logic_string(self, string):
        if not isinstance(string, str):
            raise TypeError("geometry_logic_string must a string")
        self._mutated = True
        self._geometry_logic_string = string

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
        if self._old_mat_number is not None:
            if self._old_mat_number > 0:
                try:
                    self._material = materials[self._old_mat_number]
                except KeyError:
                    raise BrokenObjectLinkError(
                        "Cell", self.number, "Material", self.old_mat_number
                    )
            else:
                self._material = None

        if self._old_surface_numbers:
            for surface_number in self._old_surface_numbers:
                try:
                    self._surfaces.append(surfaces[surface_number])
                except KeyError:
                    raise BrokenObjectLinkError(
                        "Cell", self.number, "Surface", surface_number
                    )

        if self._old_complement_numbers:
            for complement_number in self._old_complement_numbers:
                try:
                    self._complements.append(cells[complement_number])
                except KeyError:
                    raise BrokenObjectLinkError(
                        "Cell", self.number, "Complement Cell", complement_number
                    )

    def update_geometry_logic_string(self):
        """
        Updates the geometry logic string with new surface numbers.

        This is a bit of a hacky temporary solution while true boolean logic is implemented.

        .. warning::
            This will be deprecated and removed in version 0.1.5

        """
        matching_surfaces = {}
        matching_complements = {}
        for cell in self.complements:
            if cell.old_number:
                matching_complements[cell.old_number] = cell.number
            else:
                matching_complements[cell.number] = cell.number
        for surface in self.surfaces:
            if surface.old_number:
                matching_surfaces[surface.old_number] = surface.number
            else:
                matching_surfaces[surface.number] = surface.number
        self._update_geometry_logic_by_map(matching_surfaces, matching_complements)

    def _update_geometry_logic_by_map(
        self, mapping_surface_dict, mapping_complement_dict
    ):
        """Updates geometry logic string based on a map.

        .. warning::
            This will be deprecated and removed in version 0.1.5

        :param mapping_surface_dict: A dict mapping the old surface number to the new one. The key is the old one.
        :type mapping_dict: dict
        :param mapping_complement_dict: A dict mapping the old cell number to the new one. The key is the old one.
        :type mapping_complement_dict: dict
        """
        # make sure all numbers are surrounded by non-digit chars
        pad_string = " " + self.geometry_logic_string + " "
        # need to move all numbers to outside of feasible numbers first, before moving numbers around
        # it's possible when shifting numbers by a little to have an
        # overlap between the set of old and new numbers
        temp_numbers = itertools.count(start=int(1e8))
        temp_cells = {}
        temp_surfaces = {}
        for is_final_pass in [False, True]:
            for complement in mapping_complement_dict:
                if is_final_pass:
                    old_num = temp_cells[complement]
                    new_num = mapping_complement_dict[complement]
                else:
                    old_num = complement
                    new_num = next(temp_numbers)
                    temp_cells[complement] = new_num
                pad_string = re.sub(
                    rf"#{old_num}(\D)",
                    r"#{new_num}\g<1>".format(new_num=new_num),
                    pad_string,
                )
            for surface in mapping_surface_dict:
                if is_final_pass:
                    old_num = temp_surfaces[surface]
                    new_num = mapping_surface_dict[surface]
                else:
                    old_num = surface
                    new_num = next(temp_numbers)
                    temp_surfaces[surface] = new_num
                pad_string = re.sub(
                    rf"([^#\d]){old_num}(\D)",
                    r"\g<1>{new_num}\g<2>".format(new_num=new_num),
                    pad_string,
                )
        self._geometry_logic_string = pad_string

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
        if len(self.geometry_logic_string) == 0:
            raise IllegalState(f"Cell {self.number} has no geometry defined")

    def format_for_mcnp_input(self, mcnp_version):
        mutated = self.mutated
        self.validate()
        if not mutated:
            if self.material:
                mutated = self.material.mutated
            for surf in self.surfaces:
                if surf.mutated:
                    mutated = True
                    break
        if not mutated:
            mutated = self.modifier_block_print_changed

        if mutated:
            ret = super().format_for_mcnp_input(mcnp_version)
            self.update_geometry_logic_string()
            buffList = [str(self.number)]
            if self.material:
                buffList.append(str(self.material.number))
                if self.is_atom_dens:
                    dens = self.atom_density
                else:
                    dens = -self.mass_density
                buffList.append(f"{dens:.4g}")
            else:
                buffList.append("0")
            ret += Cell.wrap_words_for_mcnp(buffList, mcnp_version, True)
            ret += Cell.wrap_string_for_mcnp(
                self.geometry_logic_string, mcnp_version, False
            )
            if self.parameters:
                strings = []
                keys = list(self.parameters.keys())
                for key in keys:
                    value = self.parameters[key]
                    if isinstance(value, list):
                        value = " ".join(value)
                    strings.append(f"{key}={value}")
                ret += Cell.wrap_words_for_mcnp(strings, mcnp_version, False)
            for attr, _ in Cell._CARDS_TO_PROPERTY.values():
                if hasattr(self, attr):
                    if (
                        self._problem
                        and not self._problem.print_in_data_block[
                            getattr(self, attr).class_prefix
                        ]
                    ):
                        ret += getattr(self, attr).format_for_mcnp_input(mcnp_version)
        else:
            ret = self._format_for_mcnp_unmutated(mcnp_version)
        return ret

    def link_to_problem(self, problem):
        super().link_to_problem(problem)
        self.complements.link_to_problem(problem)
        self.surfaces.link_to_problem(problem)
        for attr, _ in Cell._CARDS_TO_PROPERTY.values():
            card = getattr(self, attr, None)
            if card:
                card.link_to_problem(problem)

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
        ret = f"CELL: {self._cell_number} \n"
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

import itertools
from mcnpy.cells import Cells
from mcnpy.data_inputs import importance, volume
from mcnpy.data_inputs.data_parser import PREFIX_MATCHES
from mcnpy.input_parser.cell_parser import CellParser
from mcnpy.errors import *
from mcnpy.mcnp_input import MCNP_Input
from mcnpy.data_inputs.material import Material
from mcnpy.surfaces.surface import Surface
from mcnpy.surface_collection import Surfaces
from mcnpy.utilities import *
import re
import numbers


class Cell(MCNP_Input):
    """
    Object to represent a single MCNP cell defined in CGS.

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
    }
    _parser = CellParser()

    def __init__(self, input=None, comment=None):
        """
        :param input: the input for the cell definition
        :type input: Input
        :param comment: the Comment block that preceded this blog if any.
        :type comment: Comment
        """
        super().__init__(input, comment)
        self._material = None
        self._old_number = None
        self._load_blank_modifiers()
        self._old_mat_number = None
        self._density = None
        self._surfaces = Surfaces()
        self._old_surface_numbers = set()
        self._complements = Cells()
        self._old_complement_numbers = set()
        self._number = -1
        if input:
            self._tree = self._parser.parse(input.tokenize())
            if self._tree is None:
                raise MalformedInputError(
                    input, "There is a syntax error with the input."
                )
            self._old_number = int(self._tree.get_value("cell_num"))
            self._number = self._old_number
            mat_tree = self._tree["material"]
            self._old_mat_number = int(mat_tree.get_value("mat_number"))
            if self._old_mat_number != 0:
                self._density = abs(mat_tree.get_value("density"))
                self._is_atom_dens = mat_tree.get_value("density") >= 0
            self._parse_geometry

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
        for key, value in dict(self._parameters).items():
            for prefix, input_class in PREFIX_MATCHES.items():
                if (
                    input_class in Cell._INPUTS_TO_PROPERTY
                    and prefix.upper() in key.upper()
                ):
                    attr, ban_repeat = Cell._INPUTS_TO_PROPERTY[input_class]
                    del self._parameters[key]
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
        return self._importance

    @property
    def volume(self):
        """
        The volume for the cell.

        Will only return a number if the volume has been manually set.

        :returns: the volume that has been manually set or None.
        :rtype: float
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
        return self._old_number

    @property
    def number(self):
        """
        The current cell number that will be written out to a new input.

        :rtype: int
        """
        return self._number

    @number.setter
    def number(self, number):
        if not isinstance(number, int):
            raise TypeError("number must be an int")
        if number <= 0:
            raise ValueError("number must be > 0")
        if self._problem:
            self._problem.cells.check_number(number)
        self._mutated = True
        self._number = number

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

        :rtype: float
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

    @property
    def mass_density(self) -> float:
        """
        The mass density of the material in the cell, in g/cc.

        :rtype: float
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

    @property
    def is_atom_dens(self):
        """
        Whether or not the density is in atom density [a/b-cm].

        True means it is in atom density, false means mass density [g/cc]
        """
        return self._is_atom_dens

    @property
    def old_mat_number(self):
        """
        The material number provided in the original input file
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
        The original surface input for the cell

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
        A dictionary of the additional parameters for the cell.

        e.g.: Universes, and imp:n
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

        :rytpe: Cells
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

    @property
    def cells_complementing_this(self):
        """The cells which are a complement of this cell.

        This returns a generator.
        """
        if self._problem:
            for cell in self._problem.cells:
                if cell != self:
                    if self in cell.complements:
                        yield cell

    def update_pointers(self, cell_dict, material_dict, surface_dict):
        """
        Attaches this object to the appropriate objects for surfaces and materials.

        :param material_dict: a dictionary mapping the material number to the Material object.
        :type material_dict: dict
        :param surface_dict: a dictionary mapping the surface number to the Surface object.
        :type surface_dict: dict
        """
        self._surfaces = Surfaces()
        self._complements = Cells()
        if self._old_mat_number is not None:
            if self._old_mat_number > 0:
                try:
                    self._material = material_dict[self._old_mat_number]
                except KeyError:
                    raise BrokenObjectLinkError(
                        "Cell", self.number, "Material", self.old_mat_number
                    )
            else:
                self._material = None

        if self._old_surface_numbers:
            for surface_number in self._old_surface_numbers:
                try:
                    self._surfaces.append(surface_dict[surface_number])
                except KeyError:
                    raise BrokenObjectLinkError(
                        "Cell", self.number, "Surface", surface_number
                    )

        if self._old_complement_numbers:
            for complement_number in self._old_complement_numbers:
                try:
                    self._complements.append(cell_dict[complement_number])
                except KeyError:
                    raise BrokenObjectLinkError(
                        "Cell", self.number, "Complement Cell", complement_number
                    )

    def update_geometry_logic_string(self):
        """
        Updates the geometry logic string with new surface numbers.

        This is a bit of a hacky temporary solution while true boolean logic is implemented.
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
        for attr, _ in Cell._INPUTS_TO_PROPERTY.values():
            if hasattr(self, attr):
                if getattr(self, attr).has_changed_print_style:
                    return True
        return False

    def format_for_mcnp_input(self, mcnp_version):
        mutated = self.mutated
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
                """
                Yes this is hacky voodoo.
                We don't know if it's necessary, but are too scared to remove it.
                The goal is to make sure that the FILL parameter is always the last 
                one on a cell input.

                This is based on a superstition that MCNP is less likely to crash when 
                data is given this way; but we just don't know.
                You've used MCNP are you that surprised we had to do this?

                MCNP giveth, and MCNP taketh. 
                """
                if "FILL" in keys:
                    keys.remove("FILL")
                    keys.append("FILL")
                for key in keys:
                    value = self.parameters[key]
                    if isinstance(value, list):
                        value = " ".join(value)
                    strings.append(f"{key}={value}")
                ret += Cell.wrap_words_for_mcnp(strings, mcnp_version, False)
            for attr, _ in Cell._INPUTS_TO_PROPERTY.values():
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
        return f"CELL: {self.number}, mat: {mat_num}, {dens_str}"

    def __repr__(self):
        ret = f"CELL: {self._number} \n"
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

import itertools
from mcnpy.cells import Cells
from mcnpy.data_cards import importance
from mcnpy.data_cards.data_parser import PREFIX_MATCHES
from mcnpy.errors import *
from mcnpy.mcnp_card import MCNP_Card
from mcnpy.input_parser.block_type import BlockType
from mcnpy.data_cards.material import Material
from mcnpy.surfaces.surface import Surface
from mcnpy.surface_collection import Surfaces
from mcnpy.utilities import *
import re
import numbers


class Cell(MCNP_Card):
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
    _CARDS_TO_PROPERTY = {importance.Importance: ("_importance", False)}

    def __init__(self, input_card=None, comment=None):
        """
        :param input_card: the Card input for the cell definition
        :type input_card: Card
        :param comment: the Comment block that preceded this blog if any.
        :type comment: Comment
        """
        super().__init__(input_card, comment)
        self._material = None
        self._old_cell_number = None
        self._importance = importance.Importance(in_cell_block=True)
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
                    if self._problem:
                        card.link_to_problem(self._problem)
                    if not hasattr(self, attr):
                        setattr(self, attr, card)
                    else:
                        if not ban_repeat:
                            getattr(self, attr).merge(
                                card_class(in_cell_block=True, key=key, value=value)
                            )
                        else:
                            raise MalformedInputError(
                                f"{key}={value}",
                                f"Can't repeat the card for type {card_class}",
                            )

    @property
    def allowed_keywords(self):
        return Cell._ALLOWED_KEYWORDS

    @property
    def block_type(self):
        return BlockType.CELL

    @property
    def importance(self):
        return self._importance

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
        if not isinstance(number, int):
            raise TypeError("number must be an int")
        if number <= 0:
            raise ValueError("number must be > 0")
        if self._problem:
            self._problem.cells.check_number(number)
        self._mutated = True
        self._cell_number = number

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
                    fr"#{old_num}(\D)",
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
                    fr"([^#\d]){old_num}(\D)",
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
        for attr, _ in Cell._CARDS_TO_PROPERTY.values():
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
                one on a cell card.

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
        self._importance.link_to_problem(problem)

    def __str__(self):
        ret = f"CELL: {self._cell_number} \n"
        ret += str(self._material) + "\n"
        if self._density:
            ret += f"density: {self._density} "
            if self._is_atom_dens:
                ret += "atom/b-cm"
            else:
                ret += "g/cc"
        for surface in self._surfaces:
            ret += str(surface) + "\n"
        ret += "\n"
        return ret

    def __lt__(self, other):
        return self.number < other.number

    def __repr__(self):
        return self.__str__()

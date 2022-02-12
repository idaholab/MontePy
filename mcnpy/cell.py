import itertools
from mcnpy.errors import *
from mcnpy.mcnp_card import MCNP_Card
from mcnpy.data_cards.material import Material
from mcnpy.surfaces.surface import Surface
from mcnpy.utilities import *
import re


class Cell(MCNP_Card):
    """
    Object to represent a single MCNP cell defined in CGS.

    """

    def __init__(self, input_card=None, comment=None):
        """
        :param input_card: the Card input for the cell definition
        :type input_card: Card
        :param comment: the Comment block that preceded this blog if any.
        :type comment: Comment
        """
        super().__init__(comment)
        self.__surfaces = []
        self.__old_surface_numbers = []
        self.__complements = []
        self.__old_complement_numbers = []
        self.__parameters = {}
        self.__old_cell_number = None
        self.__old_mat_number = None
        self.__material = None
        if input_card:
            words = input_card.words
            i = 0
            # cell number
            try:
                cell_num = int(words[i])
                self.__old_cell_number = cell_num
                self.__cell_number = cell_num
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
                self.__old_mat_number = mat_num
                i += 1

            except ValueError:
                raise MalformedInputError(
                    input_card, f"{words[1]} can not be parsed as a material number."
                )
            # density
            if mat_num > 0:
                try:
                    density = fortran_float(words[i])
                    self.__density = abs(density)
                    i += 1
                    if density > 0:
                        self.__is_atom_dens = True
                    else:
                        self.__is_atom_dens = False

                except ValueError:
                    raise MalformedInputError(
                        input_card,
                        f"{words[2]} can not be parsed as a material density.",
                    )
            j, param_found = self.__parse_geometry(i, words)
            if param_found:
                self.__parse_parameters(i, j, words)

    def __parse_geometry(self, i, words):
        """
        Parses the cell's geometry definition, and stores it

        :param words: list of the input card words
        :type words: list
        :param i: the index of the first geometry word
        :type i: int
        :returns: a tuple of j, param_found, j+ i = the index of the first non-geometry word,
                and param_found is True is cell parameter inputs are found
        """
        non_surface_finder = re.compile("[a-zA-Z]")
        surface_finder = re.compile("[^#]*?(\d+)")
        cell_finder = re.compile("#(\d+)")
        geometry_string = ""
        param_found = False
        for j, word in enumerate(words[i:]):
            if non_surface_finder.search(word):
                param_found = True
                break
            else:
                geometry_string += word + " "
                match = cell_finder.match(word)
                if match:
                    self.__old_complement_numbers.append(int(match.group(1)))
                else:
                    for surface in surface_finder.findall(word):
                        self.__old_surface_numbers.append(int(surface))
        self.__geometry_logic_string = geometry_string
        return (j, param_found)

    def __parse_parameters(self, i, j, words):
        params_string = " ".join(words[i + j :])
        self.__parameters = {}
        fragments = params_string.split("=")
        key = ""
        next_key = ""
        value = ""
        for i, fragment in enumerate(fragments):
            fragment = fragment.split()
            if i == 0:
                key = fragment[0]
            elif i == len(fragments) - 1:
                if next_key:
                    key = next_key
                value = fragment[0]
            else:
                if next_key:
                    key = next_key
                value = fragment[0:-1]
                next_key = fragment[-1]
            if key and value:
                self.__parameters[key.upper()] = "".join(value)

    @property
    def old_cell_number(self):
        """
        The original cell number provided in the input file

        :rtype: int
        """
        return self.__old_cell_number

    @property
    def cell_number(self):
        """
        The current cell number that will be written out to a new input.

        :rtype: int
        """
        return self.__cell_number

    @cell_number.setter
    def cell_number(self, number):
        assert isinstance(number, int)
        assert number > 0
        self.__cell_number = number

    @property
    def material(self):
        """
        The Material object for the cell.

        If the material is None this is considered to be voided.
        :rtype: Material
        """
        return self.__material

    @material.setter
    def material(self, mat=None):
        if mat:
            assert isinstance(mat, Material)
        self.__material = mat

    @property
    def density(self):
        """
        The density of the material in the cell.

        :rtype: float
        """
        return self.__density

    @density.setter
    def density(self, density_tuple):
        """
        :param density_tuple: A tuple of the density, and is_atom_dens
        :type density_tuple:
            :param density: the density of the material [a/b-cm] or [g/cc]
            :type density: float
            :param is_atom_dens: if True the density is atom density
            :type is_atom_dens: bool
        """
        density, is_atom_dens = density_tuple
        assert isinstance(density, float)
        assert isinstance(is_atom_dens, bool)
        self.__density = density
        self.__is_atom_dens = is_atom_dens

    @property
    def is_atom_dens(self):
        """
        Whether or not the density is in atom density [a/b-cm].

        True means it is in atom density, false means mass density [g/cc]
        """
        return self.__is_atom_dens

    @property
    def old_mat_number(self):
        """
        The material number provided in the original input file
        """
        return self.__old_mat_number

    @property
    def surfaces(self):
        """
        List of the Surface objects associated with this cell.

        This list does not convey any of the CGS Boolean logic
        :rtype: list
        """
        return self.__surfaces

    @surfaces.setter
    def surfaces(self, surfs):
        assert isinstance(surfs, list)
        for surf in surfs:
            assert isinstance(surf, Surface)
        self.__surfaces = surfs

    @property
    def old_surface_numbers(self):
        """
        List of the surface numbers specified in the original input file.

        :rtype: list
        """
        return self.__old_surface_numbers

    @property
    def old_complement_numbers(self):
        """
        List of the cell numbers that this is a complement of.

        :rtype: list
        """
        return self.__old_complement_numbers

    @property
    def geometry_logic_string(self):
        """
        The original surface input for the cell

        :rtype: str
        """
        return self.__geometry_logic_string

    @geometry_logic_string.setter
    def geometry_logic_string(self, string):
        assert isinstance(string, str)
        self.__geometry_logic_string = string

    @property
    def parameters(self):
        """
        A dictionary of the additional parameters for the cell.

        e.g.: Universes, and imp:n
        """
        if hasattr(self, "_Cell__parameters"):
            return self.__parameters

    @property
    def complements(self):
        """
        The Cell objects that this cell is a complement of
        """
        return self.__complements

    @complements.setter
    def complements(self, complements):
        assert isinstance(complements, list)
        for cell in complements:
            assert isinstance(cell, Cell)
        self.__complements = complements

    def update_pointers(self, cell_dict, material_dict, surface_dict):
        """
        Attaches this object to the appropriate objects for surfaces and materials.

        :param material_dict: a dictionary mapping the material number to the Material object.
        :type material_dict: dict
        :param surface_dict: a dictionary mapping the surface number to the Surface object.
        :type surface_dict: dict
        """
        self.__surfaces = []
        self.__complements = []
        if self.__old_mat_number is not None:
            if self.__old_mat_number > 0:
                self.__material = material_dict[self.__old_mat_number]
            else:
                self.__material = None

        if self.__old_surface_numbers:
            for surface_number in self.__old_surface_numbers:
                self.__surfaces.append(surface_dict[surface_number])

        if self.__old_complement_numbers:
            for complement_number in self.__old_complement_numbers:
                self.__complements.append(cell_dict[complement_number])

    def update_geometry_logic_string(self):
        """
        Updates the geometry logic string with new surface numbers.

        This is a bit of a hacky temporary solution while true boolean logic is implemented.
        """
        matching_surfaces = {}
        matching_complements = {}
        for cell in self.complements:
            if cell.old_cell_number:
                matching_complements[cell.old_cell_number] = cell.cell_number
            else:
                matching_complements[cell.cell_number] = cell.cell_number
        for surface in self.surfaces:
            if surface.old_surface_number:
                matching_surfaces[surface.old_surface_number] = surface.surface_number
            else:
                matching_surfaces[surface.surface_number] = surface.surface_number
        self.__update_geometry_logic_by_map(matching_surfaces, matching_complements)

    def __update_geometry_logic_by_map(
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
                    f"#{old_num}(\D)",
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
                    f"([^#\d]){old_num}(\D)",
                    r"\g<1>{new_num}\g<2>".format(new_num=new_num),
                    pad_string,
                )
        self.__geometry_logic_string = pad_string

    def remove_duplicate_surfaces(self, deleting_dict):
        """Updates old surface numbers to prepare for deleting surfaces.

        Note: update_pointers must be ran again.
        :param deleting_dict: a dict of the surfaces to delete.
            The key is the old surface, and the value is the new one.
        :type deleting_dict: dict
        """
        will_update = False
        for dead_surface in deleting_dict:
            if dead_surface in self.surfaces:
                will_update = True
                break
        if will_update:
            # force logic string to known state
            self.update_geometry_logic_string()
            matching_surfaces = {}
            for dead_surface in deleting_dict:
                if dead_surface in self.surfaces:
                    matching_surfaces[dead_surface.surface_number] = deleting_dict[
                        dead_surface
                    ].surface_number
                    old_old = dead_surface.old_surface_number
                    new_old = deleting_dict[dead_surface].old_surface_number
                    self.__old_surface_numbers = [
                        new_old if item == old_old else item
                        for item in self.__old_surface_numbers
                    ]
            self.__update_geometry_logic_by_map(matching_surfaces, {})

    def format_for_mcnp_input(self, mcnp_version):
        self.update_geometry_logic_string()
        ret = super().format_for_mcnp_input(mcnp_version)
        buffList = [str(self.cell_number)]
        if self.material:
            buffList.append(str(self.material.material_number))
            dens = 0
            if self.is_atom_dens:
                dens = self.density
            else:
                dens = -self.density
            buffList.append(f"{dens:.4g}")
        else:
            buffList.append("0")
        ret += Cell.wrap_words_for_mcnp(buffList, mcnp_version, True)
        ret += Cell.wrap_string_for_mcnp(
            self.geometry_logic_string, mcnp_version, False
        )
        if self.parameters:
            strings = []
            for key, value in self.parameters.items():
                if isinstance(value, list):
                    value = " ".join(value)
                strings.append(f"{key}={value}")
            ret += Cell.wrap_words_for_mcnp(strings, mcnp_version, False)
        return ret

    def __str__(self):
        ret = f"CELL: {self.__cell_number} \n"
        ret += str(self.__material) + "\n"
        if hasattr(self, "_Cell__density"):
            ret += f"density: {self.__density} "
            if self.__is_atom_dens:
                ret += "atom/b-cm"
            else:
                ret += "g/cc"
        for surface in self.__surfaces:
            ret += str(surface) + "\n"
        ret += "\n"
        return ret

    def __lt__(self, other):
        return self.cell_number < other.cell_number

    def __repr__(self):
        return self.__str__()

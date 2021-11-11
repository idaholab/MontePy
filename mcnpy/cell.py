from .errors import *
from .mcnp_card import MCNP_Card
from .material import Material
import re
from .surfaces import Surface


class Cell(MCNP_Card):
    """
    Object to represent a single MCNP cell defined in CGS.

    """

    def __init__(self, input_card, comment=None):
        """
        :param input_card: the Card input for the cell definition
        :type input_card: Card
        :param comment: the Comment block that preceded this blog if any.
        :type comment: Comment
        """
        super().__init__(comment)
        self.__surfaces = []
        self.__old_surface_numbers = []
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
                density = float(words[i])
                self.__density = abs(density)
                i += 1
                if density > 0:
                    self.__is_atom_dens = False
                else:
                    self.__is_atom_dens = True

            except ValueError:
                raise MalformedInputError(
                    input_card,
                    f"{words[2]} can not be parsed as a material number.",
                )
        non_surface_finder = re.compile("[a-zA-Z]")
        surface_finder = re.compile("\d+")
        surface_string = ""
        param_found = False
        for j, word in enumerate(words[i:]):
            if non_surface_finder.search(word):
                param_found = True
                break
            else:
                surface_string += word + " "
                for surface in surface_finder.findall(word):
                    self.__old_surface_numbers.append(int(surface))
        self.__surface_logic_string = surface_string
        if param_found:
            params_string = " ".join([word] + words[i + j : 0])
            self.__parameters_string = params_string

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

    @property
    def old_surface_numbers(self):
        """
        List of the surface numbers specified in the original input file.

        :rtype: list
        """
        return self.__old_surface_numbers

    @property
    def surface_logic_string(self):
        """
        The original surface input for the cell

        :rtype: str
        """
        return self.__surface_logic_string

    @property
    def parameters_string(self):
        """
        The string of the cell parameters: e.g. IMP:N = 1 if set.

        :rtype: str
        """
        if hasattr(self, "_Cell__parameters_string"):
            return self.__parameters_string

    def update_pointers(self, material_dict, surface_dict):
        """
        Attaches this object to the appropriate objects for surfaces and materials.

        :param material_dict: a dictionary mapping the material number to the Material object.
        :type material_dict: dict
        :param surface_dict: a dictionary mapping the surface number to the Surface object.
        :type surface_dict: dict
        """
        if self.__old_mat_number > 0:
            self.__material = material_dict[self.__old_mat_number]
        else:
            self.__material = None

        for surface_number in self.__old_surface_numbers:
            self.__surfaces.append(surface_dict[surface_number])

    def update_surface_logic_string(self):
        """
        Updates the surface logic string with new surface numbers.

        This is a bit of a hacky temporary solution while true boolean logic is implemented.
        """
        # make sure all numbers are surrounded by non-digit chars
        pad_string = " " + self.surface_logic_string + " "
        for surface in self.surfaces:
            old_num = surface.old_surface_number
            new_num = surface.surface_number
            pad_string = re.sub(
                f"(\D){old_num}(\D)",
                r"\g<1>{new_num}\g<2>".format(new_num=new_num),
                pad_string,
            )
        self.__surface_logic_string = pad_string

    def format_for_mcnp_input(self, mcnp_version):
        self.update_surface_logic_string()
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
        ret += Cell.wrap_string_for_mcnp(self.surface_logic_string, mcnp_version, False)
        if self.parameters_string:
            ret += Cell.wrap_string_for_mcnp(
                self.parameters_string, mcnp_version, False
            )
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

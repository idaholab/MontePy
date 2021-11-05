from .errors import *
from .mcnp_card import MCNP_Card
from .material import Material
import re
from .surface import Surface


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
        # cell number
        try:
            cell_num = int(words[0])
            self.__old_cell_number = cell_num
            self.__cell_number = cell_num
        except ValueError:
            raise MalformedInputError(
                input_card, f"{words[0]} can not be parsed as a cell number."
            )
        if words[1].lower() == "like":
            raise UnsupportedFeature(
                "Currently the LIKE option in cell cards is unsupported"
            )
        # material
        try:
            mat_num = int(words[1])
            self.__old_mat_number = mat_num

        except ValueError:
            raise MalformedInputError(
                input_card, f"{words[1]} can not be parsed as a material number."
            )
        # density
        if mat_num > 0:
            try:
                density = float(words[2])
                self.__density = abs(density)
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
        for i, word in enumerate(words[3:]):
            if non_surface_finder.search(word):
                param_found = True
                break
            else:
                surface_string += word + " "
                for surface in surface_finder.findall(word):
                    self.__old_surface_numbers.append(int(surface))
            self.__surface_logic_string = surface_string
        if param_found:
            params_string = " ".join([word] + words[3 + i : 0])
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
    def density(self, density, is_atom_dens):
        """
        :param density: the density of the material [a/b-cm] or [g/cc]
        :type density: float
        :param is_atom_dens: if True the density is atom density
        :type is_atom_dens: bool
        """
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
        if hasattr(self, "__parameters_string"):
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

    def format_for_mcnp_input(self):
        pass

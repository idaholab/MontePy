from .cell import Cell
from .data_card import DataCard
from .input_parser import read_input_syntax, BlockType, Card, Comment, Message, Title
from .material import Material
from .surfaces import Surface


class MCNP_Problem:
    """
    A class to represent an entire MCNP problem in a semantic way.
    """

    def __init__(self, file_name):
        """
        :param file_name: the path to the file that will be read.
        :type file_name: str
        """
        self.__input_file = file_name
        self.__original_inputs = []
        self.__cells = []
        self.__surfaces = []
        self.__data_cards = []
        self.__materials = []
        self.__mcnp_version = (6.2, 0)

    @property
    def original_inputs(self):
        """
        A list of the MCNP_Inputs read from the original file.

        This should not be mutated, and should be used a reference to maintain
        the structure

        :return: A list of the MCNP_Input objects representing the file as it was read
        :rtype: list
        """
        return self.__original_inputs

    @property
    def cells(self):
        """
        A list of the Cell objects in this problem.

        :return: a list of the Cell objects, ordered by the order they were in the input file.
        :rtype: list
        """
        return self.__cells

    def add_cells(self, cells):
        """
        Adds the given cells to the problem and all owned surfaces and materials as well.

        This will guarantee there are no naming collisions. If a collison is detected an exception is thrown.
        :param cells: The list of Cell objects to add to this problem.
        :type cells: list
        """
        pass

    @property
    def mcnp_version(self):
        """
        The version of MCNP that this is intended for.

        MCNP versions prior to 6.2 aren't officially supported to avoid
        Export Control Restrictions. Documentation for MCNP 6.2 is public in report:
            LA-UR-17-29981

        The version is a tuple of the major and minor revisions combined.
        6.2.0 would be represented as (6.2, 0)
        :rtype: tuple
        """
        return self.__mcnp_version

    @mcnp_version.setter
    def mcnp_version(self, version):
        """
        :param version: the version tuple. Must be greater than 6.2.0
        :type version: tuple
        """
        assert version >= (6.2, 0)
        self.__mcnp_version = version

    @property
    def surfaces(self):
        """
        A list of the Surface objects in this problem.

        :return: a list of the Surface objects, ordered by the order they were in the input file.
        :rtype: list
        """
        return self.__surfaces

    @property
    def materials(self):
        """
        A list of the Material objects in this problem.

        :return: a list of the Material objects, ordered by the order they were in the input file.
        :rtype: list
        """
        return self.__materials

    @property
    def data_cards(self):
        """
        A list of the DataCard objects in this problem.

        :return: a list of the DataCard objects, ordered by the order they were in the input file.
        :rtype: list
        """
        return self.__data_cards

    @property
    def input_file(self):
        """
        The file name of the original file name this problem was read from.

        :rtype: str
        """
        return self.__input_file

    @property
    def message(self):
        """
        The Message object at the beginning of the problem if any.

        :rtype: Message
        """
        if hasattr(self, "_MCNP_Problem__message"):
            return self.__message

    @property
    def title(self):
        """
        The Title object for the title.

        :rtype: Title
        """
        return self.__title

    def parse_input(self):
        """
        Semantically parses the MCNP file provided to the constructor.
        """
        comment_queue = None
        for i, input_card in enumerate(read_input_syntax(self.__input_file)):
            self.__original_inputs.append(input_card)
            if i == 0 and isinstance(input_card, Message):
                self.__message = input_card

            elif isinstance(input_card, Title) and not hasattr(
                self, "_MCNP_Problem__title"
            ):
                self.__title = input_card

            elif isinstance(input_card, Comment):
                comment_queue = input_card

            elif isinstance(input_card, Card):
                if input_card.block_type == BlockType.CELL:
                    cell = Cell(input_card, comment_queue)
                    self.__cells.append(cell)
                if input_card.block_type == BlockType.SURFACE:
                    surface = Surface(input_card, comment_queue)
                    self.__surfaces.append(surface)
                if input_card.block_type == BlockType.DATA:
                    data = DataCard.parse_data(input_card, comment_queue)
                    self.__data_cards.append(data)
                    if isinstance(data, Material):
                        self.__materials.append(data)
                comment_queue = None
        material_dict = {}
        surface_dict = {}
        for material in self.__materials:
            material_dict[material.material_number] = material
        for surface in self.__surfaces:
            surface_dict[surface.surface_number] = surface
        for cell in self.__cells:
            cell.update_pointers(material_dict, surface_dict)

    def write_to_file(self, new_problem):
        """
        Writes the problem to a file.

        :param new_problem: the file name to write this problem to
        :type new_problem: str
        """
        with open(new_problem, "w") as fh:
            if self.message:
                for line in self.message.format_for_mcnp_input(self.mcnp_version):
                    fh.write(line + "\n")
            lines = self.title.format_for_mcnp_input(self.mcnp_version)
            fh.write(lines[0] + "\n")
            for cell in self.cells:
                for line in cell.format_for_mcnp_input(self.mcnp_version):
                    fh.write(line + "\n")
            # block terminator
            fh.write("\n")
            for surface in self.surfaces:
                for line in surface.format_for_mcnp_input(self.mcnp_version):
                    fh.write(line + "\n")
            fh.write("\n")

            for card in self.data_cards:
                for line in card.format_for_mcnp_input(self.mcnp_version):
                    fh.write(line + "\n")

            fh.write("\n")

    def __str__(self):
        ret = f"MCNP problem for: {self.__input_file}\n"
        if self.message:
            ret += str(self.__message) + "\n"
        ret += str(self.__title) + "\n"
        for cell in self.__cells:
            ret += str(cell) + "\n"
        for data_card in self.__data_cards:
            if not isinstance(data_card, Material):
                ret += str(data_card) + "\n"
        return ret

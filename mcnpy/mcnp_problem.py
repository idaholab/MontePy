from .cell import Cell
from .data_card import DataCard
from .input_parser import read_input_syntax, BlockType, Card, Comment, Message, Title
from .material import Material
from .surface import Surface


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
        if hasattr(self, "__message"):
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

            elif isinstance(input_card, Title) and not hasattr(self, "__title"):
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

    def __str__(self):
        ret = f"MCNP problem for: {self.__input_file}\n"
        if self.__message:
            ret += str(self.__message) + "\n"
        ret += str(self.__title)
        for cell in self.__cells:
            ret += str(cell) + "\n"
        for data_card in self.__data_cards:
            if not isinstance(data_card, Material):
                ret += str(data_card) + "\n"
        return ret

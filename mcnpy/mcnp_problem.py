from .cell import Cell
from .data_card import DataCard
from .input_parser import read_input_syntax, Card, Comment, Message, Title
from .material import Material
from .surface import Surface

class MCNP_Problem:
    """
    A class to represent an entire MCNP problem in a semantic way.
    """

    def __init__(self, file_name):
        """

        """
        self.__input_file = file_name

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




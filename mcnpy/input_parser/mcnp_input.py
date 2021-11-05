from .block_type import BlockType 

class MCNP_Input:
    """
    Object to represent a single coherent MCNP input, such as a card.
    """
    pass

class Card(MCNP_Input):
    """
    Represents a single MCNP "card" e.g. a single cell definition.
    """

    def __init__(self, block_type, words):
        """
        :param block_type: An enum showing which of three MCNP blocks this was inside of.
        :type block_type: BlockType
        :param words: a list of the string representation of the words for the card definition
                        for example a material definition may contain: 'M10', '10001.70c', '0.1'
        :type words: list
        """
        assert isinstance(block_type, BlockType)
        self.__words = words
        self.__block_type = block_type

    def __str__(self):
        return f"CARD: {self.__block_type}: {self.__words}"

    @property
    def words(self):
        """
        A list of the string representation of the words for the card definition.
          
        For example a material definition may contain: 'M10', '10001.70c', '0.1'
        """
        return self.__words

    @property
    def block_type(self):
        """
        Enum representing which block of the MCNP input this came from
        """
        return self.__block_type

class Comment(MCNP_Input):
    """
    Object to represent a full line comment in an MCNP problem.
    """
    def __init__(self, lines):
        """
        :param lines: the strings of each line in this comment block
        :type lines: list
        """
        assert isinstance(lines, list)
        self.__lines = lines

    def __str__(self):
        ret = "COMMENT:\n"
        for line in self.__lines:
            ret = ret + line 
        return ret

    @property
    def lines(self):
        """
        The lines of input in this comment block.
       
        Each entry is a string of that line in the message block.
        The comment beginning "C " has been stripped out 
        """
        return self.__lines

class Message(MCNP_Input):
    """
    Object to represent an MCNP message.
    
    These are blocks at the beginning of an input that are printed in the output.
    """
    def __init__(self, lines):
        """
        :param lines: the strings of each line in the message block
        :type lines: list
        """
        assert isinstance(lines, list)
        self.__lines = lines

    def __str__(self):
        ret = "MESSAGE:\n"
        for line in self.__lines:
            ret = ret + line  
        return ret

    @property
    def lines(self):
        """
        The lines of input for the message block.
        
        Each entry is a string of that line in the message block
        """
        return self.__lines

class Title(MCNP_Input):
    """
    Object to represent the title for an MCNP problem
    """
    def __init__(self, title):
        self.__title = title

    @property
    def title(self):
        "The string of the title set for this problem"
        return self.__title

    def __str__(self):
        return f"title: {self.__title}"


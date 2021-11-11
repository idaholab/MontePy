from .surface_type import SurfaceType
from .surface import Surface


class CylinderParAxis(Surface):
    """
    Represents surfaces: C/X, C/Y, C/Z
    """

    def __init__(self, input_card, comment=None):

        COORDINATE_PAIRS = {
            SurfaceType.C_X: {0: "y", 1: "z"},
            SurfaceType.C_Y: {0: "x", 1: "z"},
            SurfaceType.C_Z: {0: "x", 1: "y"},
        }
        """
        :param input_card: The Card object representing the input
        :type input_card: Card
        :param comment: the Comment object representing the
                        preceding comment block.
        :type comment: Comment
        """
        super().__init__(input_card, comment)
        ST = surface_type.SurfaceType
        assert self.surface_type in [ST.C_X, ST.C_Y, ST,C_Z]
        assert len(self.constants) == 3
        self.__coordinates = self.constants[0:2]
        self.__radius = self.constant[2]


    @property
    def coordinates(self):
        """
        The two coordinates for this cylinder to center on.

        :rytpe: list
        """
        return self.__coordinates

    @coordinates.setter
    def coordinates(self, coordinates):
        """
        :param coordinates: the coordinates, must be 2 long.
        """
        assert len(coordinates) == 2
        self.__coordinates = coordinates
        self.__constants[0:2] = coordinates

    @property
    def radius(self):
        """
        The radius of the cylinder.

        :rtype: float
        """
        return self.__radius
        
    @radius.setter
    def radius(self, radius):
        assert isinstance(radius, float)
        assert radius > 0
        self.__radius = radius
        self.__constants[2] = radius


from .surface_type import SurfaceType
from .surface import Surface


class CylinderOnAxis(Surface):
    """
    Represents surfaces: CX, CY, CZ
    """

    def __init__(self, input_card, comment=None):
        """
        :param input_card: The Card object representing the input
        :type input_card: Card
        :param comment: the Comment object representing the
                        preceding comment block.
        :type comment: Comment
        """
        super().__init__(input_card, comment)
        ST = SurfaceType
        assert self.surface_type in [ST.CX, ST.CY, ST.CZ]
        assert len(self.surface_constants) == 1
        self.__radius = self.surface_constants[0]

    @property
    def radius(self):
        """
        The radius of the cylinder
        """
        return self.__radius

    @radius.setter
    def radius(self, radius):
        assert isinstance(radius, float)
        self.__radius = radius

from mcnpy.numbered_object_collection import NumberedObjectCollection
from mcnpy.universe import Universe


class Universes(NumberedObjectCollection):
    """
    A container of multiple :class:`mcnpy.data_cards.material.Material` instances.
    """

    def __init__(self, objects=None):
        super().__init__(Universe, objects)

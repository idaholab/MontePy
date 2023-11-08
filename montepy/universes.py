from mcnpy.numbered_object_collection import NumberedObjectCollection
from mcnpy.universe import Universe


class Universes(NumberedObjectCollection):
    """
    A container of multiple :class:`~mcnpy.universe.Universe` instances.
    """

    def __init__(self, objects=None, problem=None):
        super().__init__(Universe, objects, problem)

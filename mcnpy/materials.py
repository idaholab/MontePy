import mcnpy
from mcnpy.numbered_object_collection import NumberedObjectCollection

Material = mcnpy.data_cards.material.Material

class Materials(NumberedObjectCollection):
    """
    A container of multiple :class:`mcnpy.data_cards.material.Material` instances.
    """
    def __init__(self, objects=None):
        super().__init__(Material, objects)

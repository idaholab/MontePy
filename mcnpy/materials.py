import mcnpy
from mcnpy.numbered_object_collection import NumberedObjectCollection

Material = mcnpy.data_cards.material.Material


class Materials(NumberedObjectCollection):
    def __init__(self, objects=None):
        super().__init__(Material, objects)

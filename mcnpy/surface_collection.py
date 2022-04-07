from mcnpy.surfaces.surface import Surface
from mcnpy.numbered_object_collection import NumberedObjectCollection


class Surfaces(NumberedObjectCollection):
    def __init__(self, surfaces=None):
        super().__init__(Surface, surfaces)

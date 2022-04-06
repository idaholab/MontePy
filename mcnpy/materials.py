import mcnpy
from mcnpy.numbered_object_collection import NumberedObjectCollection

Material = mcnpy.data_cards.material.Material


class Materials(NumberedObjectCollection):
    def __init__(self, objects=None):
        super().__init__(Material, objects)

    def append(self, material):
        assert isinstance(material, Material)
        self._objects.append(material)

    def __iadd__(self, other):
        assert type(other) in [Materials, list]
        for mat in other:
            assert isinstance(mat, Material)
        if isinstance(other, Materials):
            self._objects += other._objects
        else:
            self._objects += other
        return self

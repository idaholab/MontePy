import mcnpy
from mcnpy.collections import Collection

Material = mcnpy.data_cards.material.Material


class Materials(Collection):
    def __init__(self, objects=None):
        super().__init__(Material, objects)

    @property
    def numbers(self):
        for mat in self._objects:
            yield mat.material_number

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

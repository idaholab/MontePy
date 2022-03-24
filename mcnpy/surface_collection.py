from mcnpy.collections import Collection
from mcnpy.surfaces.surface import Surface


class Surfaces(Collection):
    def __init__(self, surfaces=None):
        super().__init__(Surface, surfaces)

    def append(self, surface):
        assert isinstance(surface, Surface)
        self._objects.append(surface)

    def __iadd__(self, other):
        assert type(other) in [Surfaces, list]
        for surface in other:
            assert isinstance(surface, Surface)
        if isinstance(other, Surfaces):
            self._objects += other._objects
        else:
            self._objects += other
        return self

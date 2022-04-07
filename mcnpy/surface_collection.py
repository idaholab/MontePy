from mcnpy.surfaces.surface import Surface
from mcnpy.surfaces.surface_type import SurfaceType
from mcnpy.numbered_object_collection import NumberedObjectCollection


class SurfacesGenerator:
    def __set_name__(self, owner, name):
        self._surfs = owner
        self.surf_type = name

    def __get__(self, obj, objtype=None):
        for surf in obj.objects:
            if surf.surface_type.name.lower() == self.surf_type:
                yield surf


class Surfaces(NumberedObjectCollection):
    pz = SurfacesGenerator()

    def __init__(self, surfaces=None):
        super().__init__(Surface, surfaces)


for surf_type in SurfaceType:
    generator = SurfacesGenerator()
    generator.__set_name__(Surfaces, surf_type.name.lower())
    setattr(Surfaces, surf_type.name.lower(), generator)

from mcnpy.surfaces.surface import Surface
from mcnpy.surfaces.surface_type import SurfaceType
from mcnpy.numbered_object_collection import NumberedObjectCollection


class SurfacesGenerator:
    """A class for a Descriptor for the Surfaces collection.

    This is meant to make it possible to get a generator at
    surfaces.pz
    """

    def __set_name__(self, owner, name):
        self._surfs = owner
        self.surf_type = name

    def __get__(self, obj, objtype=None):
        for surf in obj.objects:
            if surf.surface_type.name.lower() == self.surf_type:
                yield surf


class Surfaces(NumberedObjectCollection):
    """A collection of multiple :class:`mcnpy.surfaces.surface.Surface` instances.

    This collection has a generator for every supported type of MCNP surface.
    These are accessed by the for lower case version of the MCNP mnemonic.
    For example you can access all planes normal to the z-axis through .pz

    This example will shift all PZ surfaces up by 10 cm.

    >>> for surface in problem.surfaces.pz:
    >>>    surface.location += 10

    """
    pz = SurfacesGenerator()

    def __init__(self, surfaces=None):
        super().__init__(Surface, surfaces)


for surf_type in SurfaceType:
    generator = SurfacesGenerator()
    generator.__set_name__(Surfaces, surf_type.name.lower())
    setattr(Surfaces, surf_type.name.lower(), generator)

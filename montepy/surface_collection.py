# Copyright 2024, Battelle Energy Alliance, LLC All Rights Reserved.
from montepy.surfaces.surface import Surface
from montepy.surfaces.surface_type import SurfaceType
from montepy.numbered_object_collection import NumberedObjectCollection


def __create_surface_generator(surf_type):
    """A function for a Descriptor for the Surfaces collection.

    This is meant to make it possible to get a generator at
    surfaces.pz

    This works by creating a closure that is a generator.
    This closure is then passed to ``property()`` to create a property
    """

    def closure(obj):
        for surf in obj.objects:
            if surf.surface_type == surf_type:
                yield surf

    return closure


class Surfaces(NumberedObjectCollection):
    """A collection of multiple :class:`montepy.surfaces.surface.Surface` instances.

    This collection has a generator for every supported type of MCNP surface.
    These are accessed by the for lower case version of the MCNP mnemonic.
    For example you can access all planes normal to the z-axis through .pz

    This example will shift all PZ surfaces up by 10 cm.

    .. code-block:: python

        for surface in problem.surfaces.pz:
            surface.location += 10

    :param surfaces: the list of surfaces to start with if needed
    :type surfaces: list
    """

    def __init__(self, surfaces=None, problem=None):
        super().__init__(Surface, surfaces, problem)


def __setup_surfaces_generators():
    for surf_type in SurfaceType:
        doc = f"Generator for getting all surfaces of type *{surf_type.description}* or ``{surf_type.value}``"
        getter = property(__create_surface_generator(surf_type), doc=doc)
        setattr(Surfaces, surf_type.name.lower(), getter)


__setup_surfaces_generators()

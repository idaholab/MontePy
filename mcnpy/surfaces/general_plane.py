from mcnpy.surfaces.surface_type import SurfaceType
from mcnpy.surfaces.surface import Surface


class GeneralPlane(Surface):
    """
    Represents P
    """

    def __init__(self, input_card, comment=None):
        super().__init__(input_card, comment)
        assert self.surface_type == SurfaceType.P
        assert len(self.surface_constants) in {4, 9}

    def find_duplicate_surfaces(self, surfaces, tolerance):
        ret = []
        if not self.old_periodic_surface:
            for surface in surfaces:
                if surface != self and surface.surface_type == self.surface_type:
                    if not self.old_periodic_surface:
                        match = True
                        for i, constant in enumerate(self.surface_constants):
                            if (
                                abs(constant - surface.surface_constants[i])
                                >= tolerance
                            ):
                                match = False
                        # Try the anti-vector
                        if not match:
                            match = True
                            for i, constant in enumerate(self.surface_constants):
                                if (
                                    abs(-constant - surface.surface_constants[i])
                                    >= tolerance
                                ):
                                    match = False
                        if match and self.transform:
                            match = False
                            if surface.transform:
                                if self.transform.equivalent(
                                    surface.transform, tolerance
                                ):
                                    match = True
                        if match:
                            ret.append(surface)
        return ret

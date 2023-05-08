from mcnpy.surfaces.axis_plane import AxisPlane
from mcnpy.surfaces.surface import Surface
from mcnpy.surfaces.surface_type import SurfaceType
from mcnpy.surfaces.cylinder_on_axis import CylinderOnAxis
from mcnpy.surfaces.cylinder_par_axis import CylinderParAxis
from mcnpy.surfaces.general_plane import GeneralPlane


def surface_builder(input):
    """
    Builds a Surface object for the type of Surface

    :param input: The Input object representing the input
    :type input: Input
    :returns: A Surface object properly parsed. If supported a sub-class of Surface will be given.
    :rtype: Surface
    """
    ST = SurfaceType
    buffer_surface = Surface(input)
    type_of_surface = buffer_surface.surface_type
    if type_of_surface in [ST.C_X, ST.C_Y, ST.C_Z]:
        return CylinderParAxis(input)
    elif type_of_surface in [ST.CX, ST.CY, ST.CZ]:
        return CylinderOnAxis(input)
    elif type_of_surface in [ST.PX, ST.PY, ST.PZ]:
        return AxisPlane(input)
    elif type_of_surface == ST.P:
        return GeneralPlane(input)
    else:
        return buffer_surface

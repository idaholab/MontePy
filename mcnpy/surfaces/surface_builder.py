from mcnpy.surfaces.axis_plane import AxisPlane
from mcnpy.surfaces.surface import Surface
from mcnpy.surfaces.surface_type import SurfaceType
from mcnpy.surfaces.cylinder_on_axis import CylinderOnAxis
from mcnpy.surfaces.cylinder_par_axis import CylinderParAxis


def surface_builder(input_card, comment = None):
    """
    Builds a Surface object for the type of Surface

    :param input_card: The Card object representing the input
    :type input_card: Card
    :param comment: the Comment object representing the
                    preceding comment block.
    :type comment: Comment
    :returns: A Surface object properly parsed. If supported a sub-class of Surface will be given.
    :rtype: Surface
    """
    ST = SurfaceType
    buffer_surface = Surface(input_card, comment)
    type_of_surface = buffer_surface.surface_type
    if type_of_surface in [ST.C_X, ST.C_Y, ST.C_Z]:
        return CylinderParAxis(input_card, comment)
    elif type_of_surface in [ST.CX, ST.CY, ST.CZ]:
        return CylinderOnAxis(input_card, comment)
    elif type_of_surface in [ST.PX, ST.PY, ST.PZ]:
        return AxisPlane(input_card, comment)
    else:
        return buffer_surface

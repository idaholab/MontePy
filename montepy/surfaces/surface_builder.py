from montepy.surfaces.axis_plane import AxisPlane
from montepy.surfaces.surface import Surface
from montepy.surfaces.surface_type import SurfaceType
from montepy.surfaces.cylinder_on_axis import CylinderOnAxis
from montepy.surfaces.cylinder_par_axis import CylinderParAxis
from montepy.surfaces.general_plane import GeneralPlane


def surface_builder(input_card, comments=None):
    """
    Builds a Surface object for the type of Surface

    :param input_card: The Card object representing the input
    :type input_card: Card
    :param comments: the Comment object representing the
                    preceding comments block.
    :type comments: Comment
    :returns: A Surface object properly parsed. If supported a sub-class of Surface will be given.
    :rtype: Surface
    """
    ST = SurfaceType
    buffer_surface = Surface(input_card, comments)
    type_of_surface = buffer_surface.surface_type
    if type_of_surface in [ST.C_X, ST.C_Y, ST.C_Z]:
        return CylinderParAxis(input_card, comments)
    elif type_of_surface in [ST.CX, ST.CY, ST.CZ]:
        return CylinderOnAxis(input_card, comments)
    elif type_of_surface in [ST.PX, ST.PY, ST.PZ]:
        return AxisPlane(input_card, comments)
    elif type_of_surface == ST.P:
        return GeneralPlane(input_card, comments)
    else:
        return buffer_surface

from mcnpy.data_inputs import (
    data_input,
    importance,
    material,
    mode,
    thermal_scattering,
    volume,
)
from mcnpy.data_inputs import transform
import re

PREFIX_MATCHES = {
    "imp": importance.Importance,
    "m": material.Material,
    "mode": mode.Mode,
    "mt": thermal_scattering.ThermalScatteringLaw,
    "tr": transform.Transform,
    "vol": volume.Volume,
}


def parse_data(input, comment=None):
    """
    Parses the data input as the appropriate object if it is supported.

    :param input: the Input object for this Data input
    :type input: Input
    :param comment: the Comment that may proceed this.
    :type comment: Comment
    :return: the parsed DataInput object
    :rtype: DataInput
    """

    base_input = data_input.DataInput(input, comment)
    prefix = base_input.prefix

    for match, data_class in PREFIX_MATCHES.items():
        if prefix == match:
            return data_class(input, comment)
    return base_input

# Copyright 2024, Battelle Energy Alliance, LLC All Rights Reserved.
from montepy.data_cards import (
    data_card,
    fill,
    importance,
    lattice_card,
    material,
    mode,
    thermal_scattering,
    universe_card,
    volume,
)
from montepy.data_cards import transform
import re

PREFIX_MATCHES = {
    "fill": fill.Fill,
    "imp": importance.Importance,
    "lat": lattice_card.LatticeCard,
    "m": material.Material,
    "mode": mode.Mode,
    "mt": thermal_scattering.ThermalScatteringLaw,
    "tr": transform.Transform,
    "vol": volume.Volume,
    "u": universe_card.UniverseCard,
}


def parse_data(input_card, comment=None):
    """
    Parses the data card as the appropriate object if it is supported.

    :param input_card: the Card object for this Data card
    :type input_card: Card
    :param comment: the Comment that may proceed this.
    :type comment: Comment
    :return: the parsed DataCard object
    :rtype: DataCard
    """

    base_card = data_card.DataCard(input_card, comment)
    prefix = base_card.prefix

    for match, data_class in PREFIX_MATCHES.items():
        if prefix == match:
            return data_class(input_card, comment)
    return base_card

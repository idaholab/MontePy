from mcnpy.data_cards import data_card, material, thermal_scattering
from mcnpy.data_cards import transform
import re

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
    identifier = input_card.words[0].lower()

    # material finder
    if re.match("m\d+",identifier):
        return material.Material(input_card, comment)
    if re.match("mt\d+", identifier):
        return thermal_scattering.ThermalScatteringLaw(
            input_card=input_card, comment=comment
        )
    if re.match("\*?tr\d+", identifier):
        return transform.Transform(input_card, comment) 
    else:
        return data_card.DataCard(input_card, comment)


def __str__(self):
    return f"DATA CARD: {self.__words}"

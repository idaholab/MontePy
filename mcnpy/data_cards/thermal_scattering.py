from mcnpy.data_cards.data_card import DataCard
from mcnpy import mcnp_card
from mcnpy.errors import *


class ThermalScatteringLaw(DataCard):
    """
    Class to hold MT cards
    """

    def __init__(self, input_card="", comment=None, material=None):
        """
        This is designed to be called two ways.

        The first is with a read input file using input_card, comment
        The second is after a read with a material and a comment (using named inputs)
        :param input_card: the Card object representing this data card
        :type input_card: Card
        :param comment: The Comment that may proceed this
        :type comment: Comment
        :param material: the parent Material object that owns this
        :type material: Material
        """
        if input_card:
            super().__init__(input_card, comment)
            assert "mt" in self.words[0].lower()
            words = self.words
            try:
                num = int(words[0].lower().strip("mt"))
                assert num > 0
                self._old_material_number = num
            except (ValueError, AssertionError) as e:
                raise MalformedInputError(
                    input_card, f"{words[0]} could not be parsed as a material number"
                )
            self._scattering_laws = self.words[1:]
        elif comment:
            self._comment = comment
        elif material:
            self._parent_material = material

    @property
    def old_material_number(self):
        """
        The material number from the file
        """
        return self._old_material_number

    @property
    def parent_material(self):
        """
        The Material object this is tied to.
        :rtype: Material
        """
        return self._parent_material

    @property
    def thermal_scattering_laws(self):
        """
        The thermal scattering laws to use for this material
        :rtype: list
        """
        return self._scattering_laws

    @thermal_scattering_laws.setter
    def thermal_scattering_laws(self, laws):
        assert isinstance(laws, list)
        for law in laws:
            assert isinstance(law, str)
        self._scattering_laws = laws

    def add_scattering_law(self, law):
        """
        Adds the requested scattering law to this material
        """
        self._scattering_laws.append(law)

    def format_for_mcnp_input(self, mcnp_version):
        ret = mcnp_card.MCNP_Card.format_for_mcnp_input(self, mcnp_version)
        buff_list = [f"MT{self.parent_material.material_number}"]
        buff_list += self._scattering_laws
        ret += ThermalScatteringLaw.wrap_words_for_mcnp(buff_list, mcnp_version, True)
        return ret

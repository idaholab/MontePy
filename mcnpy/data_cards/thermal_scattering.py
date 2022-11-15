from mcnpy.data_cards.data_card import DataCardAbstract
from mcnpy import mcnp_card
from mcnpy.errors import *
import mcnpy


class ThermalScatteringLaw(DataCardAbstract):
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
        self._old_material_number = None
        self._parent_material = None
        self._scattering_laws = []
        if input_card:
            super().__init__(input_card, comment)
            words = self.words
            self._old_material_number = self._input_number
            self._scattering_laws = self.words[1:]
        else:
            if comment:
                self._comment = comment
            if material:
                self._parent_material = material

    @property
    def class_prefix(self):
        return "mt"

    @property
    def has_number(self):
        return True

    @property
    def has_classifier(self):
        return 0

    @property
    def old_number(self):
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
        if not isinstance(laws, list):
            raise TypeError("thermal_scattering_laws must be a list")
        for law in laws:
            if not isinstance(law, str):
                raise TypeError(
                    f"element {law} in thermal_scattering_laws must be a string"
                )
        self._mutated = True
        self._scattering_laws = laws

    def add_scattering_law(self, law):
        """
        Adds the requested scattering law to this material
        """
        self._scattering_laws.append(law)

    def format_for_mcnp_input(self, mcnp_version):
        ret = mcnp_card.MCNP_Card.format_for_mcnp_input(self, mcnp_version)
        mutated = self.mutated
        if not self.parent_material:
            raise MalformedInputError(
                self, "MT input is detached from a parent material"
            )
        if not mutated:
            mutated = self.parent_material.mutated
        if mutated:
            buff_list = [f"MT{self.parent_material.number}"]
            buff_list += self._scattering_laws
            ret += ThermalScatteringLaw.wrap_words_for_mcnp(
                buff_list, mcnp_version, True
            )
        else:
            ret = self._format_for_mcnp_unmutated(mcnp_version)
        return ret

    def update_pointers(self, data_cards):
        """
        Updates pointer to the thermal scattering data

        :param data_cards: a list of the data cards in the problem
        :type data_cards: list
        """
        found = False
        for card in data_cards:
            if isinstance(card, mcnpy.data_cards.material.Material):
                if card.number == self.old_number:
                    found = True

        if not found:
            raise MalformedInputError(
                self, "MT input is detached from a parent material"
            )

    def __str__(self):
        return f"THERMAL SCATTER: {self.thermal_scattering_laws}"

    def __repr__(self):
        return f"THERMAL SCATTER: material: {self.parent_material}, old_num: {self.old_number}, scatter: {self.thermal_scattering_laws}"

from mcnpy.data_cards.cell_modifier import CellModifierCard
from mcnpy.errors import *
from mcnpy.particle import Particle
import numbers


class Importance(CellModifierCard):
    """
    A data input that sets the importance for a cell(s).
    """

    def __init__(
        self, input_card=None, comments=None, in_cell_block=False, key=None, value=None
    ):
        """
        :param input_card: the Card object representing this data card
        :type input_card: Card
        :param comment: The Comment that may proceed this
        :type comment: Comment
        :param in_cell_block: if this card came from the cell block of an input file.
        :type in_cell_block: bool
        :param key: the key from the key-value pair in a cell
        :type key: str
        :param key: the value from the key-value pair in a cell
        :type key: str
        """
        super().__init__(input_card, comments, in_cell_block, key, value)
        self._particle_importances = {}
        if self.in_cell_block:
            if key:
                try:
                    value = float(value)
                    assert value >= 0
                except (ValueError, AssertionError) as e:
                    raise ValueError(
                        f"Cell importance must be a number >= 0. {value} was given"
                    )
                for particle in self.particle_classifiers:
                    self._particle_importances[particle] = value
        elif input_card:
            values = []
            for word in self.words[1:]:
                try:
                    value = float(word)
                    values.append(value)
                    assert value >= 0
                except (ValueError, AssertionError) as e:
                    raise MalformedInputError(
                        input_card, f"Importances must be ≥ 0 value: {word} given"
                    )
            for particle in self.particle_classifiers:
                self._particle_importances[particle] = values

    @property
    def class_prefix(self):
        return "imp"

    @property
    def has_number(self):
        return False

    @property
    def has_classifier(self):
        return 2

    def merge(self, other):
        pass

    def push_to_cells(self):
        if self._problem:
            for particle in self._particle_importances:
                for i, cell in enumerate(self._problem.cells):
                    value = self._particle_importances[particle][i]
                    cell.importance._particle_importances[particle] = value

    @property
    def all(self):
        """
        Setter for setting importance for all particle types in problem at once.
        """
        return None

    @all.setter
    def all(self, value):
        if not isinstance(value, float):
            raise TypeError("All importance must be a float")
        if value < 0.0:
            raise ValueError("Importance must be ≥ 0.0")
        if self._problem:
            for particle in self._problem.mode:
                self._particle_importances[particle] = value

    def _clear_data(self):
        if not self.in_cell_block:
            self._particle_importances = {}

    def _check_particle_in_problem(self, particle_type):
        if self._problem:
            if particle_type not in self._problems.mode:
                raise ParticleTypeNotInProblem(
                    f"Particle type: {particle_type} not included in problem mode."
                )


def __create_importance_getter(particle_type):
    def closure(obj, objtype=None):
        obj._check_particle_in_problem(particle_type)
        try:
            return obj._particle_importances[particle_type]
        except KeyError:
            return 0.0

    return closure


# TODO handle multi-cell cases
def __create_importance_setter(particle_type):
    def closure(obj, value):
        obj._check_particle_in_problem(particle_type)
        if not isinstance(value, numbers.Number):
            raise TypeError("importance must be a number")
        if value < 0:
            raise ValueError("importance must be ≥ 0")
        obj._particle_importances[particle_type] = value

    return closure


def __create_importance_deleter(particle_type):
    def closure(obj):
        del obj._particle_importances[particle_type]

    return closure


def __create_particle_imp_doc(particle_type):
    return f"Importance for particles of type *{particle_type.name.lower()}*"


for particle in Particle:
    getter = __create_importance_getter(particle)
    setter = __create_importance_setter(particle)
    deleter = __create_importance_deleter(particle)
    doc = __create_particle_imp_doc(particle)
    prop = property(getter, setter, deleter, doc=doc)
    setattr(Importance, particle.name.lower(), prop)

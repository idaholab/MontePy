from mcnpy.data_cards.cell_modifier import CellModifierCard
from mcnpy.particle import Particle
import numbers


class Importance(CellModifierCard):
    """
    A data input that sets the importance for a cell(s).
    """

    def __init__(
        self, input_card=None, comments=None, in_cell_block=True, key=None, value=None
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
        self._remove_excess_methods()
        if self.in_cell_block:
            self._particle_importances = {}
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

    @property
    def class_prefix(self):
        return "imp"

    @property
    def has_number(self):
        return False

    @property
    def has_classifier(self):
        return 2

    def merge_importance(self, other):
        pass

    @property
    def all(self):
        pass

    def _define_problem_level_method_map(self):
        return set()

    def _define_cell_level_method_map(self):
        return set()


def __create_importance_getter(particle_type):
    def closure(obj, objtype=None):
        return obj._particle_importances[particle_type]

    return closure


# TODO handle multi-cell cases
def __create_importance_setter(particle_type):
    def closure(obj, value):
        if not isinstance(value, numbers.Number):
            raise TypeError("importance must be a number")
        if value < 0 or value > 1:
            raise ValueError("importance must be in [0,1]")
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

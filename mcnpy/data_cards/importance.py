from mcnpy.data_cards.cell_modifier import CellModifierCard
from mcnpy.errors import *
from mcnpy.input_parser.constants import DEFAULT_VERSION
from mcnpy.mcnp_card import MCNP_Card
from mcnpy.particle import Particle
from mcnpy.utilities import *
import numbers


class Importance(CellModifierCard):
    """
    A data input that sets the importance for a cell(s).

    :param input_card: the Card object representing this data card
    :type input_card: Card
    :param comments: The list of Comments that may proceed this or be entwined with it.
    :type comments: list
    :param in_cell_block: if this card came from the cell block of an input file.
    :type in_cell_block: bool
    :param key: the key from the key-value pair in a cell
    :type key: str
    :param value: the value from the key-value pair in a cell
    :type value: str
    """

    def __init__(
        self, input_card=None, comments=None, in_cell_block=False, key=None, value=None
    ):
        super().__init__(input_card, comments, in_cell_block, key, value)
        self._particle_importances = {}
        if self.in_cell_block:
            if key:
                try:
                    value = fortran_float(value)
                    assert value >= 0
                except (ValueError, AssertionError) as e:
                    raise ValueError(
                        f"Cell importance must be a number ≥ 0. {value} was given"
                    )
                for particle in self.particle_classifiers:
                    self._particle_importances[particle] = value
        elif input_card:
            values = []
            for word in self.words[1:]:
                try:
                    value = fortran_float(word)
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

    @property
    def has_information(self):
        if self.in_cell_block:
            return True

    def merge(self, other):
        if not isinstance(other, type(self)):
            raise TypeError("Can only be merged with other Importance object")
        if self.in_cell_block != other.in_cell_block:
            raise ValueError("Can not mix cell-level and data-level Importance objects")
        self._input_lines.extend(other._input_lines)
        if other.set_in_cell_block:
            self._set_in_cell_block = True
        for particle in other:
            if particle not in self:
                self._particle_importances[particle] = other[particle]
            else:
                raise MalformedInputError(
                    other, "Cannot have two importance cards for the same particle type"
                )

    def __iter__(self):
        return iter(self._particle_importances.keys())

    def __contains__(self, value):
        return value in self._particle_importances

    def __getitem__(self, particle):
        if not isinstance(particle, Particle):
            raise TypeError("Key must be a particle")
        self._check_particle_in_problem(particle)
        return self._particle_importances[particle]

    def __setitem__(self, particle, value):
        if not isinstance(particle, Particle):
            raise TypeError("Key must be a particle")
        self._check_particle_in_problem(particle)
        if not isinstance(value, numbers.Number):
            raise TypeError("importance must be a number")
        if value < 0:
            raise ValueError("importance must be ≥ 0")
        self._mutated = True
        self._particle_importances[particle] = value

    def __delitem__(self, particle):
        if not isinstance(particle, Particle):
            raise TypeError("Key must be a particle")
        del self._particle_importances[particle]

    def __str__(self):
        if not self.in_cell_block and self._problem is None:
            return " ".join(self.input_lines)
        return "".join(self.format_for_mcnp_input(DEFAULT_VERSION))

    def __repr__(self):
        return (
            f"Importance: in_cell_block: {self.in_cell_block},"
            f" set_in_cell_block {self.set_in_cell_block},"
            f"\n{self._particle_importances}"
        )

    def push_to_cells(self):
        if self._problem and not self.in_cell_block:
            self._check_redundant_definitions()
            for particle in self._particle_importances:
                for i, cell in enumerate(self._problem.cells):
                    value = self._particle_importances[particle][i]
                    cell.importance[particle] = value
                    cell.importance._mutated = False

    @property
    def all(self):
        """
        Setter for setting importance for all particle types in the problem at once.

        :param importance: the importance to set all particles to.
        :type importance: float
        :returns: None
        :rtype: None
        """
        return None

    @all.setter
    def all(self, value):
        if not isinstance(value, numbers.Number):
            raise TypeError("All importance must be a float")
        value = float(value)
        if value < 0.0:
            raise ValueError("Importance must be ≥ 0.0")
        if self._problem:
            self._mutated = True
            for particle in self._problem.mode:
                self._particle_importances[particle] = value

    def _clear_data(self):
        if not self.in_cell_block:
            self._particle_importances = {}

    def _check_particle_in_problem(self, particle_type):
        if self._problem:
            if particle_type not in self._problem.mode:
                raise ParticleTypeNotInProblem(
                    f"Particle type: {particle_type} not included in problem mode."
                )

    def _combine_importances(self):
        ret = {}
        inverse = {}
        mod_threshold = 1e6
        for particle, value in self._particle_importances.items():
            round_val = int(value * mod_threshold)
            if round_val in inverse:
                inverse[round_val].append(particle)
            else:
                inverse[round_val] = [particle]
        for value, particles in inverse.items():
            part_tuple = tuple(sorted(particles))
            ret[part_tuple] = value / mod_threshold
        return ret

    def _format_data_input_particle(self, particle):
        values = []
        for cell in self._problem.cells:
            values.append(cell.importance[particle])
        return self.compress_repeat_values(values)

    def format_for_mcnp_input(self, mcnp_version):
        ret = []
        if self.in_cell_block:
            if self._particle_importances:
                combined_values = self._combine_importances()
                for particles, value in combined_values.items():
                    particles_short = ",".join([part.value for part in particles])
                    ret.extend(
                        self.wrap_string_for_mcnp(
                            f"IMP:{particles_short}={value}", mcnp_version, False
                        )
                    )
        else:
            mutated = self.mutated
            if not mutated:
                mutated = self.has_changed_print_style
                for cell in self._problem.cells:
                    if cell.importance.mutated:
                        mutated = True
                        break
            if mutated and self._problem.print_in_data_block["IMP"]:
                has_info = False
                for cell in self._problem.cells:
                    if cell._importance.has_information:
                        has_info = True
                        break
                if has_info:
                    ret = MCNP_Card.format_for_mcnp_input(self, mcnp_version)
                    part_value = {}
                    for particle in sorted(self._problem.mode):
                        value = tuple(self._format_data_input_particle(particle))
                        if value in part_value:
                            part_value[value].append(particle)
                        else:
                            part_value[value] = [particle]
                    for value, particles in part_value.items():
                        particles_short = ",".join(
                            [part.value for part in sorted(particles)]
                        )
                        ret.extend(
                            self.wrap_words_for_mcnp(
                                [f"IMP:{particles_short}"] + list(value),
                                mcnp_version,
                                True,
                            )
                        )
            # if not mutated
            elif self._problem.print_in_data_block["IMP"]:
                ret = self._format_for_mcnp_unmutated(mcnp_version)
        return ret


def __create_importance_getter(particle_type):
    def closure(obj):
        obj._check_particle_in_problem(particle_type)
        try:
            return obj._particle_importances[particle_type]
        except KeyError:
            return 0.0

    return closure


def __create_importance_setter(particle_type):
    def closure(obj, value):
        obj._check_particle_in_problem(particle_type)
        if not isinstance(value, numbers.Number):
            raise TypeError("importance must be a number")
        value = float(value)
        if value < 0:
            raise ValueError("importance must be ≥ 0")
        obj._mutated = True
        obj._particle_importances[particle_type] = value

    return closure


def __create_importance_deleter(particle_type):
    def closure(obj):
        obj._mutated = True
        del obj._particle_importances[particle_type]

    return closure


def __create_particle_imp_doc(particle_type):
    return f"""Importance for particles of type *{particle_type.name.lower()}*

Can only be set if this particle is used in the problem mode.

:param importance: The importance to set this to.
:type importnace: float
:returns: the importance for the particle type. If not set, defaults to 0.
:rtype: float
:raises ParticleTypeNotInProblem: raised if this particle is accessed while not in the problem mode.
"""


def __setup_importances():
    for particle in Particle:
        getter = __create_importance_getter(particle)
        setter = __create_importance_setter(particle)
        deleter = __create_importance_deleter(particle)
        doc = __create_particle_imp_doc(particle)
        prop = property(getter, setter, deleter, doc=doc)
        setattr(Importance, particle.name.lower(), prop)


__setup_importances()

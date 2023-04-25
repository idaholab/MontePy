import copy
import math
from mcnpy.data_inputs.cell_modifier import CellModifierInput
from mcnpy.errors import *
from mcnpy.constants import DEFAULT_VERSION, rel_tol, abs_tol
from mcnpy.input_parser import syntax_node
from mcnpy.mcnp_object import MCNP_Object
from mcnpy.particle import Particle
from mcnpy.utilities import *
import numbers


class Importance(CellModifierInput):
    """
    A data input that sets the importance for a cell(s).

    :param input: the input object representing this data input
    :type input: Input
    :param comments: The list of Comments that may proceed this or be entwined with it.
    :type comments: list
    :param in_cell_block: if this Input came from the cell block of an input file.
    :type in_cell_block: bool
    :param key: the key from the key-value pair in a cell
    :type key: str
    :param value: the value from the key-value pair in a cell
    :type value: str
    """

    def __init__(
        self, input=None, comments=None, in_cell_block=False, key=None, value=None
    ):
        self._particle_importances = {}
        super().__init__(input, comments, in_cell_block, key, value)
        if self.in_cell_block:
            if key:
                val = value["data"]
                if isinstance(val, syntax_node.ListNode):
                    val = value["data"][0]
                if val.type != float or val.value < 0:
                    raise ValueError(
                        f"Cell importance must be a number ≥ 0. {val.value} was given"
                    )
                for particle in self.particle_classifiers:
                    self._particle_importances[particle] = value
        elif input:
            values = []
            for node in self._tree["data"]:
                try:
                    value = node.value
                    assert value >= 0
                    values.append(node)
                except (AttributeError, AssertionError) as e:
                    raise MalformedInputError(
                        input, f"Importances must be ≥ 0 value: {node} given"
                    )
            for particle in self.particle_classifiers:
                self._particle_importances[particle] = copy.deepcopy(self._tree)

    def _generate_default_cell_tree(self, particle=None):
        classifier = syntax_node.ClassifierNode()
        classifier.prefix = self._generate_default_node(
            str, self._class_prefix().upper(), None
        )
        if particle is None:
            particles = syntax_node.ParticleNode("imp particle", "n")
            particle = Particle.NEUTRON
        else:
            particles = syntax_node.ParticleNode("imp particle", particle.value.lower())
        if self._problem:
            particles.particles = self._problem.mode.particles
        classifier.particles = particles
        list_node = syntax_node.ListNode("imp data")
        list_node.append(self._generate_default_node(float, 0.0))
        tree = syntax_node.SyntaxNode(
            "Importance",
            {
                "classifier": classifier,
                "seperator": self._generate_default_node(str, "=", padding=None),
                "data": list_node,
            },
        )
        self._tree = tree
        self._particle_importances[particle] = tree

    @property
    def _tree_value(self, particle):
        pass

    def _collect_new_values(self):
        pass
        # TODO

    @staticmethod
    def _class_prefix():
        return "imp"

    @staticmethod
    def _has_number():
        return False

    @staticmethod
    def _has_classifier():
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
                self._particle_importances[particle] = other._particle_importances[
                    particle
                ]
            else:
                raise MalformedInputError(
                    other,
                    "Cannot have two importance inputs for the same particle type",
                )

    def __iter__(self):
        return iter(self._particle_importances.keys())

    def __contains__(self, value):
        return value in self._particle_importances

    def __getitem__(self, particle):
        if not isinstance(particle, Particle):
            raise TypeError("Key must be a particle")
        self._check_particle_in_problem(particle)
        try:
            val = self._particle_importances[particle]["data"][0]
            return val.value
        except KeyError:
            return 0.0

    def __setitem__(self, particle, value):
        if not isinstance(particle, Particle):
            raise TypeError("Key must be a particle")
        self._check_particle_in_problem(particle)
        if not isinstance(value, numbers.Number):
            raise TypeError("importance must be a number")
        if value < 0:
            raise ValueError("importance must be ≥ 0")
        if particle not in self._particle_importances:
            self._generate_default_cell_tree(particle)
        self._particle_importances[particle]["data"][0].value = value

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
            # TODO delete
            self._starting_num_cells = len(self._problem.cells)
            for particle in self._particle_importances:
                if not self._particle_importances[particle]:
                    continue
                for i, cell in enumerate(self._problem.cells):
                    value = self._particle_importances[particle]["data"][i]
                    # force generating the default tree
                    cell.importance[particle] = value.value
                    # replace default ValueNode with actual valueNode
                    data = cell.importance._particle_importances[particle]["data"]
                    data.nodes.pop()
                    data.nodes.append(value)

    def _format_tree(self):
        particles_printed = set()
        ret = ""
        for particle in self:
            if particle in particles_printed:
                continue
            other_particles = self._particle_importances[particle][
                "classifier"
            ].particles
            to_remove = set()
            for other_part in other_particles:
                if other_part != particle:
                    if math.isclose(
                        self[particle],
                        self[other_part],
                        rel_tol=rel_tol,
                        abs_tol=abs_tol,
                    ):
                        particles_printed.add(other_part)
                    else:
                        to_remove.add(other_part)
            for removee in to_remove:
                other_particles.remove(removee)
            ret += self._particle_importances[particle].format()
            particles_printed.add(particle)
        return ret

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
            for particle in self._problem.mode:
                self._particle_importances[particle]["data"][0].value = value

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

    def _update_cell_values(self):
        if not hasattr(self, "_tree"):
            self._generate_default_tree()


def __create_importance_getter(particle_type):
    def closure(obj):
        return obj[particle_type]

    return closure


def __create_importance_setter(particle_type):
    def closure(obj, value):
        obj[particle_type] = value

    return closure


def __create_importance_deleter(particle_type):
    def closure(obj):
        del obj[particle_type]

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

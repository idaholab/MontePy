# Copyright 2024, Battelle Energy Alliance, LLC All Rights Reserved.
import collections
import copy
import math
from montepy.data_inputs.cell_modifier import CellModifierInput
from montepy.errors import *
from montepy.constants import DEFAULT_VERSION, rel_tol, abs_tol
from montepy.input_parser import syntax_node
from montepy.mcnp_object import MCNP_Object
from montepy.particle import Particle
from montepy.utilities import *
import numbers

#
# ********************* Developer Notes ********************************************
#
# How Importance handles syntax trees is complicated.
# One object holds information for N particle types.
# This can be associated with between 1 and N syntax trees (imp:n,p v. imp:n imp:p)
#
# Variables
#
# * _tree      : the syntax tree from parsing. Only used on initial parsing
# * _real_tree : holds unique trees for every particle type. This is used in data block formatting.
# * _particle_importances : a dictionary of ParameterNodes that maps a particle to it's ParameterNode
# * _part_combos : a list of ParticleNode that show which particles were combined on the original input


class Importance(CellModifierInput):
    """
    A data input that sets the importance for a cell(s).

    :param input: the Input object representing this data input
    :type input: Input
    :param in_cell_block: if this card came from the cell block of an input file.
    :type in_cell_block: bool
    :param key: the key from the key-value pair in a cell
    :type key: str
    :param value: the value syntax tree from the key-value pair in a cell
    :type value: SyntaxNode
    """

    def __init__(self, input=None, in_cell_block=False, key=None, value=None):
        self._particle_importances = {}
        self._real_tree = {}
        self._part_combos = []
        super().__init__(input, in_cell_block, key, value)
        if self.in_cell_block:
            if key:
                val = value["data"]
                if isinstance(val, syntax_node.ListNode):
                    val = value["data"][0]
                if val.type != float or val.value < 0:
                    raise ValueError(
                        f"Cell importance must be a number ≥ 0. {val.value} was given"
                    )
                self._part_combos.append(self.particle_classifiers)
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
            self._part_combos.append(self.particle_classifiers)
            for particle in self.particle_classifiers:
                self._particle_importances[particle] = copy.deepcopy(self._tree)
                self._real_tree[particle] = copy.deepcopy(self._tree)

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
        if other.set_in_cell_block:
            self._set_in_cell_block = True
        for particle in other:
            if particle not in self:
                self._particle_importances[particle] = other._particle_importances[
                    particle
                ]
                # keep original formatting external to data cleared out
                if not self.in_cell_block:
                    self._real_tree[particle] = self._particle_importances[particle]
            else:
                raise MalformedInputError(
                    other._input,
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
            for particle in self._particle_importances:
                if not self._particle_importances[particle]:
                    continue
                for i, cell in enumerate(self._problem.cells):
                    value = self._particle_importances[particle]["data"][i]
                    # force generating the default tree
                    cell.importance[particle] = value.value
                    # replace default ValueNode with actual valueNode
                    tree = cell.importance._particle_importances[particle]
                    tree.nodes["classifier"] = copy.deepcopy(
                        self._particle_importances[particle]["classifier"]
                    )
                    tree["classifier"].padding = None
                    data = tree["data"]
                    data.nodes.pop()
                    data.nodes.append(value)

    def _format_tree(self):
        if self.in_cell_block:
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
        else:
            printed_parts = set()
            ret = []
            for particle, tree in self._real_tree.items():
                if particle in printed_parts:
                    continue
                printed_parts |= tree["classifier"].particles.particles
                ret.append(tree.format())
            return "\n".join(ret)

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

    def _collect_new_values(self):
        new_vals = collections.defaultdict(list)
        particle_pairings = collections.defaultdict(set)
        for particle in self._problem.mode.particles:
            for cell in self._problem.cells:
                try:
                    tree = cell.importance._particle_importances[particle]
                except KeyError:
                    raise ParticleTypeNotInCell(
                        f"Importance data not available for cell {cell.number} for particle: "
                        f"{particle}, though it is in the problem"
                    )
                new_vals[particle].append(tree["data"][0])
                if len(particle_pairings[particle]) == 0:
                    particle_pairings[particle] = tree["classifier"].particles.particles
                else:
                    particle_pairings[particle] &= tree[
                        "classifier"
                    ].particles.particles
        return self._try_combine_values(new_vals, particle_pairings)

    def _update_values(self, in_middle=False):
        if self.in_cell_block:
            self._update_cell_values()
            length = len(self._particle_importances)
            for i, tree in enumerate(self._particle_importances.values()):
                if i < length - 1:
                    edge = tree["data"][-1]
                    if isinstance(edge, syntax_node.ValueNode) and edge.padding is None:
                        edge.padding = syntax_node.PaddingNode(" ")
        else:
            new_vals = self._collect_new_values()
            for part_set, data in new_vals.items():
                for particle in part_set:
                    if particle not in self._real_tree:
                        tree = _generate_default_data_tree(particle)
                        self._real_tree[particle] = tree
                        padding = tree["classifier"].padding
                        tree.nodes["classifier"] = copy.deepcopy(
                            next(
                                iter(self._problem.cells)
                            ).importance._particle_importances[particle]["classifier"]
                        )
                        tree["classifier"].padding = padding
                    tree = self._real_tree[particle]
                    tree["classifier"].particles.particles = set(part_set)
                    tree["data"].update_with_new_values(data)

    def _try_combine_values(self, new_vals, particle_pairings):
        covered_parts = set()
        ret = {}
        for particle, pairings in particle_pairings.items():
            if particle in covered_parts:
                continue
            gold = new_vals[particle]
            matching_parts = {particle}
            covered_parts.add(particle)
            for test_part in pairings:
                if test_part == particle or test_part in covered_parts:
                    continue
                test_vals = new_vals[test_part]
                matches = True
                for gold_val, test_val in zip(gold, test_vals):
                    if not math.isclose(
                        gold_val.value,
                        test_val.value,
                        rel_tol=rel_tol,
                        abs_tol=abs_tol,
                    ):
                        matches = False
                        break
                if matches:
                    matching_parts.add(test_part)
                    covered_parts.add(test_part)
            ret[frozenset(matching_parts)] = gold
        return ret

    def _update_cell_values(self):
        pass

    @property
    def trailing_comment(self):
        """
        The trailing comments and padding of an input.

        Generally this will be blank as these will be moved to be a leading comment for the next input.

        :returns: the trailing ``c`` style comments and intermixed padding (e.g., new lines)
        :rtype: list
        """
        last_tree = list(self._real_tree.values())[-1]
        if last_tree:
            return last_tree.get_trailing_comment()

    def _delete_trailing_comment(self):
        for part, tree in reversed(self._real_tree.items()):
            tree._delete_trailing_comment()
            self.__delete_common_trailing(part)
            break

    def __delete_common_trailing(self, part):
        to_delete = {part}
        for combo_set in self._part_combos:
            if part in combo_set:
                to_delete |= combo_set
        if self._in_cell_block:
            for part in to_delete:
                self._particle_importances[part]["data"]._delete_trailing_comment()
        else:
            for part in to_delete:
                self._real_tree[part]._delete_trailing_comment()

    def _grab_beginning_comment(self, new_padding, last_obj=None):
        last_tree = None
        last_padding = None
        if self._in_cell_block:
            if not isinstance(last_obj, Importance):
                for part, tree in self._particle_importances.items():
                    if last_padding is not None and last_tree is not None:
                        last_tree._grab_beginning_comment(last_padding)
                        self.__delete_common_trailing(part)
                    last_padding = tree.get_trailing_comment()
                    last_tree = tree
                if new_padding:
                    next(iter(self._particle_importances.values()))[
                        "start_pad"
                    ]._grab_beginning_comment(new_padding)
        else:
            # if not inside a block of importances
            if not isinstance(last_obj, Importance):
                for part, tree in self._real_tree.items():
                    if tree.get_trailing_comment() == last_padding:
                        continue
                    if last_padding is not None and last_tree is not None:
                        last_tree._grab_beginning_comment(last_padding)
                        self.__delete_common_trailing(part)
                    last_padding = tree.get_trailing_comment()
                    last_tree = tree
                if new_padding:
                    next(iter(self._real_tree.values()))[
                        "start_pad"
                    ]._grab_beginning_comment(new_padding)
            # otherwise keep it as is inside the block
            else:
                list(self._real_tree.values())[-1]["start_pad"]._grab_beginning_comment(
                    new_padding
                )


def _generate_default_data_tree(particle):
    list_node = syntax_node.ListNode("number sequence")
    list_node.append(syntax_node.ValueNode(None, float))
    classifier = syntax_node.ClassifierNode()
    classifier.prefix = syntax_node.ValueNode("IMP", str)
    classifier.padding = syntax_node.PaddingNode(" ")
    classifier.particles = syntax_node.ParticleNode(
        "IMP_particles", f":{particle.value}"
    )
    classifier.particles.particles = {particle}
    return syntax_node.SyntaxNode(
        "IMP",
        {
            "start_pad": syntax_node.PaddingNode(),
            "classifier": classifier,
            "keyword": syntax_node.ValueNode(None, str, None),
            "data": list_node,
        },
    )


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

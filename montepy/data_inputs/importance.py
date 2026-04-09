# Copyright 2024, Battelle Energy Alliance, LLC All Rights Reserved.
from __future__ import annotations
import collections
import copy
import math
import warnings

import montepy
from montepy.data_inputs.cell_modifier import CellModifierInput, InitInput
from montepy.exceptions import *
from montepy.constants import DEFAULT_VERSION, rel_tol, abs_tol
from montepy.input_parser import syntax_node
from montepy.mcnp_object import MCNP_Object
from montepy.particle import Particle
import montepy.types as ty
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
# * _inputs    : holds the original Importance inputs from all distinct instances
# * _particle_importances : a dictionary of ParameterNodes that maps a particle to it's ParameterNode
# * _part_combos : a list of ParticleNode that show which particles were combined on the original input
#
# Defaults and all or nothing
#
# The default value is stored in _DEFAULT_IMP
#
#


class Importance(CellModifierInput):
    """A data input that sets the importance for a cell(s).

    Parameters
    ----------
    input : Input | str
        the Input object representing this data input
    in_cell_block : bool
        if this card came from the cell block of an input file.
    key : str
        the key from the key-value pair in a cell
    value : SyntaxNode
        the value syntax tree from the key-value pair in a cell
    """

    _DEFAULT_IMP = 1.0
    _ALL_OR_NOTHING = True
    """
    Marks that if one cell has a value all cells must have values, no matter the default.
    """
    _KEYS_TO_PRESERVE = {"_parked_value", "_inputs"}

    def _init_blank(self):
        self._particle_importances = {}
        self._real_tree = {}
        self._inputs = []
        self._part_combos = []
        self.__explicitly_set = False

    def _parse_cell_tree(self):
        if self._in_key:
            val = self._in_value["data"]
            if isinstance(val, syntax_node.ListNode):
                val = self._in_value["data"][0]
            if val.type != float or val.value < 0:
                raise ValueError(
                    f"Cell importance must be a number ≥ 0. {val.value} was given"
                )
            self._explicitly_set = True
            self._part_combos.append(self.particle_classifiers)
            for particle in self.particle_classifiers:
                self._particle_importances[particle] = self._in_value

    def _parse_data_tree(self):
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
        self._explicitly_set = True
        self._part_combos.append(self.particle_classifiers)
        for particle in self.particle_classifiers:
            self._particle_importances[particle] = copy.deepcopy(self._tree)
            self._real_tree[particle] = copy.deepcopy(self._tree)

    def _generate_default_cell_tree(self, particle=None):
        classifier = syntax_node.ClassifierNode()
        classifier.prefix = self._generate_default_node(str, self._class_prefix(), None)
        if particle is None:
            particles = syntax_node.ParticleNode("imp particle", "n")
            particle = Particle.NEUTRON
        else:
            particles = syntax_node.ParticleNode("imp particle", particle.value.lower())
        classifier.particles = particles
        list_node = syntax_node.ListNode("imp data")
        list_node.append(self._generate_default_node(float, self._DEFAULT_IMP))
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

    def _generate_default_data_tree(self, particle=None):
        self._tree = _generate_default_data_tree(Particle.NEUTRON)

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

    def keys(self) -> collections.abc.Generator[Particle, None, None]:
        """
        Returns a generator of all of the particles that have set values for this importance.

        .. versionadded:: 1.4.0
        """
        yield from self._particle_importances.keys()

    def values(self) -> collections.abc.Generator[float, None, None]:
        """Returns a generator of the importance values set for this cell in the order in which they were set.

        .. versionadded:: 1.4.0
        """
        for tree in self._particle_importances.values():
            yield tree["data"][0].value

    def items(
        self,
    ) -> collections.abc.Generator[tuple[Particle, float], None, None]:
        """Returns a generator of the particle and the importance value for all importances set for this cell.

        .. versionadded:: 1.4.0
        """
        for part in self:
            yield (part, self._particle_importances[part]["data"][0].value)

    @property
    @needs_full_ast
    def has_information(self):
        has_info = []
        for part in self:
            has_info.append(
                self._explicitly_set
                or not math.isclose(
                    # avoid __getitem__ to avoid warnings of not in problem due to default values
                    self._particle_importances[part]["data"][0].value,
                    self._DEFAULT_IMP,
                    rel_tol=rel_tol,
                    abs_tol=abs_tol,
                )
            )
        if any(has_info):
            return True
        if self.in_cell_block:
            return self.set_in_cell_block

    @args_checked
    def merge(self, other: Importance):
        # ensure all parsed or none are parsed
        if not self.full_parsed:
            if other.full_parsed:
                self.full_parse()
            else:
                self._inputs.append(other)
                return
        # if full parsed
        elif not other.full_parsed:
            other.full_parse()
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

    def full_parse(self):
        if hasattr(self, "_not_parsed") and self._not_parsed:
            super().full_parse()
        # handle all other inputs
        has_extra = bool(self._inputs)
        for input in self._inputs:
            input.full_parse()
            self.merge(input)
        self._inputs.clear()
        if has_extra and not self.in_cell_block and self._problem:
            self.push_to_cells()

    def _original_lines(self):
        ret = super()._original_lines()
        for input in self._inputs:
            ret += input._input.input_lines
        return ret

    @needs_full_ast
    def __iter__(self):
        return iter(self._particle_importances.keys())

    @needs_full_ast
    def __contains__(self, value):
        return value in self._particle_importances

    @needs_full_ast
    @args_checked
    def __getitem__(self, particle: Particle):
        self._check_particle_in_problem(particle)
        try:
            val = self._particle_importances[particle]["data"][0]
            return val.value
        except KeyError:
            return self._DEFAULT_IMP

    @needs_full_cst
    @args_checked
    def __setitem__(self, particle: Particle, value: ty.NonNegativeReal):
        self._check_particle_in_problem(particle)
        if particle not in self._particle_importances:
            self._generate_default_cell_tree(particle)
        self._explicitly_set = True
        self._particle_importances[particle]["data"][0].value = value

    @needs_full_cst
    @args_checked
    def __delitem__(self, particle: Particle):
        del self._particle_importances[particle]

    @needs_full_ast
    def push_to_cells(self):
        if self._problem and not self.in_cell_block:
            # TODO
            self._check_redundant_definitions()
            part_keys = self._particle_importances.keys()
            cell_importances = []
            # Doing in place transpose
            for imp_group in zip(
                *[v["data"] for v in self._particle_importances.values()]
            ):
                cell_importances.append({k: v for k, v in zip(part_keys, imp_group)})
            for cell_imp, cell in zip(cell_importances, self._problem.cells):
                for particle, val in cell_imp.items():
                    cell._importance._accept_from_data(particle, val)

    def _accept_from_data(self, key, value):
        if hasattr(self, "_not_parsed"):
            if not hasattr(self, "_parked_value"):
                self._parked_value = {}
            self._parked_value[key] = value
        else:
            self._accept_and_update({key: value})

    def _accept_and_update(self, value):
        for part, val in value.items():
            self[part] = val.value
            data_tree = self._particle_importances[part]["data"]
            data_tree.nodes.pop()
            data_tree.nodes.append(val)
        self._explicitly_set = True

    def _format_tree(self):
        def ensure_has_end_space(ret, strip_new_lines=False):
            if strip_new_lines:
                ret = ret.rstrip("\n")
            if ret and ret[-1] != " ":
                # remove new lines that exist
                return ret.rstrip() + " "
            return ret

        if self.in_cell_block:
            particles_printed = set()
            ret = ""
            for particle in self:
                if particle in particles_printed or (
                    self._problem and particle not in self._problem.mode
                ):
                    continue
                particle_node = self._particle_importances[particle][
                    "classifier"
                ].particles
                other_particles = set(particle_node.particles)
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
                if to_remove:
                    particle_node.particles = other_particles - to_remove
                ret = ensure_has_end_space(ret)
                ret += self._particle_importances[particle].format()
                particles_printed.add(particle)
            # catch default values
            if self._problem:
                missed_defaults = self._problem.mode.particles - particles_printed
                for particle in missed_defaults:
                    # trigger adding syntax tree
                    self[particle] = self._DEFAULT_IMP
                    ret = ensure_has_end_space(ret, strip_new_lines=True)
                    ret += self._particle_importances[particle].format()
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
        """Setter for setting importance for all particle types in the problem at once.

        Parameters
        ----------
        importance : float
            the importance to set all particles to.

        Returns
        -------
        None
            None
        """
        return None

    @all.setter
    @needs_full_cst
    @args_checked
    def all(self, value: ty.NonNegativeReal):
        value = float(value)
        self._explicitly_set = True
        if self._problem:
            for particle in self._problem.mode:
                self._particle_importances[particle]["data"][0].value = value
        else:
            for particle in montepy.Particle:
                self[particle] = value

    def _clear_data(self):
        if not self.in_cell_block:
            self._particle_importances = {}

    def _check_particle_in_problem(self, particle_type):
        if self._problem:
            if particle_type not in self._problem.mode:
                warnings.warn(
                    f"Particle type: {particle_type} not included in problem mode.",
                    ParticleTypeNotInProblem,
                )

    def _collect_new_values(self):
        new_vals = collections.defaultdict(list)
        # Seed pairings from _real_tree classifiers so that particle groups
        # originally written together (e.g. imp:n,p) are preserved even when
        # cell-level importances were generated with single-particle classifiers
        # (which happens after push_to_cells creates default cell trees).
        # Both particles in a combined entry (e.g. N and P for imp:n,p) each
        # have a deepcopy of the same original tree, so the pairing is symmetric.
        particle_pairings = {
            p: t["classifier"].particles.particles for p, t in self._real_tree.items()
        }
        for particle in self._problem.mode.particles:
            if particle not in particle_pairings:
                particle_pairings[particle] = {particle}
            for cell in self._problem.cells:
                imp = cell._importance
                if hasattr(imp, "_not_parsed"):
                    imp.full_parse()
                try:
                    tree = imp._particle_importances[particle]
                except KeyError:
                    raise NotImplementedError(
                        f"Importance data not available for cell {cell.number} for particle: "
                        f"{particle}, though it is in the problem, and default importance logic "
                        "is not yet implemented in MontePy."
                    )
                new_vals[particle].append(tree["data"][0])
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
    @needs_full_ast
    def trailing_comment(self) -> syntax_node.CommentNode:
        """The trailing comments and padding of an input.

        Generally this will be blank as these will be moved to be a leading comment for the next input.

        Returns
        -------
        list
            the trailing ``c`` style comments and intermixed padding
            (e.g., new lines)
        """
        last_tree = list(self._real_tree.values())[-1]
        if last_tree:
            return last_tree.get_trailing_comment()

    @needs_full_cst
    def _delete_trailing_comment(self):
        for part, tree in reversed(self._real_tree.items()):
            tree._delete_trailing_comment()
            self.__delete_common_trailing(part)
            break

    @needs_full_cst
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

    @needs_full_cst
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

    @property
    def _explicitly_set(self):
        return self.__explicitly_set

    @_explicitly_set.setter
    def _explicitly_set(self, value):
        if value and self._problem:
            self._problem.print_in_data_block._set_all_or_none(self._class_prefix())
        self.__explicitly_set = value

    def link_to_problem(self, problem, *, deepcopy: bool = False):
        super().link_to_problem(problem, deepcopy=deepcopy)
        if not deepcopy and problem and self._explicitly_set:
            self._problem.print_in_data_block._set_all_or_none(self._class_prefix())


def _generate_default_data_tree(particle):
    list_node = syntax_node.ListNode("number sequence")
    list_node.append(syntax_node.ValueNode(str(Importance._DEFAULT_IMP), float))
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

Parameters
----------
importance: float 
    The importance to set this to.

Returns
-------
float
    the importance for the particle type. If not set, defaults to 1.0.
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

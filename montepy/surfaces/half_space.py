# Copyright 2024, Battelle Energy Alliance, LLC All Rights Reserved.
import montepy
from montepy.errors import *
from montepy.geometry_operators import Operator
from montepy.input_parser.syntax_node import (
    GeometryTree,
    PaddingNode,
    ValueNode,
    CommentNode,
)
from montepy.utilities import *


class HalfSpace:
    """
    Class representing a geometry half_space.

    .. versionadded:: 0.2.0
        This was added as the core of the rework to how MCNP geometries are implemented.

    The term `half-spaces <https://en.wikipedia.org/wiki/Half-space_(geometry)>`_ in MontePy is used very loosely,
    and is not mathematically rigorous. In MontePy a divider is a something
    that splits a space (R\\ :sup:`3` ) into two half-spaces. At the simplest this would
    be a plane or other quadratic surface. There will always be two half-spaces,
    a negative, or inside (False) or positive, outside (True).
    This class proper is for binary trees implementing
    `constructive solid geometry (CSG) <https://en.wikipedia.org/wiki/Constructive_solid_geometry>`_ set logic.
    The same logic with half-spaces still apply as the intersection will always create two
    half-spaces (though one may be the empty set).
    In this case thinking of "inside" and "outside" may be more useful.

    HalfSpaces use binary operators to implement set logic.

    For Intersection:

    .. code-block:: python

        half_space = left & right
        half_space &= other_side

    For Union:

    .. code-block:: python

        half_space = left | right
        half_space |= other_side

    And you can also complement a HalfSpace:

    .. code-block:: python

        half_space = ~ other_half_space

    Parantheses are allowed, and handled properly

    .. code-block:: python

        half_space = +bottom & (-left | +right)

    :param left: The left side of the binary tree.
    :type left: HalfSpace
    :param operator: the operator to apply between the two branches.
    :type operator: Operator
    :param right: the right side of the binary tree.
    :type right: HalfSpace
    :param node: the node this was parsed from.
    :type node: GeometryTree
    """

    def __init__(self, left, operator, right=None, node=None):
        if not isinstance(left, HalfSpace):
            raise TypeError(f"left must be a HalfSpace. {left} given.")
        if not isinstance(right, (HalfSpace, type(None))):
            raise TypeError(f"right must be a HalfSpace, or None. {right} given.")
        if not isinstance(operator, Operator):
            raise TypeError(f"operator must be of type Operator. {operator} given.")
        if not isinstance(node, (GeometryTree, type(None))):
            raise TypeError(f"node must be a GeometryTree or None. {node} given.")
        if right is None and operator not in {Operator.COMPLEMENT, Operator.GROUP}:
            raise ValueError(f"Both sides required for: {operator}")
        self._left = left
        self._operator = operator
        self._right = right
        self._node = node
        self._cell = None

    @make_prop_pointer("_left", ())
    def left(self):
        """
        The left side of the binary tree of this half_space.

        :returns: the left side of the tree.
        :rtype: HalfSpace
        """
        pass

    @make_prop_pointer("_right", (), deletable=True)
    def right(self):
        """
        The right side of the binary tree of this half_space if any.

        :returns: the right side of the tree.
        :rtype: HalfSpace
        """
        pass

    @make_prop_pointer("_operator", Operator)
    def operator(self):
        """
        The operator for applying to this binary tree.

        :returns: the operator for the tree.
        :rtype: Operator
        """
        pass

    @make_prop_pointer("_node")
    def node(self):
        """
        The syntax node for this HalfSpace if any.

        If this was generated by :func:`parse_input_node`,
        that initial node will be given. If this was created from scratch,
        a new node will be generated prior as this is being written to file.

        :returns: the node for this tree.
        :rtype: GeometryTree
        """
        pass

    @staticmethod
    def parse_input_node(node):
        """
        Parses the given syntax node as a half_space.

        :param node: the Input syntax node to parse.
        :type node: GeometryTree
        :returns: the HalfSpace properly representing the input geometry.
        :rtype: HalfSpace
        """
        if not isinstance(node, GeometryTree):
            raise TypeError("Node must be a GeoemtryTree.")
        sides = []
        for side in (node.left, node.right):
            if side is None:
                continue
            if isinstance(side, ValueNode):
                is_cell = node.operator == Operator.COMPLEMENT
                sides.append(UnitHalfSpace.parse_input_node(side, is_cell))
            else:
                sides.append(HalfSpace.parse_input_node(side))
        if node.operator == Operator._SHIFT and isinstance(sides[0], UnitHalfSpace):
            return sides[0]
        if len(sides) == 1:
            sides.append(None)
        return HalfSpace(sides[0], node.operator, sides[1], node)

    def update_pointers(self, cells, surfaces, cell):
        """
        Update pointers, and link this object to other objects in the problem.

        This will:

        1. Link this HalfSpace (and its children) to the parent cell.
        2. Update the divider parameter to point to the relevant surface or cell.
        3. Update the parent's :func:`~montepy.cell.Cell.surfaces`, and :func:`~montepy.cell.Cell.complements`.

        :param cells: the cells in the problem.
        :type cells: Cells
        :param surfaces: The surfaces in the problem.
        :type surfaces: Surfaces
        :param cell: the cell this HalfSpace is tied to.
        :type cell: Cell
        """
        self._cell = cell
        self.left.update_pointers(cells, surfaces, cell)
        if self.right is not None:
            self.right.update_pointers(cells, surfaces, cell)

    def _add_new_children_to_cell(self, other):
        """
        Adds the cells and surfaces from a new tree to this parent cell.

        :param other: the other HalfSpace to work with.
        :type other: HalfSpace
        """
        if self._cell is None:
            return
        cells, surfaces = other._get_leaf_objects()
        for container, parent in zip(
            (cells, surfaces), (self._cell.complements, self._cell.surfaces)
        ):
            for item in container:
                if item not in parent:
                    parent.append(item)

    def remove_duplicate_surfaces(self, deleting_dict):
        """Updates old surface numbers to prepare for deleting surfaces.

        This will ensure any new surfaces or complements properly get added to the parent
        cell's :func:`~montepy.cell.Cell.surfaces` and :func:`~montepy.cell.Cell.complements`.

        :param deleting_dict: a dict of the surfaces to delete.
        :type deleting_dict: dict
        """
        _, surfaces = self._get_leaf_objects()
        new_deleting_dict = {}
        for dead_surface, new_surface in deleting_dict.items():
            if dead_surface in surfaces:
                new_deleting_dict[dead_surface] = new_surface
        if len(new_deleting_dict) > 0:
            self.left.remove_duplicate_surfaces(new_deleting_dict)
            if self.right is not None:
                self.right.remove_duplicate_surfaces(new_deleting_dict)

    def _get_leaf_objects(self):
        """
        Get all of the leaf objects for this tree.

        The leaf objects are the surfaces and cells used
        as dividers for this HalfSpace.

        :returns: a Tuple of two sets: cells, and surfaces.
        :rtype: Tuple
        """
        cells, surfaces = self.left._get_leaf_objects()
        if self.right:
            new_cells, new_surfaces = self.right._get_leaf_objects()
            cells |= new_cells
            surfaces |= new_surfaces
        return cells, surfaces

    def _update_values(self):
        self._ensure_has_nodes()
        self._update_node()
        if isinstance(self, UnitHalfSpace):
            return
        self.left._update_values()
        if self.right:
            self.right._update_values()

    def _ensure_has_nodes(self):
        """
        Ensures this HalfSpace and its children has the necessary syntax nodes.
        """
        self._ensure_has_parens()
        self.left._ensure_has_nodes()
        if self.right is not None:
            self.right._ensure_has_nodes()
        if self.node is None:
            if self.operator == Operator.INTERSECTION:
                operator = " "
            elif self.operator == Operator.UNION:
                operator = " : "
            elif self.operator == Operator.COMPLEMENT:
                operator = " #"
            elif self.operator == Operator.GROUP:
                operator = None
            operator = PaddingNode(operator)
            # Update trees
            if self.operator in {Operator.INTERSECTION, Operator.UNION}:
                ret = {"left": self.left.node, "operator": operator}
            elif self.operator == Operator.COMPLEMENT and isinstance(
                self.left, UnitHalfSpace
            ):
                ret = {"operator": operator, "left": self.left.node}
            else:
                ret = {
                    "operator": operator,
                    "start_pad": PaddingNode("("),
                    "left": self.left.node,
                    "end_pad": PaddingNode(")"),
                }
            # handle right side of tree
            if self.right is not None:
                ret["right"] = self.right.node
            self._node = GeometryTree(
                "default geometry", ret, self.operator.value, self.left, self.right
            )
        self.node.nodes["left"] = self.left.node
        if self.right is not None:
            self.node.nodes["right"] = self.right.node

    def _ensure_has_parens(self):
        """
        Ensures that when a parentheses is needed it is added.

        This detects unions below an intersection. It then "adds" a parentheses
        by adding a GROUP to the tree.

        This ignores parentheses needed for complements as its handled in _update_node.
        """
        if self.operator == Operator.INTERSECTION:
            if type(self) == type(self.left) and self.left.operator == Operator.UNION:
                self.left = HalfSpace(self.left, Operator.GROUP)
            if (
                self.right is not None
                and type(self) == type(self.right)
                and self.right.operator == Operator.UNION
            ):
                self.right = HalfSpace(self.right, Operator.GROUP)

    def _update_node(self):
        """
        Ensures that the syntax node properly reflects the current HalfSpace structure
        """
        try:
            operator_node = self.node.nodes["operator"]
            output = operator_node.format()
        except KeyError:
            output = ""
        if self.operator == Operator.INTERSECTION:
            if not output.isspace():
                self.__switch_operator(" ")
        elif self.operator == Operator.UNION:
            if ":" not in output:
                self.__switch_operator(":")
        elif self.operator == Operator.COMPLEMENT:
            if "#" not in output:
                self.__switch_operator("#")
                # change tree order
                self._node = GeometryTree(
                    "default geometry",
                    {
                        "operator": self.node.nodes["operator"],
                        "left": self.node.nodes["left"],
                    },
                    self.operator.value,
                    self.left.node,
                    None,
                )
        elif self.operator == Operator.GROUP:
            if "start_pad" not in self.node.nodes:
                self._node = GeometryTree(
                    "default Geometry",
                    {
                        "start_pad": PaddingNode("("),
                        "left": self.node.nodes["left"],
                        "end_pad": PaddingNode(")"),
                    },
                    self.operator.value,
                    self.left.node,
                    None,
                )

    def __switch_operator(self, new_symbol):
        """
        Updates the information about the operator in the syntax tree.
        """
        operator_node = self.node.nodes["operator"]
        operator_node._nodes = [
            (
                n.replace("#", " ").replace(":", " ")
                if not isinstance(n, CommentNode)
                else n
            )
            for n in operator_node.nodes
        ]
        if new_symbol == "#":
            operator_node._nodes[-1] = operator_node.nodes[-1][:-1] + "#"
        elif new_symbol == ":":
            output = operator_node.format()
            midpoint = len(output) // 2
            total_len = 0
            for i, node in enumerate(operator_node.nodes):
                if total_len + len(node) - 1 >= midpoint:
                    break
                total_len += len(node)
            index = midpoint - total_len
            operator_node._nodes[i] = node[:index] + ":" + node[index + 1 :]

    def __iand__(self, other):
        if not isinstance(other, HalfSpace):
            raise TypeError(f"Right hand side must be HalfSpace. {other} given.")
        if isinstance(self, UnitHalfSpace):
            return self & other
        right_leaf = (
            self.right is not None and isinstance(self.right, UnitHalfSpace)
        ) or self.right is None
        if right_leaf:
            if self.right is not None:
                self.right = self.right & other
                return self
            else:
                return (~self.left) & other
        self.right &= other
        self._add_new_children_to_cell(other)
        return self

    def __ior__(self, other):
        if not isinstance(other, HalfSpace):
            raise TypeError(f"Right hand side must be HalfSpace. {other} given.")
        if isinstance(self, UnitHalfSpace):
            return self | other
        right_leaf = (
            self.right is not None and isinstance(self.right, UnitHalfSpace)
        ) or self.right is None
        if right_leaf:
            if self.right is not None:
                self.right = self.right | other
                return self
            else:
                return (~self.left) | other
        self.right |= other
        self._add_new_children_to_cell(other)
        return self

    def __and__(self, other):
        if not isinstance(other, HalfSpace):
            raise TypeError(f"Right hand side must be HalfSpace. {other} given.")
        return HalfSpace(self, Operator.INTERSECTION, other)

    def __or__(self, other):
        if not isinstance(other, HalfSpace):
            raise TypeError(f"Right hand side must be HalfSpace. {other} given.")
        return HalfSpace(self, Operator.UNION, other)

    def __invert__(self):
        return HalfSpace(self, Operator.COMPLEMENT)

    def __len__(self):
        length = 0
        length += len(self.left)
        if self.right is not None:
            length += len(self.right)
        return length

    def __eq__(self, other):
        # don't allow subclassing on right side
        if type(self) != type(other):
            raise TypeError(f"HalfSpaces can only be compared to each other")
        if self.operator != other.operator:
            return False
        if (self.right is None) != (other.right is None):
            return False

        if self.left != other.left:
            return False
        if self.right is not None and self.right == other.right:
            return True
        elif self.right is None:
            return True
        return False

    def _generate_default_tree(self):
        pass

    def __str__(self):
        if self.operator == Operator.COMPLEMENT:
            return f"{self.operator.value}{self.left}"
        if self.operator == Operator.GROUP:
            return str(self.left)
        return f"({self.left}{self.operator.value}{self.right})"

    def __repr__(self):
        return f"(l: {repr(self.left)}| op: {self.operator}| r:{repr(self.right)})"


class UnitHalfSpace(HalfSpace):
    """
    The leaf node for the HalfSpace tree.
    
    .. versionadded:: 0.2.0
        This was added as the core of the rework to how MCNP geometries are implemented.

    This can only be used as leaves and represents one half_space of a 
    a divider.
    The easiest way to generate one is with the divider with unary operators. 
    For surfaces you can choose the positive (True) or negative (False) side quickly:

    .. code-block:: python

        bottom_half = -surf
        top_half = +surf

    For a cell you can only take the complement:
    
    .. code-block:: python
    
        comp = ~cell

    .. Note::
        
        When you complement a cell you don't actually get a UnitHalfSpace directly.
        You get a UnitHalfSpace wrapped with a complementing HalfSpace Tree

        .. code-block:: text

                     HalfSpace
                   /      #   \\
            UnitHalfSpace      None
                   |
                   Cell

    :param divider: the divider object
    :type divider: int, Cell, Surface
    :param side: which side the divider is on. For Cells this will be True.
    :type side: bool
    :param is_cell: Whether or not this is a cell or not for the divider.
    :type is_cell: bool
    :param node: the node if any this UnitHalfSpace was built from
    :type node: ValueNode
    """

    def __init__(self, divider, side, is_cell, node=None):
        if not isinstance(
            divider, (int, montepy.Cell, montepy.surfaces.surface.Surface)
        ):
            raise TypeError(
                f"divider must be an int, Cell, or Surface. {divider} given"
            )
        if not isinstance(side, bool):
            raise TypeError(f"side must be bool. {side} given.")
        if not isinstance(is_cell, bool):
            raise TypeError(f"is_cell must be bool. {is_cell} given.")
        if not isinstance(node, (ValueNode, type(None))):
            raise TypeError(f"node must be a ValueNode or None. {node} given.")
        self._divider = divider
        self._side = side
        self._is_cell = is_cell
        self._node = node
        self._cell = None

    @property
    def divider(self):
        """
        The divider this UnitHalfSpace is based on.

        :returns: the divider defining this HalfSpace
        :rtype: int, Cell, Surface
        """
        return self._divider

    # done manually to avoid circular imports
    @divider.setter
    def divider(self, div):
        if not isinstance(div, (montepy.Cell, montepy.surfaces.surface.Surface)):
            raise TypeError("Divider must be a Cell or Surface")
        if self.is_cell != isinstance(div, montepy.Cell):
            raise TypeError("Divider type must match with is_cell")
        self._divider = div
        if self._cell is not None:
            if self.is_cell:
                container = self._cell.complements
            else:
                container = self._cell.surfaces
            if div not in container:
                container.append(div)

    @make_prop_pointer("_is_cell", bool)
    def is_cell(self):
        """
        Whether or not the divider this uses is a cell.

        :returns: True if this is a cell based HalfSpace
        :rtype: bool
        """
        pass

    def __str__(self):
        side = ""
        if self.side:
            if not self.is_cell:
                side = "+"
        else:
            side = "-"
        if isinstance(self.divider, int):
            div = self.divider
        else:
            div = self.divider.number
        return f"{side}{div}"

    def __repr__(self):
        return f"s: {self.side}, is_c: {self.is_cell}, div: {self.divider}"

    @property
    def node(self):
        """
        The node that this UnitHalfSpace is based on if any.

        :returns: The ValueNode that this UnitHalfSpace is tied to.
        :rtype: ValueNode
        """
        return self._node

    @make_prop_pointer("_side", bool)
    def side(self):
        """
        Which side of the divider this HalfSpace is on.

        This maps the conventional positive/negative half_spaces of MCNP
        to boolean values. True is the positive side, and False is the negative one.
        For cells this is always True as the Complementing logic is handled by the parent
        binary tree.

        :returns: the side of the divider for the HalfSpace
        :rtype: bool
        """
        # make cells always "+"
        return self.is_cell or self._side

    @staticmethod
    def parse_input_node(node, is_cell=False):
        """
        Parses the given syntax node as a UnitHalfSpace.

        :param node: the Input syntax node to parse.
        :type node: ValueNode
        :param is_cell: Whether or not this UnitHalfSpace represents a cell.
        :type is_cell: bool
        :returns: the HalfSpace properly representing the input geometry.
        :rtype: UnitHalfSpace
        """
        if not isinstance(node, ValueNode):
            raise TypeError(f"Must be called on a ValueNode. {node} given.")
        if not isinstance(is_cell, bool):
            raise TypeError("is_cell must be a bool.")
        node.is_negatable_identifier = True
        if is_cell:
            side = True
        else:
            side = not node.is_negative
        return UnitHalfSpace(node.value, side, is_cell, node)

    def update_pointers(self, cells, surfaces, cell):
        self._cell = cell
        container = surfaces
        par_container = self._cell.surfaces
        if self._is_cell:
            container = cells
            par_container = self._cell.complements
        if isinstance(self.divider, int):
            try:
                self._divider = container[self._divider]
                if self._divider not in par_container:
                    par_container.append(self._divider)
            except KeyError:
                if self._is_cell:
                    raise BrokenObjectLinkError(
                        "Cell", self._cell.number, "Complement", self._divider
                    )
                raise BrokenObjectLinkError(
                    "Cell", self._cell.number, "Surface", self._divider
                )

    def _ensure_has_nodes(self):
        if self.node is None:
            if isinstance(self.divider, int):
                num = self.divider
            else:
                num = self.divider.number
            node = ValueNode(None, int, never_pad=True)
            node.value = num
            node.is_negatable_identifier = True
            node.is_negative = not self.side
            self._node = node

    def _update_node(self):
        if isinstance(self.divider, int):
            self._node.value = self.divider
        else:
            self._node.value = self.divider.number
        self._node.is_negative = not self.side

    def _get_leaf_objects(self):
        if self._is_cell:
            return ({self._divider}, set())
        return (set(), {self._divider})

    def remove_duplicate_surfaces(self, deleting_dict):
        """Updates old surface numbers to prepare for deleting surfaces.

        :param deleting_dict: a dict of the surfaces to delete.
        :type deleting_dict: dict
        """
        if not self.is_cell:
            if self.divider in deleting_dict:
                new_surface = deleting_dict[self.divider]
                self.divider = new_surface

    def __len__(self):
        return 1

    def __eq__(self, other):
        if not isinstance(other, UnitHalfSpace):
            raise TypeError("UnitHalfSpace can't be equal to other type")
        return (
            self.is_cell == other.is_cell
            and self.divider is other.divider
            and self.side == other.side
        )

from mcnpy.geometry_operators import Operator


class HalfSpace:
    def __init__(self, left, operator, right=None):
        # TODO type enforcement
        self._left = left
        self._operator = operator
        self._right = rght

    @property
    def left(self):
        return self._left

    @property
    def right(self):
        return self._right

    @property
    def operator(self):
        return self._operator

    @staticmethod
    def parse_input_node(node):
        pass

    def __iand__(self, other):
        if not isinstance(other, HalfSpace):
            raise TypeError(f"Right hand side must be HalfSpace. {other} given.")
        left_leaf = isinstance(self.left, UnitHalfSpace)
        right_leaf = (
            self.right is not None and isinstance(self.right, UnitHalfSpace)
        ) or self.right is None
        if left_leaf and right_leaf:
            if self.right is not None:
                self.right = self.right & other
                return self
            else:
                return (~self.left) & other
        self.right &= other
        return self

    def __ior__(self, other):
        if not isinstance(other, HalfSpace):
            raise TypeError(f"Right hand side must be HalfSpace. {other} given.")
        left_leaf = isinstance(self.left, UnitHalfSpace)
        right_leaf = (
            self.right is not None and isinstance(self.right, UnitHalfSpace)
        ) or self.right is None
        if left_leaf and right_leaf:
            if self.right is not None:
                self.right = self.right | other
                return self
            else:
                return (~self.left) | other
        self.right |= other
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
        if not isinstance(other, HalfSpace):
            raise TypeError(f"Right hand side must be HalfSpace. {other} given.")
        return HalfSpace(self, Operator.COMPLEMENT)


class UnitHalfSpace:
    def __init__(self, divider=None, side=None, node=None):
        if divider and side:
            self._divider = divider
            self._side = side > 0
        elif node:
            pass

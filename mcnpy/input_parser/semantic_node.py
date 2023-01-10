from abc import ABC, abstractmethod
from mcnpy.geometry_operators import Operator
from mcnpy.utilities import fortran_float


class SemanticNodeBase(ABC):
    def __init__(self, name):
        self._name = name
        self._nodes = []

    def append(self, node):
        # todo type checking
        self._nodes.append(node)

    @property
    def nodes(self):
        return self._nodes

    def has_leaves(self):
        if any([isinstance(x, ValueNode) for x in self.nodes]):
            return True
        for node in self.nodes:
            if isinstance(node, SemanticNodeBase):
                if node.has_leaves:
                    return True
        return False

    def get_last_leaf_parent(self):
        for node in self.nodes[::-1]:
            if isinstance(node, Token):
                return self
            if node.has_leaves:
                return node.get_last_leaf_parent()

    def __len__(self):
        return len(self.nodes)

    def print_nodes(self):
        ret = []
        for node in self._nodes:
            ret.append(node.print_nodes())
        return f"N: {self._name} {{{', '.join(ret)}}}"

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, name):
        if isinstance(name, str):
            raise TypeError("Name must be a string")
        self._name = name


class SemanticNode(SemanticNodeBase):
    def __init__(self, name, parse_dict):
        super().__init__(name)
        self._name = name
        self._nodes = parse_dict

    def __getitem__(self, key):
        return self.nodes[key]

    def get_value(self, key):
        temp = self.nodes[key]
        if isinstance(temp, ValueNode):
            return temp.value
        else:
            raise KeyError(f"{key} is not a value leaf node")

    def __str__(self):
        return f"(Node: {self.name}: {self.nodes})"

    def __repr__(self):
        return str(self)


class GeometryTree(SemanticNodeBase):
    def __init__(self, name, tokens, op, left, right=None):
        super().__init__(name)
        self._nodes = tokens
        self._operator = Operator(op)
        self._left_side = left
        self._right_side = right

    def __str__(self):
        return f"Geometry: {self._left_side} {self._operator} {self._right_side}"

    def __repr__(self):
        return str(self)


class PaddingNode(SemanticNodeBase):
    def __init__(self, token):
        super().__init__("padding")
        self._nodes = [token]

    def __str__(self):
        return f"(Padding, {self._nodes})"

    def __repr__(self):
        return str(self)


class ValueNode(SemanticNodeBase):
    def __init__(self, token, token_type, padding=None):
        super().__init__("")
        self._token = token
        self._type = token_type
        if token_type == float:
            self._value = fortran_float(token)
        else:
            self._value = token
        self._padding = padding

    @property
    def padding(self):
        return self._padding

    @padding.setter
    def padding(self, pad):
        self._padding = pad

    def __str__(self):
        return f"(Value, {self._value}, padding: {self._padding}"

    def __repr__(self):
        return str(self)

    @property
    def value(self):
        return self._value


class ListNode(SemanticNodeBase):
    def __init__(self, name):
        super.__init__(name)


class ParametersNode(SemanticNodeBase):
    def __init__(self):
        super().__init__("parameters")
        self._nodes = {}

    def append(self, key, seperator, value):
        self._nodes[key.lower()] = (value, key, seperator)

    def get_value(self, key):
        return self._params[key.lower()][0].value

    def __str__(self):
        return f"(Parameters, {self.nodes})"

    def __repr__(self):
        return str(self)

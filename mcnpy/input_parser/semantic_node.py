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

    def __contains__(self, key):
        return key in self.nodes

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

    def get_geometry_identifiers(self):
        surfaces = []
        cells = []
        for node in self.nodes:
            if isinstance(node, type(self)):
                child_surf, child_cell = node.get_geometry_identifiers()
                surfaces += child_surf
                cells += child_cell
            elif isinstance(node, ValueNode):
                identifier = abs(int(node.value))
                if self._operator == Operator.COMPLEMENT:
                    cells.append(identifier)
                else:
                    surfaces.append(identifier)
        return (surfaces, cells)


class PaddingNode(SemanticNodeBase):
    def __init__(self, token):
        super().__init__("padding")
        self._nodes = [token]

    def __str__(self):
        return f"(Padding, {self._nodes})"

    def __repr__(self):
        return str(self)

    @property
    def value(self):
        return "".join(self.nodes)


class ValueNode(SemanticNodeBase):
    def __init__(self, token, token_type, padding=None):
        super().__init__("")
        self._token = token
        self._type = token_type
        if token_type == float:
            self._value = fortran_float(token)
        elif token_type == int:
            self._value = int(token)
        else:
            self._value = token
        self._padding = padding
        self._nodes = [self]

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


class ParticleNode(SemanticNodeBase):
    def __init__(self, name, token):
        super().__init__(name)
        self._nodes = [self]
        self._token = token
        # TODO parse particles


class ListNode(SemanticNodeBase):
    def __init__(self, name):
        super().__init__(name)

    def __repr__(self):
        return f"(list: {self.name}, {self.nodes})"

    @property
    def value(self):
        strings = []
        for node in self.nodes:
            if isinstance(node, SemanticNodeBase):
                strings.append(str(node.value))
            else:
                strings.append(node)
        return " ".join(strings)


class ClassifierNode(SemanticNodeBase):
    def __init__(self):
        super().__init__("classifier")
        self._prefix = None
        self._number = None
        self._particles = None
        self._modifier = None
        self._nodes = []

    @property
    def prefix(self):
        return self._prefix

    @prefix.setter
    def prefix(self, pref):
        self.append(pref)
        self._prefix = pref

    @property
    def number(self):
        return self._number

    @number.setter
    def number(self, number):
        self.append(number)
        self._number = number

    @property
    def particles(self):
        return self._particles

    @particles.setter
    def particles(self, part):
        self.append(number)
        self._particles = part

    @property
    def modifier(self):
        return self._modifier

    @modifier.setter
    def modifier(self, mod):
        self._modifier = mod


class ParametersNode(SemanticNodeBase):
    def __init__(self):
        super().__init__("parameters")
        self._nodes = {}

    def append(self, *argv):
        if len(argv) == 3:
            key, seperator, value = argv
            self._nodes[key.lower()] = (value, key, seperator)
        elif len(argv) == 4:
            key, particle, seperator, value = argv
            self._nodes[key.lower() + particle.lower()] = (
                value,
                key,
                particle,
                seperator,
            )

    def get_value(self, key):
        return self.nodes[key.lower()][0].value

    def __str__(self):
        return f"(Parameters, {self.nodes})"

    def __repr__(self):
        return str(self)

    def __getitem__(self, key):
        return self.nodes[key.lower()]

    def __contains__(self, key):
        return key.lower() in self.nodes

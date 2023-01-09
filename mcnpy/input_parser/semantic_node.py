from abc import ABC, abstractmethod

# from mcnpy.input_parser.tokens import Token


class SemanticNode(ABC):
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
        if any([isinstance(x, Token) for x in self.nodes]):
            return True
        for node in self.nodes:
            if isinstance(node, SemanticNode):
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


class PaddingNode(SemanticNode):
    def __init__(self, token):
        super().__init__("padding")
        self._nodes = [token]

    def __str__(self):
        return f"(Padding, {self._nodes})"

    def __repr__(self):
        return str(self)


class ValueNode(SemanticNode):
    def __init__(self, token, padding=None):
        super().__init__("")
        self._value = token
        self._padding = padding

    def __str__(self):
        return f"(Value, {self._value}, padding: {self._padding}"

    def __repr__(self):
        return str(self)

    @property
    def value(self):
        return self._value


class ParametersNode(SemanticNode):
    def __init__(self):
        super().__init__("parameters")
        self._params = {}

    def append(self, key, seperator, value):
        self._params[key.lower()] = (value, key, seperator)

    def get_value(self, key):
        return self._params[key][0].value

    def __str__(self):
        return f"(Parameters, {self._params})"

    def __repr__(self):
        return str(self)


class IdentifierNode(SemanticNode):
    pass

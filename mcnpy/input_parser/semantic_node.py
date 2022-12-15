from abc import ABC, abstractmethod
from mcnpy.input_parser.tokens import Token


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


class IdentifierNode(SemanticNode):

    pass

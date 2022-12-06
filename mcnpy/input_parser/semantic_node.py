from abc import ABC, abstractmethod


class SemanticNode(ABC):
    def __init__(self, name):
        self._name = name
        self._nodes = []

    def append(self, node):
        # todo type checking
        self._nodes.append(node)

    def print_nodes(self):
        ret = []
        for node in self._nodes:
            ret.append(node.print_nodes())
        return f"N: {self._name} ({', '.join(ret)})"


class IdentifierNode(SemanticNode):

    pass

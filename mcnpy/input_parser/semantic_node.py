from abc import ABC, abstractmethod


def SemanticNode(ABC):

    def __init__(self, name):
        self._name = name
        self._nodes = []

    def append(self, node):
        # todo type checking
        self._nodes.append(node)

def IdentifierNode(SemanticNode):

    pass

def SemanticLeaf(SemanticNode):
    pass

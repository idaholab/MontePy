from montepy.numbered_object_collection import NumberedObjectCollection
from montepy.data_cards.transform import Transform


class Transforms(NumberedObjectCollection):
    """
    A container of multiple :class:`montepy.data_cards.transform.Transform` instances.
    """

    def __init__(self, objects=None, problem=None):
        super().__init__(Transform, objects, problem)

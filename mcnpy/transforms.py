from mcnpy.numbered_object_collection import NumberedObjectCollection
from mcnpy.data_inputs.transform import Transform


class Transforms(NumberedObjectCollection):
    """
    A container of multiple :class:`mcnpy.data_cards.transform.Transform` instances.
    """

    def __init__(self, objects=None, problem=None):
        super().__init__(Transform, objects, problem)

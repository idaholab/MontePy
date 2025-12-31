# Copyright 2024, Battelle Energy Alliance, LLC All Rights Reserved.
from __future__ import annotations

import montepy
from montepy.utilities import *
from montepy.numbered_object_collection import NumberedObjectCollection
from montepy.universe import Universe
import montepy.types as ty


class Universes(NumberedObjectCollection):
    """A container of multiple :class:`~montepy.universe.Universe` instances.

    This collection can be sliced to get a subset of the universe.
    Slicing is done based on the universe numbers, not their order in the input.
    For example, ``problem.universe[1:3]`` will return a new `universe` collection
    containing Universes with numbers from 1 to 3, inclusive.

    See also
    --------
    :class:`~montepy.numbered_object_collection.NumberedObjectCollection`

    Notes
    -----

    For examples see the ``NumberedObjectCollection`` :ref:`collect ex`.
    """

    @args_checked
    def __init__(
        self,
        objects: ty.Iterable[Universe] = None,
        problem: montepy.MCNP_Problem = None,
    ):
        super().__init__(Universe, objects, problem)

    def __getitem__(self, key):
        try:
            return super().__getitem__(key)
        except KeyError as e:
            if self._problem:
                new_uni = self._problem.cells._universe._find_and_populate_universe(key)
                if new_uni is not None:
                    return new_uni
            raise e

# Copyright 2024, Battelle Energy Alliance, LLC All Rights Reserved.
from abc import ABC, abstractmethod
import inspect
from functools import wraps


class SingletonGroup(ABC):
    """A base class for implementing a Singleton-like data structure.

    This treats immutable objects are Enums without having to list all.
    This is used for: Element, Nucleus, Library. When a brand new instance
    is requested it is created, cached and returned.
    If an existing instance is requested it is returned.
    This is done to reduce the memory usage for these objects.

    """

    __slots__ = "_instances"

    def __new__(cls, *args, **kwargs):
        kwargs_t = tuple([(k, v) for k, v in kwargs.items()])
        try:
            return cls._instances[args + kwargs_t]
        except KeyError:
            instance = super().__new__(cls)
            instance.__init__(*args, **kwargs)
            cls._instances[args + kwargs_t] = instance
            return cls._instances[args + kwargs_t]

    def __init_subclass__(cls, **kwargs):
        """Workaround to get sphinx autodoc happy."""
        cls._instances = {}
        super().__init_subclass__(**kwargs)

        original_new = cls.__new__

        @wraps(original_new)
        def __new__(cls, *args, **kwargs):
            return original_new(cls, *args, **kwargs)

        __new__.__signature__ = inspect.signature(cls.__init__)
        cls.__new__ = staticmethod(__new__)

    def __deepcopy__(self, memo):
        """Make deepcopy happy."""
        if self in memo:
            return memo[self]
        memo[self] = self
        return self

    @abstractmethod
    def __reduce__(self):
        """See: <https://docs.python.org/3/library/pickle.html#object.__reduce__>"""
        pass

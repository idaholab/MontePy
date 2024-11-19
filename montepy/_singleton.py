import collections


class SingletonGroup(type):
    """
    A metaclass for implementing a Singleton-like data structure.

    This treats immutable objects are Enums without having to list all.
    This is used for: Element, Nucleus, Library. When a brand new instance
    is requested it is created, cached and returned.
    If an existing instance is requested it is returned.
    This is done to reduce the memory usage for these objects.
    """

    _instances = collections.defaultdict(dict)

    def __call__(cls, *args, **kwargs):
        kwargs_t = tuple([(k, v) for k, v in kwargs.items()])
        try:
            return cls._instances[cls][args + kwargs_t]
        except KeyError:
            cls._instances[cls][args + kwargs_t] = super(SingletonGroup, cls).__call__(
                *args, **kwargs
            )
            return cls._instances[cls][args + kwargs_t]

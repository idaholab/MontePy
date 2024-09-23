import collections


class SingletonGroup(type):
    """
    Pass
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

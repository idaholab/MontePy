from abc import ABC, abstractmethod


class NumberedObjectCollection(ABC):
    """A collections of cells."""

    def __init__(self, obj_class, objects=None):
        """
        :param cells: the list of cells to start with if needed
        :type cells: list
        """
        self.__num_cache = {}
        if objects:
            assert isinstance(objects, list)
            for obj in objects:
                assert isinstance(obj, obj_class)
                self.__num_cache[obj.number] = obj
            self._objects = objects
        else:
            self._objects = []

    @property
    def numbers(self):
        """
        A generator of the numbers being used.
        """
        for obj in self._objects:
            yield obj.number

    def check_redundant_numbers(self):
        """
        Checks if there are any redundant  numbers.
        :returns: true if there are collisions of numbers
        :rtype: bool
        """
        return len(self._objects) != len(set(self.numbers))

    def pop(self, pos=1):
        """
        Pop the final items off of the collection

        :param pos: The distance from the end of the list to remove.
        :type pos: int
        :return: the final element(s_
        """
        assert isinstance(pos, int)
        assert pos > 0
        obj = self._objects.pop(pos)
        self.__num_cache.pop(obj.number, None)
        return obj

    def extend(self, other_list):
        assert isinstance(other_list, list)
        self._objects.extend(other_list)

    def remove(self, delete):
        self._objects.remove(delete)

    def __iter__(self):
        self._iter = self._objects.__iter__()
        return self._iter

    def __next__(self):
        return self._iter.__next__()

    @abstractmethod
    def append(self, cell):
        pass

    def __getitem__(self, i):
        find_manually = False
        try:
            ret = self.__num_cache[i]
            if ret.number != i:
                ret = None
                find_manually = True
        except KeyError:
            find_manually = True
        if find_manually:
            ret = None
            for obj in self._objects:
                if obj.number == i:
                    ret = obj
                    break
            if ret is None:
                raise KeyError(f"Object with number {i} not found")
        return ret

    def __delitem__(self, idx):
        del self._objects[idx]

    def __len__(self):
        return len(self._objects)

    @abstractmethod
    def __iadd__(self, other):
        pass

    def __contains__(self, element):
        return any(x is element for x in self._objects)

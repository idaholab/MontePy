import itertools as it
from montepy.utilities import *


class MCNP_InputFile:
    """
    A class to represent a distinct input file.

    .. Note::
        this is a bare bones implementation to be fleshed out in the future.

    :param path: the path to the input file
    :type path: str
    :param parent_file: the parent file for this file if any. This occurs when a "read" input is used.
    :type parent_file: str
    """

    def __init__(self, path, parent_file=None):
        self._path = path
        self._parent_file = parent_file
        self._lineno = 1
        self._fh = None

    @make_prop_pointer("_path")
    def path(self):
        """
        The path for the file.

        :rtype: str
        """
        pass

    @property
    def name(self):
        return self.path

    @make_prop_pointer("_parent_file")
    def parent_file(self):
        """
        The parent file for this file.

        This is only used when this file is pointed to by a "read" input.

        :rtype: str
        """
        pass

    @make_prop_pointer("_lineno")
    def lineno(self):
        """
        The current line number being read in the file.

        This is 1-indexed.

        :rtype: int
        """
        pass

    def open(self, mode):
        """
        Opens the underlying file, and returns self.

        :param mode: the mode to open the file in
        :type mode: str
        :returns: self
        """
        self._fh = open(self.path, mode, encoding="ascii")
        return self

    def __enter__(self):
        self._fh.__enter__()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        status = self._fh.__exit__(exc_type, exc_val, exc_tb)
        self._fh = None
        return status

    def __iter__(self):
        for lineno, line in enumerate(self._fh):
            self._lineno = lineno + 1
            yield line

    def read(self, size=-1):
        """ """
        if self._fh:
            ret = self._fh.read(size)
            self._lineno += ret.count("\n")
            return ret

    def readline(self, size=-1):
        """ """
        if self._fh:
            ret = self._fh.readline(size)
            self._lineno += ret.count("\n")
            return ret

    def write(self, to_write):
        if self._fh:
            self._lineno += to_write.count("\n")
            return self._fh.write(to_write)

    def __str__(self):
        return self.name

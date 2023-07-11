from mcnpy.utilities import *


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

    @make_prop_pointer("_path")
    def path(self):
        """
        The path for the file.

        :rtype: str
        """
        pass

    @make_prop_pointer("_parent_file")
    def parent_file(self):
        """
        The parent file for this file.

        This is only used when this file is pointed to by a "read" input.

        :rtype: str
        """
        pass

    @make_prop_pointer("_lineno", int)
    def lineno(self):
        """
        The current line number being read in the file.

        This is 1-indexed.

        :rtype: int
        """
        pass

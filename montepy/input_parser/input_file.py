# Copyright 2024, Battelle Energy Alliance, LLC All Rights Reserved.
import itertools as it
from montepy.constants import ASCII_CEILING
from montepy.utilities import *
import os


class MCNP_InputFile:
    """
    A class to represent a distinct input file.

    .. Note::
        this is a bare bones implementation to be fleshed out in the future.

    .. versionchanged:: 0.3.0
        Added the overwrite attribute.

    :param path: the path to the input file
    :type path: str
    :param parent_file: the parent file for this file if any. This occurs when a "read" input is used.
    :type parent_file: str
    :param overwrite: Whether to overwrite the file 'path' if it exists
    :type overwrite: bool
    """

    def __init__(self, path, parent_file=None, overwrite=False):
        self._path = path
        self._parent_file = parent_file
        self._lineno = 1
        self._replace_with_space = False
        self._overwrite = overwrite
        self._mode = None
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

    def open(self, mode, encoding="ascii", replace=True):
        """
        Opens the underlying file, and returns self.

        This should only ever be completed from within a ``with`` statement.
        For this reason, a ``close`` functional is intentionally
        not provided.


        .. Note::
            For different encoding schemes see the available list
            `here <https://docs.python.org/3.9/library/codecs.html#standard-encodings>`_.

            CP1252 is commonly referred to as "extended-ASCII".
            You may have success with this encoding for working with special characters.

        .. versionchanged:: 0.2.11
            Added guardrails to raise FileExistsError and IsADirectoryError.

        :param mode: the mode to open the file in
        :type mode: str
        :param encoding: The encoding scheme to use. If replace is true, this is ignored, and changed to ASCII
        :type encoding: str
        :param replace: replace all non-ASCII characters with a space (0x20)
        :type replace: bool
        :returns: self
        :raises FileExistsError: if a file already exists with the same path while writing.
        :raises IsADirectoryError: if the path given is actually a directory while writing.
        """
        if "r" in mode:
            if replace:
                self._replace_with_space = True
                mode = "rb"
                encoding = None
        self._mode = mode
        if "w" in mode:
            if os.path.isfile(self.path) and self._overwrite is not True:
                raise FileExistsError(
                    f"{self.path} already exists, and overwrite is not set."
                )
            if os.path.isdir(self.path):
                raise IsADirectoryError(
                    f"{self.path} is a directory, and cannot be overwritten."
                )
        self._fh = open(self.path, mode, encoding=encoding)
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
            if self._mode == "rb" and self._replace_with_space:
                line = self._clean_line(line)
            yield line

    @staticmethod
    def _clean_line(line):
        new_line = bytes([code if code < ASCII_CEILING else ord(" ") for code in line])
        line = new_line.decode("ascii")
        line = line.replace("\r\n", "\n").replace("\r", "\n")
        return line

    def read(self, size=-1):
        """ """
        if self._fh:
            ret = self._fh.read(size)
            if self._mode == "rb" and self._replace_with_space:
                ret = self._clean_line(ret)
            self._lineno += ret.count("\n")
            return ret

    def readline(self, size=-1):
        """ """
        if self._fh:
            ret = self._fh.readline(size)
            if self._mode == "rb" and self._replace_with_space:
                ret = self._clean_line(ret)
            self._lineno += ret.count("\n")
            return ret

    def write(self, to_write):
        if self._fh:
            self._lineno += to_write.count("\n")
            return self._fh.write(to_write)

    def __str__(self):
        return self.name

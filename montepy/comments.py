# Copyright 2026, Battelle Energy Alliance, LLC All Rights Reserved.
from collections.abc import Sequence
import re


class CommentCollection(Sequence):
    """A read-only collection of the comments in an object that supports searching by text.

    This is a :class:`~collections.abc.Sequence` of
    :class:`~montepy.input_parser.syntax_node.CommentNode` instances, so it
    supports indexing, slicing, iteration, and ``len()``. Checking a string
    with the ``in`` operator searches the *text* of all comments, so an
    object can be found by its comments; anything other than a string keeps
    normal membership behavior.

    Examples
    --------

    .. doctest::

        >>> import montepy
        >>> problem = montepy.read_input("foo.imcnp")
        >>> "light water" in problem.materials[1].comments
        True
        >>> import re
        >>> problem.materials[1].comments.search(re.compile(r"(?i)LIGHT"))[0].contents
        'light water'

    Parameters
    ----------
    comments : iterable of CommentNode
        the comments in this collection.
    """

    __slots__ = ("_comments",)

    def __init__(self, comments=()):
        self._comments = tuple(comments)

    def __getitem__(self, i):
        if isinstance(i, slice):
            return CommentCollection(self._comments[i])
        return self._comments[i]

    def __len__(self):
        return len(self._comments)

    def __contains__(self, item):
        """For a string: search the text of all comments; otherwise: normal membership."""
        if isinstance(item, str):
            return any(item in comment for comment in self._comments)
        return item in self._comments

    def __repr__(self):
        return f"CommentCollection({self._comments!r})"

    def search(self, pattern):
        """Searches the text of the comments in this collection.

        The search is run against each comment's
        :attr:`~montepy.input_parser.syntax_node.CommentNode.contents`, that
        is the comment's text without its delimiters (``c``/``$``).

        Parameters
        ----------
        pattern : str or re.Pattern
            a substring to search for, or a compiled regular expression
            (e.g. ``re.compile(pattern, re.IGNORECASE)``).

        Returns
        -------
        CommentCollection
            a new collection of the comments that matched.

        Raises
        ------
        TypeError
            if ``pattern`` is not a str, or a pattern compiled from a str.
        """
        if isinstance(pattern, str):
            matcher = re.compile(re.escape(pattern)).search
        elif isinstance(pattern, re.Pattern) and isinstance(pattern.pattern, str):
            matcher = pattern.search
        else:
            raise TypeError(
                f"pattern must be a str, or a pattern compiled from a str. {pattern} given."
            )
        return CommentCollection(c for c in self._comments if matcher(c.contents))

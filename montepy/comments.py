# Copyright 2026, Battelle Energy Alliance, LLC All Rights Reserved.
import re

from montepy.input_parser.syntax_node import CommentNode


class CommentCollection(list):
    """A list of the comments in an object that supports searching by text.

    This is a :class:`list` of :class:`~montepy.input_parser.syntax_node.CommentNode`
    instances, and behaves like a normal list in every way. In addition,
    checking a string with the ``in`` operator searches the *text* of all
    comments, so an object can be found by its comments; anything other than a
    string keeps the normal list membership behavior.

    Examples
    --------

    .. doctest::

        >>> import montepy
        >>> problem = montepy.read_input("foo.imcnp")
        >>> "light water" in problem.materials[1].comments
        True
        >>> problem.materials[1].comments.search(r"(?i)LIGHT", regex=True)[0].contents
        'light water'
    """

    def __contains__(self, item):
        """For a string: search the text of all comments; otherwise: normal list membership."""
        if isinstance(item, str):
            return bool(self.search(item))
        return super().__contains__(item)

    def search(self, pattern, regex=False):
        """Searches the text of the comments in this collection.

        The search is run against each comment's
        :attr:`~montepy.input_parser.syntax_node.CommentNode.contents`, that
        is the comment's text without its delimiters (``c``/``$``).

        Parameters
        ----------
        pattern : str or re.Pattern
            the substring to search for, or a regular expression when
            ``regex`` is True. Compiled patterns are always treated as
            regular expressions.
        regex : bool
            whether to interpret ``pattern`` as a regular expression.

        Returns
        -------
        CommentCollection
            a new collection of the comments that matched.

        Raises
        ------
        TypeError
            if ``pattern`` is not a str, or a pattern compiled from a str.
        """
        if isinstance(pattern, re.Pattern) and isinstance(pattern.pattern, str):
            matcher = pattern.search
        elif isinstance(pattern, str) and regex:
            matcher = re.compile(pattern).search
        elif isinstance(pattern, str):

            def matcher(contents):
                return pattern in contents

        else:
            raise TypeError(
                f"pattern must be a str, or a pattern compiled from a str. {pattern} given."
            )
        return CommentCollection(c for c in self if matcher(c.contents))

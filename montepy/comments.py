# Copyright 2026, Battelle Energy Alliance, LLC All Rights Reserved.
import re

from montepy.input_parser.syntax_node import CommentNode


class CommentCollection(list):
    """A list of the comments in an object that supports searching by text.

    This is a :class:`list` of :class:`~montepy.input_parser.syntax_node.CommentNode`
    instances, and behaves like a normal list in every way. In addition, it
    supports searching the text of its comments.

    Examples
    --------

    Searching comments with ``in``
    ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

    Checking a string with the ``in`` operator searches the *text* of all
    comments in the collection, so an object can be found by its comments:

    .. testcode::

        import montepy

        problem = montepy.read_input("foo.imcnp")

        for material in problem.materials:
            if "light water" in material.comments:
                print("found material:", material.number)

    .. testoutput::

        found material: 1

    Checking anything other than a string keeps the normal :class:`list`
    behavior, so membership tests for
    :class:`~montepy.input_parser.syntax_node.CommentNode` instances are
    unchanged.

    Searching comments by pattern
    ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

    :func:`search` finds the comments matching a substring, or a regular
    expression with ``regex=True``:

    .. testcode::

        material = problem.materials[1]
        for comment in material.comments.search(r"(?i)LIGHT", regex=True):
            print(comment.contents)

    .. testoutput::

        light water

    """

    def __contains__(self, item):
        """Checks if a string is in the text of any comment, or if a comment is in this list.

        Parameters
        ----------
        item : str or object
            a string to search the text of all comments for, or any other
            object to check list membership for.

        Returns
        -------
        bool
            for a string: True iff the string is contained in any comment's
            ``contents``; otherwise: normal list membership.
        """
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
        if isinstance(pattern, re.Pattern):
            # bytes patterns cannot search the comments' str contents
            if not isinstance(pattern.pattern, str):
                raise TypeError(
                    f"pattern must be a str, or a pattern compiled from a str. {pattern} given."
                )
            matcher = pattern.search
        else:
            if not isinstance(pattern, str):
                raise TypeError(
                    f"pattern must be a str, or a pattern compiled from a str. {pattern} given."
                )
            if regex:
                matcher = re.compile(pattern).search
            else:

                def matcher(contents):
                    return pattern in contents

        return CommentCollection(
            comment for comment in self if matcher(comment.contents)
        )

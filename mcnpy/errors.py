class LineOverRunWarning(UserWarning):
    """
    Raised when non-comment inputs exceed the allowed line length in an input.
    """

    def __init__(self, message):
        self.message = message


class MalformedInputError(ValueError):
    """
    Raised when there is an error parsing the MCNP input
    """

    def __init__(self, card, message):
        self.message = message + "\n the full input: \n " + str(card)
        super().__init__(self.message)


class NumberConflictError(ValueError):
    """
    Raised when there is a conflict in number spaces
    """

    def __init__(self, message):
        super().__init__(message)


class NumberUnallowedError(ValueError):
    """
    Raised when a number is set to an unallowed value
    """

    def __init__(self, object_type, number):
        super().__init__(
            f"The specified number: {number} is not allowed for: {object_type}"
        )


class BrokenObjectLinkError(MalformedInputError):
    """Raised when the referenced object does not exist in the input file."""

    def __init__(self, parent_type, parent_number, child_type, child_number):
        """
        :param parent_type: Name of the parent object linking (e.g., Cell)
        :type parent_type: str
        :param parent_number: the number of the parent object
        :type parent_number: int
        :param child_type: Name of the type of object missing in the link (e.g., surface)
        :type child_type: str
        :param child_number: the number for the missing object
        :type child_number: int
        """
        super().__init__(
            None,
            f"{child_type} {child_number} is missing from the input from the definition of: {parent_type} {parent_number}",
        )


class UnsupportedFeature(NotImplementedError):
    """
    Raised when MCNP syntax that is not supported is found
    """

    def __init__(self, message):
        self.message = message
        super().__init__(self.message)

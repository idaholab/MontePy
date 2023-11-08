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


class NumberConflictError(Exception):
    """
    Raised when there is a conflict in number spaces
    """

    def __init__(self, message):
        super().__init__(message)


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


class ParticleTypeNotInProblem(ValueError):
    """
    Raised when data are set for a particle type not in
    the problem's mode.
    """

    def __init__(self, message):
        super().__init__(message)


class UnsupportedFeature(NotImplementedError):
    """
    Raised when MCNP syntax that is not supported is found
    """

    def __init__(self, message):
        self.message = message
        super().__init__(self.message)


class UnknownElement(ValueError):
    """
    Raised when an undefined element is used.
    """

    def __init__(self, missing_val):
        self.message = f"An element identified by: {missing_val} is unknown to MontePy."
        super().__init__(self.message)


class IllegalState(ValueError):
    """
    Raised when an object can't be printed out due to an illegal state.
    """

    def __init__(self, message):
        self.message = message
        super().__init__(self.message)

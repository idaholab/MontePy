class MalformedInputError(Exception):
    """
    Raised when there is an error parsing the MCNP input
    """

    def __init__(self, card, message):
        self.message = message + "\n the full input: \n " + str(card)
        super().__init__(self.message)


class UnsupportedFeature(NotImplementedError):
    """
    Raised when MCNP syntax that is not supported is found
    """

    def __init__(self, message):
        self.message = message
        super().__init__(self.message)

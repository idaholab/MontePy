import mcnpy


class CellDataPrintController:
    """
    Class for controlling if cell modifier data is printed in cell or data blocks.
    """

    def __init__(self):
        self._print_data = {}

    def __getitem__(self, key):
        if not isinstance(key, str):
            raise TypeError("Key must be a str")
        if key.upper() in mcnpy.Cell._ALLOWED_KEYWORDS:
            try:
                return self._print_data[key.lower()]
            except KeyError:
                return True
        else:
            raise KeyError(f"{key} is not a supported cell modifier in MCNP")

    def __setitem__(self, key, value):
        if not isinstance(key, str):
            raise TypeError("Key must be a str")
        if not isinstance(value, bool):
            raise TypeError("Must be set to a boolean value")
        if key.upper() in mcnpy.Cell._ALLOWED_KEYWORDS:
            self._print_data[key.lower()] = value
        else:
            raise KeyError(f"{key} is not a supported cell modifier in MCNP")

    def __str__(self):
        return f"Print data in data block: {self._print_data}"

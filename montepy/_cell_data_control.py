# Copyright 2024, Battelle Energy Alliance, LLC All Rights Reserved.
import montepy


class CellDataPrintController:
    """Class for controlling if cell modifier data is printed in cell or data blocks."""

    def __init__(self):
        self._print_data = {}
        self._all_or_nothing = {}

    def __getitem__(self, key):
        if not isinstance(key, str):
            raise TypeError("Key must be a str")
        if key.upper() in montepy.Cell._ALLOWED_KEYWORDS:
            return self._print_data.get(key.lower(), False)
        else:
            raise KeyError(f"{key} is not a supported cell modifier in MCNP")

    def __setitem__(self, key, value):
        if not isinstance(key, str):
            raise TypeError("Key must be a str")
        if not isinstance(value, bool):
            raise TypeError("Must be set to a boolean value")
        if key.upper() in montepy.Cell._ALLOWED_KEYWORDS:
            self._print_data[key.lower()] = value
        else:
            raise KeyError(f"{key} is not a supported cell modifier in MCNP")

    def _set_all_or_none(self, key, all_in=True):
        """ """
        self._all_or_nothing[key.upper()] = all_in

    def _get_all_or_none(self, key):
        """ """
        return self._all_or_nothing.get(key.upper(), False)

    def __str__(self):
        return f"Print data in data block: {self._print_data}"

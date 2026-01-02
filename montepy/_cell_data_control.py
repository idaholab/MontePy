# Copyright 2024, Battelle Energy Alliance, LLC All Rights Reserved.
import montepy
from montepy.utilities import *
import weakref


class CellDataPrintController:
    """Class for controlling if cell modifier data is printed in cell or data blocks."""

    _CLASSIFIER_TO_ATTRIBUTE = {
        k._class_prefix(): v[0] for k, v in montepy.Cell._INPUTS_TO_PROPERTY.items()
    }

    def __init__(self, problem):
        self._print_data = {}
        self._problem = weakref.ref(problem)

    @args_checked
    def __getitem__(self, key: str):
        if key.upper() in montepy.Cell._ALLOWED_KEYWORDS:
            return self._print_data.get(key.lower(), False)
        else:
            raise KeyError(f"{key} is not a supported cell modifier in MCNP")

    @args_checked
    def __setitem__(self, key: str, value: bool):
        if key.upper() in montepy.Cell._ALLOWED_KEYWORDS:
            # check if previously set, and has changed
            if (
                key.lower() in self._print_data
                and self._print_data[key.lower()] != value
            ):
                getattr(
                    self._problem().cells, self._CLASSIFIER_TO_ATTRIBUTE[key.lower()]
                ).full_parse()
                for cell in self._problem().cells:
                    cell.full_parse()
            self._print_data[key.lower()] = value
        else:
            raise KeyError(f"{key} is not a supported cell modifier in MCNP")

    def link_to_problem(self, problem):
        self._problem = weakref.ref(problem)

    def __getstate__(self):
        state = self.__dict__.copy()
        state.pop("_problem", None)
        return state

    def __str__(self):
        return f"Print data in data block: {self._print_data}"

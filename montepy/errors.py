# Copyright 2025, Battelle Energy Alliance, LLC All Rights Reserved.

import warnings
import montepy.exceptions


def __getattr__(name):
    if not name.startswith("__"):  # ignore __warningregistry__ and other magic
        warnings.warn(
            message=f"montepy.errors.{name} is deprecated. Instead, use montepy.exceptions.{name}",
            category=DeprecationWarning,
            stacklevel=2,
        )
    return getattr(montepy.exceptions, name)

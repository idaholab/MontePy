# Copyright 2025, Battelle Energy Alliance, LLC All Rights Reserved.

import warnings
import montepy.exceptions
from montepy.utilities import make_deprecation_getter


__gettattr__ = make_deprecation_getter("montepy.errors", "montepy.exceptions", montepy.exceptions) 


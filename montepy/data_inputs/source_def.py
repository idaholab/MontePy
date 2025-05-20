# Copyright 2025, Battelle Energy Alliance, LLC All Rights Reserved.
# from __future__ import annotations

import montepy
from montepy.data_inputs.data_input import DataInputAbstract
from montepy.input_parser.data_parser import ParamOnlyDataParser


class SourceDefinition(DataInputAbstract):
    """Class to hold MT Inputs

    This is designed to be called two ways.
    The first is with a read input file using input_card, comment
    The second is after a read with a material and a comment (using named inputs)

    See Also
    --------

    * :manual63:`5.6.2`
    * :manual62:`110`

    Parameters
    ----------
    input : Union[Input, str]
        the Input object representing this data input
    material : Material
        the parent Material object that owns this
    """

    _parser = ParamOnlyDataParser()

    @staticmethod
    def _class_prefix():
        return "sdef"

    @staticmethod
    def _has_number():
        return False

    @staticmethod
    def _has_classifier():
        return 0

# Copyright 2024, Battelle Energy Alliance, LLC All Rights Reserved.
import montepy
from montepy.data_inputs.data_input import DataInputAbstract
from montepy.input_parser.tally_parser import TallyParser


class TallySegment(DataInputAbstract):
    """ """

    _parser = TallyParser()

    @staticmethod
    def _class_prefix():
        return "fs"

    @staticmethod
    def _has_number():
        return True

    @staticmethod
    def _has_classifier():
        return 0

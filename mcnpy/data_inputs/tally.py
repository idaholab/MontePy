import mcnpy
from mcnpy.data_inputs.data_input import DataInputAbstract
from mcnpy.input_parser.tally_parser import TallyParser


class Tally(DataInputAbstract):
    """ """

    _parser = TallyParser()

    def __init__(self, input):
        """ """
        super().__init__(input)

    @staticmethod
    def _class_prefix():
        return "f"

    @staticmethod
    def _has_number():
        return True

    @staticmethod
    def _has_classifier():
        return 1
from io import StringIO
from unittest import TestCase

import mcnpy


class TestSyntaxParsing(TestCase):
    def testMessageFinder(self):
        test_message = "this is a message"
        test_string = """
message: {test_message}

test title
"""
        for tester, validate in [
            (test_string, test_message),
            (test_string.upper(), test_message.upper()),
        ]:
            with StringIO(tester) as fh:
                generator = mcnpy.input_parser.input_syntax_reader.read_front_matters(
                    fh
                )
                card = next(generator)
                self.assertIsInstance(card, mcnpy.input_parser.mcnp_input.Message)
                self.assertEqual(card.lines[0], validator)

    def testTitleFinder(self):
        pass

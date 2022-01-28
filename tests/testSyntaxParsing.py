from io import StringIO
from unittest import TestCase

import mcnpy


class TestSyntaxParsing(TestCase):
    def testMessageFinder(self):
        test_message = "this is a message"
        test_string = f"""message: {test_message}

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
                self.assertEqual(len(lines), 1)

    def testTitleFinder(self):
        test_title = "Richard Stallman writes GNU"
        test_string = f"""{test_title}
1 0 -1
"""
        for tester, validator in [
            (test_string, test_title),
            (test_string.upper(), test_title.upper()),
        ]:
            with StringIO(tester) as fh:
                generator = mcnpy.input_parser.input_syntax_reader.read_front_matters(
                    fh
                )
                card = next(generator)
                self.assertIsInstance(card, mcnpy.input_parser.mcnp_input.Title)
                self.assertEqual(card.title, validator)

    def testCardFinder(self):
        test_string = """1 0 -1
     5"""
        for i in range(5):
            tester = " " * i + test_string
            with StringIO(tester) as fh:
                generator = mcnpy.input_parser.input_syntax_reader.read_data(fh)
                card = next(generator)
                self.assertIsInstance(card, mcnpy.input_parser.mcnp_input.Card)
                answer = ["1", "0", "-1", "5"]
                self.assertEqual(len(answer), len(card.words))
                for i, word in enumerate(card.words):
                    self.assertEqual(word, answer[i])
                    self.assertEqual(
                        card.block_type, mcnpy.input_parser.block_type.BlockType.CELL
                    )

    def testCommentFinder(self):
        test_string = """c foo
c bar"""
        for i in range(5):
            tester = " " * i + test_string
            with StringIO(tester) as fh:
                card = next(mcnpy.input_parser.input_syntax_reader.read_data(fh))
                self.assertIsInstance(card, mcnpy.input_parser.mcnp_input.Comment)
                self.assertEqual(len(card.lines), 2)
                self.assertEqual(card.lines[0], "foo")
                self.assertEqual(card.lines[1], "bar")

    def testReadCardFinder(self):
        test_string = "read file=foo.imcnp "
        with StringIO(test_string) as fh:
            card = next(mcnpy.input_parser.input_syntax_reader.read_data(fh))
            self.assertIsNone(card)  # the read card is hidden from the user

    def testBlockId(self):
        test_string = "1 0 -1"

        for i in range(3):
            tester = "\n" * i + test_string
            with StringIO(tester) as fh:
                card = next(mcnpy.input_parser.input_syntax_reader.read_data(fh))
                self.assertEqual(
                    mcnpy.input_parser.block_type.BlockType(i), card.block_type
                )

    def testCommentFormatInput(self):
        card = mcnpy.input_parser.mcnp_input.Comment(["foo", "bar"])
        output = card.format_for_mcnp_input((6.2, 0))
        answer = ["C foo", "C bar"]
        str_answer = """COMMENT:
foo
bar
"""
        self.assertEqual(str(card), str_answer)
        self.assertEqual(len(answer), len(output))
        for i, line in enumerate(output):
            self.assertEqual(answer[i], line)

    def testMessageFormatInput(self):
        card = mcnpy.input_parser.mcnp_input.Message(["foo", "bar"])
        answer = ["MESSAGE: foo", "bar", ""]
        str_answer = """MESSAGE:
foo
bar"""
        self.assertEqual(str_answer, str(card))
        output = card.format_for_mcnp_input((6.2, 0))
        self.assertEqual(len(answer), len(output))
        for i, line in enumerate(output):
            self.assertEqual(answer[i], line)

    def testTitleFormatInput(self):
        card = mcnpy.input_parser.mcnp_input.Title("foo")
        answer = ["foo"]
        str_answer = "TITLE: foo"
        self.assertEqual(str(card), str_answer)
        output = card.format_for_mcnp_input((6.2, 0))
        self.assertEqual(len(answer), len(output))
        for i, line in enumerate(output):
            self.assertEqual(answer[i], line)

    def testReadInput(self):
        generator = mcnpy.input_parser.input_syntax_reader.read_input_syntax(
            "tests/inputs/test.imcnp"
        )
        mcnp_in = mcnpy.input_parser.mcnp_input
        input_order = [mcnp_in.Message, mcnp_in.Title, mcnp_in.Comment]
        input_order += [mcnp_in.Card] * 4 + [mcnp_in.Comment]
        input_order += [mcnp_in.Card] * 3 + [mcnp_in.Comment]
        for i in range(2):
            input_order += [mcnp_in.Card, mcnp_in.Comment]
        input_order += [mcnp_in.Card, mcnp_in.Card, mcnp_in.Comment]
        input_order += [mcnp_in.Card] * 4
        for i, input in enumerate(generator):
            self.assertIsInstance(input, input_order[i])

    def testReadInputWithRead(self):
        generator = mcnpy.input_parser.input_syntax_reader.read_input_syntax(
            "tests/inputs/testRead.imcnp"
        )
        next(generator)  # skip title
        next(generator)  # skip read none
        card = next(generator)
        answer = ["1", "0", "-1"]
        for i, word in enumerate(card.words):
            self.assertEqual(answer[i], word)

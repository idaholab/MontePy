from io import StringIO
from unittest import TestCase

import mcnpy
from mcnpy.input_parser import input_syntax_reader


class TestSyntaxParsing(TestCase):
    def testMessageFinder(self):
        test_message = "this is a message"
        test_string = f"""message: {test_message}

test title
"""
        for tester, validator in [
            (test_string, test_message),
            (test_string.upper(), test_message.upper()),
        ]:
            with StringIO(tester) as fh:
                generator = input_syntax_reader.read_front_matters(fh)
                card = next(generator)
                self.assertIsInstance(card, mcnpy.input_parser.mcnp_input.Message)
                self.assertEqual(card.lines[0], validator)
                self.assertEqual(len(card.lines), 1)

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
                generator = input_syntax_reader.read_front_matters(fh)
                card = next(generator)
                self.assertIsInstance(card, mcnpy.input_parser.mcnp_input.Title)
                self.assertEqual(card.title, validator)

    def testCardFinder(self):
        test_string = """1 0 -1
     5"""
        for i in range(5):
            tester = " " * i + test_string
            with StringIO(tester) as fh:
                generator = input_syntax_reader.read_data(fh)
                card = next(generator)
                self.assertIsInstance(card, mcnpy.input_parser.mcnp_input.Card)
                answer = ["1", "0", "-1", "5"]
                self.assertEqual(len(answer), len(card.words))
                for j, word in enumerate(card.words):
                    self.assertEqual(word, answer[j])
                    self.assertEqual(
                        card.block_type, mcnpy.input_parser.block_type.BlockType.CELL
                    )

    def testCommentFinder(self):
        test_string = """c foo
c bar
c
c bop"""
        for i in range(5):
            tester = " " * i + test_string
            with StringIO(tester) as fh:
                card = next(input_syntax_reader.read_data(fh))
                self.assertIsInstance(card, mcnpy.input_parser.mcnp_input.Comment)
                self.assertEqual(len(card.lines), 4)
                self.assertEqual(card.lines[0], "foo")
                self.assertEqual(card.lines[1], "bar")
                self.assertEqual(card.lines[1], "bop")

    def testReadCardFinder(self):
        test_string = "read file=foo.imcnp "
        with StringIO(test_string) as fh:
            card = next(input_syntax_reader.read_data(fh))
            self.assertIsNone(card)  # the read card is hidden from the user

    def testBlockId(self):
        test_string = "1 0 -1"
        for i in range(3):
            tester = "\n" * i + test_string
            with StringIO(tester) as fh:
                for card in input_syntax_reader.read_data(fh):
                    pass
                self.assertEqual(
                    mcnpy.input_parser.block_type.BlockType(i), card.block_type
                )

    def testCommentFormatInput(self):
        in_strs = ["c foo", "c bar"]
        card = mcnpy.input_parser.mcnp_input.Comment(in_strs, ["foo", "bar"])
        output = card.format_for_mcnp_input((6.2, 0))
        output = card.format_for_mcnp_input((6, 2, 0))
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
        answer = ["MESSAGE: foo", "bar", ""]
        card = mcnpy.input_parser.mcnp_input.Message(answer, ["foo", "bar"])
        str_answer = """MESSAGE:
foo
bar
"""
        self.assertEqual(str_answer, str(card))
        output = card.format_for_mcnp_input((6, 2, 0))
        self.assertEqual(len(answer), len(output))
        for i, line in enumerate(output):
            self.assertEqual(answer[i], line)

    def testTitleFormatInput(self):
        card = mcnpy.input_parser.mcnp_input.Title(["foo"], "foo")
        answer = ["foo"]
        str_answer = "TITLE: foo"
        self.assertEqual(str(card), str_answer)
        output = card.format_for_mcnp_input((6, 2, 0))
        self.assertEqual(len(answer), len(output))
        for i, line in enumerate(output):
            self.assertEqual(answer[i], line)

    def testReadInput(self):
        generator = input_syntax_reader.read_input_syntax("tests/inputs/test.imcnp")
        mcnp_in = mcnpy.input_parser.mcnp_input
        input_order = [mcnp_in.Message, mcnp_in.Title, mcnp_in.Comment]
        input_order += [mcnp_in.Card] * 5 + [mcnp_in.Comment] * 2
        input_order += [mcnp_in.Card] * 3 + [mcnp_in.Comment]
        for i in range(2):
            input_order += [mcnp_in.Card, mcnp_in.Comment]
        input_order += [mcnp_in.Card, mcnp_in.Card, mcnp_in.Comment]
        input_order += [mcnp_in.Card] * 5
        for i, input in enumerate(generator):
            self.assertIsInstance(input, input_order[i])

    def testReadInputWithRead(self):
        generator = input_syntax_reader.read_input_syntax("tests/inputs/testRead.imcnp")
        next(generator)  # skip title
        next(generator)  # skip read none
        card = next(generator)
        answer = ["1", "0", "-1"]
        for i, word in enumerate(card.words):
            self.assertEqual(answer[i], word)

    def testReadInputWithVertMode(self):
        generator = input_syntax_reader.read_input_syntax(
            "tests/inputs/testVerticalMode.imcnp"
        )
        next(generator)
        next(generator)
        with self.assertRaises(mcnpy.errors.UnsupportedFeature):
            next(generator)

    def testCardStringRepr(self):
        in_str = "1 0 -1"
        card = mcnpy.input_parser.mcnp_input.Card(
            [in_str], mcnpy.input_parser.block_type.BlockType.CELL
        )
        self.assertEqual(str(card), "CARD: BlockType.CELL: ['1', '0', '-1']")

    def testShortcutExpansion(self):
        tests = {
            ("M", "1", "3M", "2r"): ["M", "1", "3", "3", "3"],
            ("M", "0.01", "2ILOG", "10"): ["M", "0.01", "0.1", "1", "10"],
            ("M", "1", "3M", "I", "4"): ["M", "1", "3", "3.5", "4"],
            ("M", "1", "3M", "3M"): ["M", "1", "3", "9"],
            ("M", "1", "2R", "2I", "2.5"): ["M", "1", "1", "1", "1.5", "2", "2.5"],
            ("M", "1", "R", "2m"): ["M", "1", "1", "2"],
            ("M", "1", "R", "R"): ["M", "1", "1", "1"],
            ("M", "1", "2i", "4", "3m"): ["M", "1", "2", "3", "4", "12"],
            ("M", "1", "2i", "4", "2i", "10"): [
                "M",
                "1",
                "2",
                "3",
                "4",
                "6",
                "8",
                "10",
            ],
            (
                "M",
                "1",
                "2j",
                "4",
            ): ["M", "1", None, None, "4"],
        }
        invalid = [
            ("M", "3J", "4R"),
            ("M", "1", "4I", "3M"),
            ("M", "1", "4I", "J"),
            ("M", "1", "2Ilog", "J"),
            ("M", "3J", "2M"),
        ]

        parser = mcnpy.input_parser.mcnp_input.parse_card_shortcuts
        for test, answer in tests.items():
            parsed = parser(list(test))
            self.assertEqual(parsed, answer)
        for test in invalid:
            with self.assertRaises(mcnpy.errors.MalformedInputError):
                parser(list(test))

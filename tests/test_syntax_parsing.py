from io import StringIO
from unittest import TestCase

import mcnpy
from mcnpy.input_parser import input_syntax_reader
from mcnpy.input_parser.mcnp_input import Input, Jump, Message, ReadInput, Title
from mcnpy.input_parser.block_type import BlockType
from mcnpy.particle import Particle


class TestSyntaxParsing(TestCase):
    def testCardInit(self):
        with self.assertRaises(TypeError):
            Input("5", BlockType.CELL)
        with self.assertRaises(TypeError):
            Input([5], BlockType.CELL)
        with self.assertRaises(TypeError):
            Input(["5"], "5")

    def testMessageInit(self):
        with self.assertRaises(TypeError):
            Message(["hi"], "5")
        with self.assertRaises(TypeError):
            Message(["hi"], [5])

    def testTitleInit(self):
        with self.assertRaises(TypeError):
            Title(["hi"], 5)

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
                generator = input_syntax_reader.read_front_matters(fh, (6, 2, 0))
                card = next(generator)
                self.assertIsInstance(card, mcnpy.input_parser.mcnp_input.Message)
                self.assertEqual(card.lines[0], validator)
                self.assertEqual(len(card.lines), 1)

    def testReadCardStr(self):
        card = ReadInput(["Read file=hi.imcnp"], BlockType.CELL)
        self.assertEqual(str(card), "READ INPUT: Block_Type: BlockType.CELL")
        self.assertEqual(
            repr(card), "READ INPUT: BlockType.CELL: ['Read', 'file=hi.imcnp']"
        )

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
                generator = input_syntax_reader.read_front_matters(fh, (6, 2, 0))
                card = next(generator)
                self.assertIsInstance(card, mcnpy.input_parser.mcnp_input.Title)
                self.assertEqual(card.title, validator)

    def testCardFinder(self):
        test_string = """1 0 -1
     5"""
        for i in range(5):
            tester = " " * i + test_string
            with StringIO(tester) as fh:
                generator = input_syntax_reader.read_data(fh, (6, 2, 0))
                card = next(generator)
                self.assertIsInstance(card, mcnpy.input_parser.mcnp_input.Input)
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
c bop
 c
"""
        for i in range(5):
            tester = " " * i + test_string
            with StringIO(tester) as fh:
                card = next(input_syntax_reader.read_data(fh, (6, 2, 0)))
                self.assertIsInstance(card, mcnpy.input_parser.mcnp_input.Comment)
                self.assertEqual(len(card.lines), 5)
                self.assertEqual(card.lines[0], "foo")
                self.assertEqual(card.lines[1], "bar")
                self.assertEqual(card.lines[3], "bop")

    def testReadCardFinder(self):
        test_string = "read file=foo.imcnp "
        with StringIO(test_string) as fh:
            card = next(input_syntax_reader.read_data(fh, (6, 2, 0)))
            self.assertIsNone(card)  # the read input is hidden from the user

    def testBlockId(self):
        test_string = "1 0 -1"
        for i in range(3):
            tester = "\n" * i + test_string
            with StringIO(tester) as fh:
                for card in input_syntax_reader.read_data(fh, (6, 2, 0)):
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
        self.assertEqual(repr(card), str_answer)
        self.assertEqual("COMMENT: 2 lines", str(card))
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
        self.assertEqual(str_answer, repr(card))
        self.assertEqual("MESSAGE: 2 lines", str(card))
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
        # TODO ensure comments are properly glued to right input
        generator = input_syntax_reader.read_input_syntax("tests/inputs/test.imcnp")
        mcnp_in = mcnpy.input_parser.mcnp_input
        input_order = [mcnp_in.Message, mcnp_in.Title]
        input_order += [mcnp_in.Input] * 17
        for i, input in enumerate(generator):
            print(input.input_lines)
            print(input_order[i])
            self.assertIsInstance(input, input_order[i])

    def testReadInputWithRead(self):
        generator = input_syntax_reader.read_input_syntax("tests/inputs/testRead.imcnp")
        next(generator)  # skip title
        next(generator)  # skip read none
        card = next(generator)
        answer = ["1 0 -1"]
        self.assertEqual(answer, card.input_lines)

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
        card = mcnpy.input_parser.mcnp_input.Input(
            [in_str], mcnpy.input_parser.block_type.BlockType.CELL
        )
        self.assertEqual(str(card), "INPUT: BlockType.CELL")
        self.assertEqual(repr(card), "INPUT: BlockType.CELL: ['1', '0', '-1']")

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
            ("M", "1", "i", "3"): ["M", "1", "2", "3"],
            ("M", "1", "ilog", "100"): ["M", "1", "10", "100"],
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
            ): ["M", "1", mcnpy.Jump(), mcnpy.Jump(), "4"],
        }
        invalid = [
            ("M", "3J", "4R"),
            ("M", "1", "4I", "3M"),
            ("M", "1", "4I", "J"),
            ("M", "1", "2Ilog", "J"),
            ("M", "3J", "2M"),
            ("M", "10", "M"),
            (
                "M5",
                "2R",
            ),
        ]

        parser = mcnpy.input_parser.mcnp_input.parse_input_shortcuts
        for test, answer in tests.items():
            print(test)
            parsed = parser(list(test))
            self.assertEqual(parsed, answer)
        for test in invalid:
            print(test)
            with self.assertRaises(mcnpy.errors.MalformedInputError):
                parser(list(test))

    def testDataInputNameParsing(self):
        tests = {
            "kcOde": {"prefix": "kcode", "number": None, "classifier": None},
            "M300": {"prefix": "m", "number": 300, "classifier": None},
            "IMP:N,P,E": {
                "prefix": "imp",
                "number": None,
                "classifier": [Particle.NEUTRON, Particle.PHOTON, Particle.ELECTRON],
            },
            "F1004:n,P": {
                "prefix": "f",
                "number": 1004,
                "classifier": [Particle.NEUTRON, Particle.PHOTON],
            },
        }
        for in_str, answer in tests.items():
            # Testing parsing the names
            card = mcnpy.input_parser.mcnp_input.Input(
                [in_str], mcnpy.input_parser.block_type.BlockType.DATA
            )
            data_input = mcnpy.data_inputs.data_input.DataInput(card)
            self.assertEqual(data_input.prefix, answer["prefix"])
            self.assertEqual(data_input._input_number, answer["number"])
            self.assertEqual(data_input.particle_classifiers, answer["classifier"])

    def testDataInputNameEnforcement(self):
        tests = {
            "kcOde5": {"prefix": "kcode", "number": False, "classifier": 0},
            "M-300": {"prefix": "m", "number": True, "classifier": 0},
            "M": {"prefix": "m", "number": True, "classifier": 0},
            "f4m": {"prefix": "fm", "number": True, "classifier": 1},
            "IMP:N,P,E": {"prefix": "imp", "number": False, "classifier": 0},
            "IMP": {"prefix": "imp", "number": False, "classifier": 2},
        }
        valid = {
            "IMP:N,P,E": {"prefix": "imp", "number": False, "classifier": 2},
            "F1004:n,P": {"prefix": "f", "number": True, "classifier": 1},
        }
        # tests invalid names
        for in_str, answer in tests.items():
            with self.assertRaises(mcnpy.errors.MalformedInputError):
                card = mcnpy.input_parser.mcnp_input.Input(
                    [in_str], mcnpy.input_parser.block_type.BlockType.DATA
                )
                card = DataInputTestFixture(card)
                card._class_prefix = answer["prefix"]
                card._has_number = answer["number"]
                card._has_classifier = answer["classifier"]
                card._DataInputAbstract__split_name()

        # tests valid names
        for in_str, answer in valid.items():
            card = mcnpy.input_parser.mcnp_input.Input(
                [in_str], mcnpy.input_parser.block_type.BlockType.DATA
            )
            card = DataInputTestFixture(card)
            card._class_prefix = answer["prefix"]
            card._has_number = answer["number"]
            card._has_classifier = answer["classifier"]
            card._DataInputAbstract__split_name()

    def test_get_line_numbers(self):
        answers = {
            (5, 1, 60): 80,
            (6, 1, 0): 80,
            (6, 2, 0): 128,
            (6, 2, 3): 128,
            (6, 3, 0): 128,
            (7, 4, 0): 128,
        }
        for version, answer in answers.items():
            self.assertEqual(
                answer, mcnpy.input_parser.constants.get_max_line_length(version)
            )
        with self.assertRaises(mcnpy.errors.UnsupportedFeature):
            mcnpy.input_parser.constants.get_max_line_length((5, 1, 38))

    def test_jump(self):
        jump = Jump()
        self.assertEqual("J", str(jump))
        jump2 = Jump()
        self.assertEqual(jump, jump2)
        with self.assertRaises(TypeError):
            bool(jump)

    def test_jump_and_a_hop(self):
        jump = Jump()
        # first you need to hop
        self.assertEqual("j", jump.lower())
        # then you need to skip
        self.assertEqual("Jump", jump.title())
        # before you can jump
        self.assertEqual("J", jump.upper())


class DataInputTestFixture(mcnpy.data_inputs.data_input.DataInputAbstract):
    def __init__(self, input_card=None, comment=None):
        """
        :param input_card: the Card object representing this data input
        :type input_card: Input
        :param comment: The Comment that may proceed this
        :type comment: Comment
        """
        self._class_prefix = None
        self._has_number = None
        self._has_classifier = None
        super().__init__(input_card, comment)

    @property
    def class_prefix(self):
        return self._class_prefix

    @property
    def has_number(self):
        return self._has_number

    @property
    def has_classifier(self):
        return self._has_classifier

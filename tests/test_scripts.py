import itertools
from unittest import TestCase
from tests import constants
import os
import subprocess


class TestChangeAsciiScript(TestCase):
    @classmethod
    def setUpClass(cls):
        new_files = {}
        for input_file in constants.BAD_ENCODING_FILES:
            new_files[input_file] = {}
            for flag in {"-w", "-d"}:
                new_file = f"{input_file}{flag}.imcnp"
                cls.run_script(
                    [flag, os.path.join("tests", "inputs", input_file), new_file]
                )
                new_files[input_file][flag] = new_file
        cls.files = new_files

    @classmethod
    def tearDownClass(cls):
        for group in cls.files.values():
            for file_name in group.values():
                try:
                    os.remove(file_name)
                except FileNotFoundError:
                    pass

    @staticmethod
    def run_script(args):
        return subprocess.run(
            ["python", os.path.join("montepy", "_scripts", "change_to_ascii.py")] + args
        )

    def test_delete_bad(self):
        for in_file in self.files:
            with (
                open(os.path.join("tests", "inputs", in_file), "rb") as in_fh,
                open(self.files[in_file]["-d"], "rb") as out_fh,
            ):
                for in_line, out_line in zip(in_fh, out_fh):
                    try:
                        in_line.decode("ascii")
                        self.assertEqual(in_line, out_line)
                    except UnicodeError:
                        new_line = []
                        for char in in_line:
                            if char <= 128:
                                new_line.append(chr(char))
                        self.assertEqual("".join(new_line), out_line.decode("ascii"))

    def test_whitespace_bad(self):
        for in_file in self.files:
            with (
                open(os.path.join("tests", "inputs", in_file), "rb") as in_fh,
                open(self.files[in_file]["-w"], "rb") as out_fh,
            ):
                for in_line, out_line in zip(in_fh, out_fh):
                    try:
                        in_line.decode("ascii")
                        self.assertEqual(in_line, out_line)
                    except UnicodeError:
                        new_line = []
                        try:
                            # try to change to utf-8
                            for char in in_line.decode():
                                if ord(char) <= 128:
                                    new_line.append(char)
                                else:
                                    new_line.append(" ")
                        except UnicodeError:
                            # try to go bit by bit
                            for char in in_line:
                                if char <= 128:
                                    new_line.append(chr(char))
                                else:
                                    new_line.append(" ")
                        self.assertEqual("".join(new_line), out_line.decode("ascii"))

    def test_bad_arguments(self):
        ret_code = self.run_script(
            [
                "-w",
                "-d",
                os.path.join("tests", "inputs", "bad_encode.imcnp", "foo.imcnp"),
            ]
        )
        self.assertNotEqual(ret_code.returncode, 0)

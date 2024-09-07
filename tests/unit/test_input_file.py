# Copyright 2024, Battelle Energy Alliance, LLC All Rights Reserved.
import os
import unittest
import pytest

import montepy
from montepy.input_parser.input_file import MCNP_InputFile


class testInputFileWrapper(unittest.TestCase):
    """
    Note: file lineno is 1-indexed as is tradition in file editors.
    """

    def setUp(self):
        self._file_name = os.path.join("tests", "inputs", "test.imcnp")
        self._file = MCNP_InputFile(self._file_name)

    def test_init(self):
        self.assertEqual(self._file.name, self._file_name)
        parent = os.path.join("tests", "inputs", "testRead.imcnp")
        test_file = MCNP_InputFile(
            os.path.join("tests", "inputs", "testReadTarget.imcnp"), parent
        )
        self.assertEqual(test_file.parent_file, parent)

    def test_open_iter(self):
        with self._file.open("r") as fh:
            for i, _ in enumerate(fh):
                self.assertEqual(self._file.lineno, i + 1)
        # test proper exiting
        self.assertIsNone(self._file._fh)
        try:
            with self._file.open("r") as fh:
                1 / 0
        except ZeroDivisionError:
            pass
        # test proper exiting with error
        self.assertIsNone(self._file._fh)

    def test_str(self):
        self.assertEqual(str(self._file), self._file_name)

    def test_read(self):
        with self._file.open("r") as fh:
            contents = fh.read()
        self.assertEqual(self._file.lineno, contents.count("\n") + 1)

    def test_readline(self):
        with self._file.open("r") as fh:
            i = 0
            line = "hi"
            while line:
                line = fh.readline()
                print(line.encode())
                if line:
                    i += 1
                self.assertEqual(self._file.lineno, i + 1)

    def test_write(self):
        out = "bar.imcnp"
        try:
            test = MCNP_InputFile(out)
            with test.open("w") as fh:
                fh.write("hi\nbar\n")
                self.assertEqual(test.lineno, 3)
            with test.open("r") as fh:
                contents = fh.read()
                self.assertIn("hi", contents)
        finally:
            if os.path.exists(out):
                os.remove(out)


def _write_file(out_file):
    with open(out_file, "w") as fh:
        fh.write("")


@pytest.mark.parametrize(
    "writer,exception, clearer",
    (
        (_write_file, FileExistsError, lambda out_file: os.remove(out_file)),
        (
            lambda out_file: os.makedirs(out_file),
            IsADirectoryError,
            lambda out_file: os.rmdir(out_file),
        ),
    ),
)
def test_write_guardrails(writer, exception, clearer):
    out_file = "foo_bar.imcnp"
    try:
        writer(out_file)
        with pytest.raises(exception):
            test = MCNP_InputFile(out_file)
            with test.open("w") as _:
                pass
    finally:
        try:
            clearer(out_file)
        except FileNotFoundError:
            pass

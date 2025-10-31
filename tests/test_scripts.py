import itertools
import pytest
from tests import constants
import os
import subprocess


def run_script(args):
    return subprocess.run(
        ["python", os.path.join("montepy", "_scripts", "change_to_ascii.py")] + args
    )


@pytest.fixture(scope="module")
def ascii_files():
    new_files = {}
    for input_file in constants.BAD_ENCODING_FILES:
        new_files[input_file] = {}
        for flag in {"-w", "-d"}:
            new_file = f"{input_file}{flag}.imcnp"
            run_script([flag, os.path.join("tests", "inputs", input_file), new_file])
            new_files[input_file][flag] = new_file
    yield new_files
    for group in new_files.values():
        for file_name in group.values():
            try:
                os.remove(file_name)
            except FileNotFoundError:
                pass


@pytest.mark.parametrize("flag", ["-d", "-w"])
def test_ascii_script(ascii_files, flag):
    for in_file in ascii_files:
        with (
            open(os.path.join("tests", "inputs", in_file), "rb") as in_fh,
            open(ascii_files[in_file][flag], "rb") as out_fh,
        ):
            for in_line, out_line in zip(in_fh, out_fh):
                try:
                    in_line.decode("ascii")
                    assert in_line == out_line
                except UnicodeError:
                    new_line = []
                    if flag == "-w":
                        try:
                            for char in in_line.decode():
                                if ord(char) <= 128:
                                    new_line.append(char)
                                else:
                                    new_line.append(" ")
                        except UnicodeError:
                            for char in in_line:
                                if char <= 128:
                                    new_line.append(chr(char))
                                else:
                                    new_line.append(" ")
                    else:
                        for char in in_line:
                            if char <= 128:
                                new_line.append(chr(char))
                    assert "".join(new_line) == out_line.decode("ascii")

    def test_bad_arguments(self):
        ret_code = self.run_script(
            [
                "-w",
                "-d",
                os.path.join("tests", "inputs", "bad_encode.imcnp", "foo.imcnp"),
            ]
        )
        self.assertNotEqual(ret_code.returncode, 0)

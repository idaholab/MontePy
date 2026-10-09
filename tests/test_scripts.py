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
                                if ord(char) <= 127:
                                    new_line.append(char)
                                else:
                                    new_line.append(" ")
                        except UnicodeError:
                            for char in in_line:
                                if char <= 127:
                                    new_line.append(chr(char))
                                else:
                                    new_line.append(" ")
                    else:
                        for char in in_line:
                            if char <= 127:
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


@pytest.mark.parametrize("flag", ["-d", "-w"])
def test_ascii_script_strips_u0080(tmp_path, flag):
    """U+0080 is not ASCII, so it must be removed rather than crash the run.

    ASCII tops out at 0x7F. A boundary of ``> 128`` kept 0x80 and the
    re-encode then raised UnicodeEncodeError out of the script.
    """
    in_file = tmp_path / "u0080.imcnp"
    out_file = tmp_path / "u0080.out.imcnp"
    in_file.write_bytes("bad \u0080 char\n".encode("utf8"))

    result = run_script([flag, str(in_file), str(out_file)])

    assert result.returncode == 0
    written = out_file.read_bytes()
    written.decode("ascii")  # must not raise
    assert b"\x80" not in written
    assert written == (b"bad   char\n" if flag == "-w" else b"bad  char\n")

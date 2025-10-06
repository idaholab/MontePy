import os
import pytest
import montepy
from montepy.input_parser.input_file import MCNP_InputFile

import os
import pytest
import montepy
from montepy.input_parser.input_file import MCNP_InputFile


def _write_file(out_file):
    with open(out_file, "w") as fh:
        fh.write("")


def test_init():
    file_name = os.path.join("tests", "inputs", "test.imcnp")
    file_obj = MCNP_InputFile(file_name)
    assert file_obj.name == file_name
    parent = os.path.join("tests", "inputs", "testRead.imcnp")
    test_file = MCNP_InputFile(
        os.path.join("tests", "inputs", "testReadTarget.imcnp"), parent
    )
    assert test_file.parent_file == parent


def test_open_iter():
    file_name = os.path.join("tests", "inputs", "test.imcnp")
    file_obj = MCNP_InputFile(file_name)
    with file_obj.open("r") as fh:
        for i, _ in enumerate(fh):
            assert file_obj.lineno == i + 1
    # test proper exiting
    assert file_obj._fh is None
    try:
        with file_obj.open("r") as fh:
            1 / 0
    except ZeroDivisionError:
        pass
    # test proper exiting with error
    assert file_obj._fh is None
    assert str(file_obj) == file_name


def test_read():
    file_name = os.path.join("tests", "inputs", "test.imcnp")
    file_obj = MCNP_InputFile(file_name)
    with file_obj.open("r") as fh:
        contents = fh.read()
    assert file_obj.lineno == contents.count("\n") + 1


def test_readline():
    file_name = os.path.join("tests", "inputs", "test.imcnp")
    file_obj = MCNP_InputFile(file_name)
    with file_obj.open("r") as fh:
        i = 0
        line = "hi"
        while line:
            line = fh.readline()
            print(line.encode())
            if line:
                i += 1
            assert file_obj.lineno == i + 1

    # test proper exiting with error
    assert file_obj._fh is None


def test_write():
    out = "bar.imcnp"
    try:
        test = MCNP_InputFile(out)
        with test.open("w") as fh:
            fh.write("hi\nbar\n")
            assert test.lineno == 3
        with test.open("r") as fh:
            contents = fh.read()
            assert "hi" in contents
    finally:
        if os.path.exists(out):
            os.remove(out)


@pytest.mark.parametrize(
    "writer,exception,clearer",
    [
        (_write_file, FileExistsError, lambda out_file: os.remove(out_file)),
        (
            lambda out_file: os.makedirs(out_file),
            IsADirectoryError,
            lambda out_file: os.rmdir(out_file),
        ),
    ],
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

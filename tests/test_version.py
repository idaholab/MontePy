import importlib
import os
import subprocess
import sys
from pathlib import Path


def test_version():
    version_file = Path("montepy") / "_version.py"
    if not version_file.exists():
        subprocess.run(
            ["python", "-m", "setuptools_scm", "--force-write-version-files"]
        )
    assert os.path.exists(os.path.join("montepy", "_version.py"))
    # Test without version.py
    try:
        # try without setuptools_scm
        old_file = os.path.join("montepy", "_version.py")
        new_file = os.path.join("montepy", "_version.bak")
        os.rename(old_file, new_file)
        # clear out previous imports
        to_delete = set()
        for mod in sys.modules:
            for bad_mod in ["setuptools_scm", "montepy"]:
                if bad_mod in mod:
                    to_delete.add(mod)
        for mod in to_delete:
            del sys.modules[mod]
        sys.modules["setuptools_scm"] = None
        import montepy

        assert montepy.__version__ == "Undefined"
        # try with setuptools_scm
        del sys.modules["setuptools_scm"]
        importlib.reload(montepy)
        print(f"From setuptools_scm: {montepy.__version__}")
        assert len(montepy.__version__.split(".")) >= 3
    finally:
        os.rename(new_file, old_file)
    # do base with _version
    importlib.reload(montepy)
    print(f"From _version.py: {montepy.__version__}")
    assert len(montepy.__version__.split(".")) >= 3

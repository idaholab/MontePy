import importlib
import os
import subprocess
import sys
from pathlib import Path


def test_version():
    import montepy
    version_file = Path("montepy") / "_version.py"
    if not version_file.exists():
        subprocess.run(
            ["python", "-m", "setuptools_scm", "--force-write-version-files"],
            check=False
        )
    assert os.path.exists(os.path.join("montepy", "_version.py"))
    
    # Test with _version.py file
    importlib.reload(montepy)
    print(f"From _version.py: {montepy.__version__}")
    assert len(montepy.__version__.split(".")) >= 3
    
    # Test what happens when setuptools_scm is not available
    # This simulates the case where setuptools_scm raises an error
    old_file = os.path.join("montepy", "_version.py")
    new_file = os.path.join("montepy", "_version.bak")
    
    try:
        os.rename(old_file, new_file)
        
        # clear out previous imports
        to_delete = set()
        for mod in sys.modules:
            for bad_mod in ["setuptools_scm", "montepy"]:
                if bad_mod in mod:
                    to_delete.add(mod)
        for mod in to_delete:
            del sys.modules[mod]
        
        # Import montepy again - it should handle missing _version.py gracefully
        import montepy
        if montepy.__version__ == "Undefined":
            print("setuptools_scm not available, skipping version test without _version.py")
        else:
            # This should not happen in normal circumstances
            assert len(montepy.__version__.split(".")) >= 3
    finally:
        if os.path.exists(new_file):
            os.rename(new_file, old_file)
        # reload to get back the proper version
        importlib.reload(montepy)

import glob
import os
import sys
import warnings

ignored = {
    "__pycache__",
    "_scripts",
    "_version.py",
    "__main__.py",
    "_cell_data_control.py",
    "_singleton.py",
}

base = os.path.join("..", "..")


def crawl_path(rel_path):
    missing = False
    for f in os.listdir(os.path.join(base, rel_path)):
        f_name = os.path.join(rel_path, f)
        if f in ignored:
            continue
        if f_name in ("montepy/__init__.py", "montepy/_check_value.py"):
            continue
        if os.path.isdir(os.path.join(base, f_name)):
            crawl_path(f_name)
        elif os.path.isfile(os.path.join(base, f_name)) and ".py" in f:
            if f == "__init__.py":
                path = f_name.replace("/", ".").replace(".__init__.py", ".rst")
            else:
                path = f_name.replace("/", ".").replace(".py", ".rst")
            if not os.path.exists(os.path.join("api", path)):
                missing = True
                warnings.warn(
                    f"Missing sphinx documentation for {os.path.join(rel_path, f)}"
                )
    return missing


missing = crawl_path("montepy")
if missing:
    sys.exit(314)

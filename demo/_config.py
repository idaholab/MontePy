from IPython.display import IFrame as _iframe
import sys

X_RES = 1200
Y_RES = 800


def IFrame(src, width=X_RES, height=Y_RES, extras=None, **kwargs):
    return _iframe(src, width, height, extras, **kwargs)


def install_montepy():
    if "pyodide" in sys.modules:
        import piplite
        import pyodide

        async def _install():
            await piplite.install("montepy")

        pyodide.webloop.run_sync(_install())

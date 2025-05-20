from IPython.display import IFrame as _iframe

X_RES = 1200
Y_RES = 800


def IFrame(src, width=X_RES, height=Y_RES, extras=None, **kwargs):
    return _iframe(src, width, height, extras, **kwargs)

from importlib.util import find_spec as _find_spec

if _find_spec("openmc") is None:
	raise ImportError(
		f"'{__name__}' requires the optional dependency 'openmc', which is not installed. "
		"Install it with 'conda install -c conda-forge openmc' "
		"or see https://docs.openmc.org/en/stable/quickinstall.html",
	)

import montepy.carlo.material_objects

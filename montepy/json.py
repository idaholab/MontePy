import inspect
import json
from enum import Enum


class MontepyJSONEncode(json.JSONEncoder):
    def default(self, o):
        try:
            print(o)
        except AttributeError:
            pass
        data = o.__getstate__()
        print(data)
        new_data = {}
        if not isinstance(data, dict):
            return data
        for key, value in data.items():
            if isinstance(
                value, (dict, list, tuple, str, int, float, bool, Enum, type(None))
            ):
                new_data[key] = value
            elif inspect.isclass(value):
                new_data[key] = str(value)
            else:
                new_data[key] = self.default(value)
        return new_data

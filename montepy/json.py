import inspect
import json
import montepy
from enum import Enum


class MontepyJSONEncode(json.JSONEncoder):
    def default(self, o):
        try:
            data = o.serialize()
        except AttributeError:
            try:
                data = o.__getstate__()
            except TypeError:
                data = o.__dict__
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


class MontepyJSONDecode(json.JSONDecoder):
    def decode(self, s):
        data = super().decode(s)

        return montepy.input_parser.syntax_node.SyntaxNode.deserialize(
            list(data.values())[-1]
        )

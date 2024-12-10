import montepy
import json

json_encoder = montepy.json.MontepyJSONEncode()
cell = montepy.Cell("1 0 -2 imp:n=1 $hi")
print(json.dumps(cell, cls=montepy.json.MontepyJSONEncode))

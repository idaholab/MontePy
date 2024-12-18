import montepy
import json
import pickle

cell = montepy.Cell("1 0 -2 imp:n=1 $hi")
payload = json.dumps(cell, cls=montepy.json.MontepyJSONEncode, indent=4)
print(payload)
new_cell = json.loads(payload, cls = montepy.json.MontepyJSONDecode)
print(new_cell)

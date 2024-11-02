import montepy
import json

json_encoder = montepy.json.MontepyJSONEncode()
cell = montepy.Cell()
#print(json.dumps(cell, default = lambda o: dict(o.__dict__)))
print(json_encoder.encode(cell))

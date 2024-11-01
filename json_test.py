import montepy

json_encoder = montepy.json.MontepyJSONEncode()
cell = montepy.Cell()
print(json_encoder.encode(cell))

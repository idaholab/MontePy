import itertools
import mcnpy

ReadInput = mcnpy.input_parser.mcnp_input.ReadInput

input = ReadInput(
    ["read $hi", "    file=foo.imcnp encode=hi"],
    mcnpy.input_parser.block_type.BlockType.CELL,
)

print(repr(input))

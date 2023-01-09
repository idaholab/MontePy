import itertools
import mcnpy

Input = mcnpy.input_parser.mcnp_input.Input

input = Input(
    ["read $hi", "    file=foo.imcnp encode=hi"],
    mcnpy.input_parser.block_type.BlockType.CELL,
)
lexer = mcnpy.input_parser.tokens.MCNP_Lexer()
parser = mcnpy.input_parser.read_parser.ReadParser()
print(parser.parse(lexer.tokenize(input.input_text)))

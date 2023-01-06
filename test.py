import itertools
import mcnpy

Input = mcnpy.input_parser.mcnp_input.Input

""
input = Input(
    ["5 CZ 5.0 3.0"],
    mcnpy.input_parser.block_type.BlockType.CELL,
)
lexer = mcnpy.input_parser.tokens.MCNP_Lexer()
parser = mcnpy.input_parser.surface_parser.SurfaceParser()
for token in lexer.tokenize(input.input_text):
    print(token)
print(parser.parse(lexer.tokenize(input.input_text)))

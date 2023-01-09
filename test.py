import itertools
import mcnpy

Input = mcnpy.input_parser.mcnp_input.Input

""
input = Input(
    ["m1 1001.80c 0.6 8016.80c 0.4 plib=80c"],
    mcnpy.input_parser.block_type.BlockType.CELL,
)
lexer = mcnpy.input_parser.tokens.MCNP_Lexer()
parser = mcnpy.input_parser.material_parser.MaterialParser()
for token in lexer.tokenize(input.input_text):
    print(token)
print(parser.parse(lexer.tokenize(input.input_text)))

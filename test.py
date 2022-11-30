import mcnpy

Input = mcnpy.input_parser.mcnp_input.Input
tokens = mcnpy.input_parser.tokens

input = Input(["line 1", "line  2"], mcnpy.input_parser.block_type.BlockType.CELL)

for token in tokens.tokenize(input):
    print(token.original_input)

import mcnpy

Input = mcnpy.input_parser.mcnp_input.Input
tokens = mcnpy.input_parser.tokens

input = Input(
    [
        "line 1",
        "line  2",
        "     line 3 $ hi",
        "C this is a comment",
        "cnot comment",
        "c",
    ],
    mcnpy.input_parser.block_type.BlockType.CELL,
)
print(input.input_lines)
for token in tokens.tokenize(input):
    print(type(token), token.original_input.encode())

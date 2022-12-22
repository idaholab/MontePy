import itertools
import mcnpy

Input = mcnpy.input_parser.mcnp_input.Input

""
input = Input(
    [
        "5  $foo 10 -0.5",
        "     1 0.5e-10 ",
        "C this is a comment",
    ],
    mcnpy.input_parser.block_type.BlockType.CELL,
)
for token in mcnpy.input_parser.tokens.MCNP_Lexer().tokenize(
    "\n".join(input.input_lines)
):
    print(token)

import itertools
import mcnpy

Input = mcnpy.input_parser.mcnp_input.Input

""
input = Input(
    [
         "5  $foo 10 -0.5",
        "     1 -0.5 -1 2:3 #(4 5)",
        #"-1 3 "
        # "C this is a comment",
    ],
    mcnpy.input_parser.block_type.BlockType.CELL,
)
lexer = mcnpy.input_parser.tokens.MCNP_Lexer()
parser = mcnpy.input_parser.node_parser.CellParser()
for token in lexer.tokenize(input.input_text):
    print(token)
print(parser.parse(lexer.tokenize(input.input_text)))

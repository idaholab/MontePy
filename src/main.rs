use chumsky::prelude::*;
use monteparser::parser::input_parser;

fn main() {
    let parser = input_parser();
    let input = "1 0 2 &
-5 6 
     imp:n=1 
";
    parser.parse(input);
}

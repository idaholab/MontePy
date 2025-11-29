
pub mod parser {
    use chumsky::prelude::*;
    enum McnpInput<'src> {
        Input(Vec<&'src str>),
    }
    
    pub fn input_parser<'src>() -> impl Parser<'src, &'src str, McnpInput<'src>> {
        none_of("&\n").repeated().then(
            choice((
                    just("\n      "),
                    just("&\n")
            ))).repeated().collect().to(McnpInput::Input)
    }
}

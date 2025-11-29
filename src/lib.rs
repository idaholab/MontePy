
pub mod parser {
    use chumsky::prelude::*;
    enum McnpInput<'src> {
        Input(Vec<&'src str>),
    }
    
    pub fn input_parser<'src>() -> impl Parser<'src, &'src str, char> {
        choice((
                just("\n     "),
                just("&\n"),
                any().repeated().at_least(1).collect::<String>()
        )).repeated().collect()
    }
}

use monteparser::syntax_node::syntax_node::Node;

fn main() {
    use monteparser::syntax_node::syntax_node::ValueNodeRust;
    let mut node = ValueNodeRust::new("123".to_string()).unwrap();
    node.convert_to_int().unwrap();
    println!("{}", node.format());
}

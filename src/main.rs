use monteparser::syntax_node::SyntaxNode::Node;

fn main() {
    use monteparser::syntax_node::SyntaxNode::ValueNodeRust;
    let mut node = ValueNodeRust::new(&"123");
    node.convert_to_int();
    println!("{}", node.format());
}

use pyo3::prelude::*;

#[pymodule]
pub mod SyntaxNode {

    use pyo3::prelude::*;
    use std::collections::HashMap;
    pub enum SyntaxNodeEnum {
        SyntaxNodeRust,
        ValueNodeRust,
    }

    pub trait Node {
        fn format(self) -> String;
    }

    #[pyclass(subclass)]
    pub struct SyntaxNodeRust {
        nodes: HashMap<String, SyntaxNodeEnum>,
    }

    enum ValueType {
        Int(u32),
        Float(f64),
        Str(String),
    }

    #[pyclass(subclass,extends=SyntaxNodeRust)]
    pub struct ValueNodeRust {
        _value: ValueType,
        _token: String,
        _og_value: ValueType,
    }

    #[pymethods]
    impl ValueNodeRust {
        #[new]
        pub fn new(token: String) -> PyResult<Self> {
            Ok(Self {
                _value: ValueType::Str(token.to_string()),
                _token: token.to_string(),
                _og_value: ValueType::Str(token.to_string()),
            })
        }
        pub fn convert_to_int(&mut self) -> PyResult<()> {
            if let ValueType::Str(str_value) = &self._value {
                let int_value = str_value.parse::<u32>().unwrap();
                self._value = ValueType::Int(int_value);
            }
            Ok(())
        }
    }

    impl Node for ValueNodeRust {
        fn format(self) -> String {
            match self._value {
                ValueType::Str(str_value) => return str_value.to_string(),
                ValueType::Int(int_value) => return format!("{}", int_value),
                ValueType::Float(float_value) => return format!("{}", float_value),
            }
        }
    }
}

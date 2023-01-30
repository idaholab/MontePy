from abc import ABC, abstractmethod
from mcnpy import input_parser
from mcnpy.input_parser.shortcuts import Shortcuts
from mcnpy.geometry_operators import Operator
from mcnpy.utilities import fortran_float
import re


class SyntaxNodeBase(ABC):
    def __init__(self, name):
        self._name = name
        self._nodes = []

    def append(self, node):
        # todo type checking
        self._nodes.append(node)

    @property
    def nodes(self):
        return self._nodes

    def has_leaves(self):
        if any([isinstance(x, ValueNode) for x in self.nodes]):
            return True
        for node in self.nodes:
            if isinstance(node, SyntaxNodeBase):
                if node.has_leaves:
                    return True
        return False

    def get_last_leaf_parent(self):
        for node in self.nodes[::-1]:
            if isinstance(node, Token):
                return self
            if node.has_leaves:
                return node.get_last_leaf_parent()

    def __len__(self):
        return len(self.nodes)

    def print_nodes(self):
        ret = []
        for node in self._nodes:
            ret.append(node.print_nodes())
        return f"N: {self._name} {{{', '.join(ret)}}}"

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, name):
        if isinstance(name, str):
            raise TypeError("Name must be a string")
        self._name = name

    @abstractmethod
    def format(self):
        pass


class SyntaxNode(SyntaxNodeBase):
    def __init__(self, name, parse_dict):
        super().__init__(name)
        self._name = name
        self._nodes = parse_dict

    def __getitem__(self, key):
        return self.nodes[key]

    def __contains__(self, key):
        return key in self.nodes

    def get_value(self, key):
        temp = self.nodes[key]
        if isinstance(temp, ValueNode):
            return temp.value
        else:
            raise KeyError(f"{key} is not a value leaf node")

    def __str__(self):
        return f"(Node: {self.name}: {self.nodes})"

    def __repr__(self):
        return str(self)

    def format(self):
        ret = ""
        for node in self.nodes.values():
            ret += node.format()
        return ret


class GeometryTree(SyntaxNodeBase):
    def __init__(self, name, tokens, op, left, right=None):
        super().__init__(name)
        self._nodes = tokens
        self._operator = Operator(op)
        self._left_side = left
        self._right_side = right

    def __str__(self):
        return f"Geometry: {self._left_side} {self._operator} {self._right_side}"

    def __repr__(self):
        return str(self)

    def get_geometry_identifiers(self):
        surfaces = []
        cells = []
        for node in self.nodes:
            if isinstance(node, type(self)):
                child_surf, child_cell = node.get_geometry_identifiers()
                surfaces += child_surf
                cells += child_cell
            elif isinstance(node, ValueNode):
                identifier = abs(int(node.value))
                if self._operator == Operator.COMPLEMENT:
                    cells.append(identifier)
                else:
                    surfaces.append(identifier)
        return (surfaces, cells)

    def format(self):
        ret = ""
        for node in self.nodes:
            ret += node.format()
        return ret


class PaddingNode(SyntaxNodeBase):
    def __init__(self, token):
        super().__init__("padding")
        self._nodes = [token]

    def __str__(self):
        return f"(Padding, {self._nodes})"

    def __repr__(self):
        return str(self)

    @property
    def value(self):
        return "".join(self.nodes)

    def is_space(self, i):
        return len(self.nodes[i].strip()) == 0

    def format(self):
        return "".join(self.nodes)


class ValueNode(SyntaxNodeBase):

    _FORMATTERS = {
        float: {
            "value_length": 0,
            "precision": 16,
            "zero_padding": 0,
            "sign": " ",
            "divider": "e",
        },
        int: {"value_length": 0, "zero_padding": 0, "sign": "-"},
        str: {"value_length": 0},
    }

    _SCIENTIFIC_FINDER = re.compile(
        r"""
                                    [+\-]?                      # leading sign if any
                                    (?P<significand>\d+\.*\d*)  # the actual number
                                    (?P<e>[eE]?)                # optional e
                                    [+\-]\d+                    #exponent
                                    """,
        re.VERBOSE,
    )

    def __init__(self, token, token_type, padding=None):
        super().__init__("")
        self._token = token
        self._type = token_type
        self._formatter = self._FORMATTERS[token_type].copy()
        if token is None:
            self._value = None
        elif token_type == float:
            self._value = fortran_float(token)
        elif token_type == int:
            self._value = int(token)
        else:
            self._value = token
        self._padding = padding
        self._nodes = [self]
        self._is_scientific = False

    def _reverse_engineer_formatting(self):
        self._formatter["value_length"] = len(self._token)
        if self.padding:
            if self.padding.is_space(0):
                self._formatter["value_length"] += len(self.padding.nodes[0])

        if self._type == float or self._type == int:
            no_zero_pad = self._token.lstrip("0+-")
            delta = len(self._token) - len(no_zero_pad)
            if self._token.startswith("+") or self._token.startswith("-"):
                delta -= 1
            if delta > 0:
                self._formatter["zero_padding"] = delta
            if self._token.startswith("+"):
                self._formatter["sign"] = "+"
            if self._type == float:
                self._reverse_engineer_float()

    def _reverse_engineer_float(self):
        if match := self._SCIENTIFIC_FINDER.match(self._token):
            groups = match.groupdict(default="")
            self._is_scientific = True
            significand = groups["significand"]
            self._formatter["divider"] = groups["e"]
            # extra space for the "e" in scientific and... stuff
            self._formatter["zero_padding"] += 4
        else:
            significand = self._token
        parts = significand.split(".")
        if len(parts) == 2:
            precision = len(parts[1])
        else:
            precision = 0
        self._formatter["precision"] = precision
        self._formatter["zero_padding"] += precision + 2

    def format(self):
        self._reverse_engineer_formatting()
        if self._type == float:
            if self._is_scientific:
                temp = "{value:0={sign}{zero_padding}.{precision}e}".format(
                    value=self.value, **self._formatter
                )
                temp = temp.replace("e", self._formatter["divider"])
            else:
                temp = "{value:0={sign}{zero_padding}.{precision}f}".format(
                    value=self.value, **self._formatter
                )
        elif self._type == int:
            temp = "{value:0={sign}{zero_padding}g}".format(
                value=self.value, **self._formatter
            )
        else:
            temp = self.value
        if self.padding:
            return "{temp:<{value_length}}{padding}".format(
                temp=temp, padding="".join(self.padding.nodes), **self._formatter
            )
        else:
            return "{temp:<{value_length}}".format(temp=temp, **self._formatter)

    @property
    def padding(self):
        return self._padding

    @padding.setter
    def padding(self, pad):
        self._padding = pad

    def __str__(self):
        return f"(Value, {self._value}, padding: {self._padding}"

    def __repr__(self):
        return str(self)

    @property
    def value(self):
        return self._value

    @value.setter
    def value(self, value):
        self._value = value


class ParticleNode(SyntaxNodeBase):
    def __init__(self, name, token):
        super().__init__(name)
        self._nodes = [self]
        self._token = token
        # TODO parse particles

    def format(self):
        # TODO
        pass


class ListNode(SyntaxNodeBase):
    def __init__(self, name):
        super().__init__(name)

    def __repr__(self):
        return f"(list: {self.name}, {self.nodes})"

    @property
    def value(self):
        strings = []
        for node in self.nodes:
            if isinstance(node, SyntaxNodeBase):
                strings.append(str(node.value))
            else:
                strings.append(node)
        return " ".join(strings)

    def format(self):
        ret = ""
        for node in self.nodes:
            ret += node.format()
        return ret


class IsotopesNode(SyntaxNodeBase):
    def __init__(self, name):
        super().__init__(name)

    def append(self, isotope_fraction):
        isotope, concentration = isotope_fraction[1:3]
        self._nodes.append((isotope, concentration))

    def format(self):
        # TODO
        pass

    def __repr__(self):
        return f"(Isotopes: {self.nodes})"


class ShortcutNode(ListNode):
    _shortcut_names = {
        "REPEAT": Shortcuts.REPEAT,
        "JUMP": Shortcuts.JUMP,
        "INTERPOLATE": Shortcuts.INTERPOLATE,
        "LOG_INTERPOLATE": Shortcuts.LOG_INTERPOLATE,
        "MULTIPLY": Shortcuts.MULTIPLY,
    }
    _num_finder = re.compile(r"\d+")

    def __init__(self, p):
        for search_str, shortcut in self._shortcut_names.items():
            self._type = None
            if hasattr(p, search_str):
                super().__init__(search_str.lower())
                self._type = shortcut
            if self._type is None:
                raise ValueError("must use a valid shortcut")
        self._original = list(p)
        if self._type == Shortcuts.REPEAT:
            self._expand_repeat(p)
        elif self._type == Shortcuts.MULTIPLY:
            self._expand_multiply(p)
        elif self._type == Shortcuts.JUMP:
            self._expand_jump(p)
        elif self._type in {Shortcuts.INTERPOLATE, Shortcuts.LOG_INTERPOLATE}:
            self._expand_interpolate(p)

    def _expand_repeat(self, p):
        self._nodes = [p[0]]
        repeat = p[1]
        try:
            repeat_num = int(repeat.lower().replace("r", ""))
        except ValueError:
            repeat_num = 1
        self._nodes += self.nodes[0] * repeat_num

    def _expand_multiply(self, p):
        self._nodes = [p[0]]
        mult_val = fortran_float(p[1])
        self._nodes.append(self.nodes[-1] * mult_val)

    def _expand_jump(self, p):
        try:
            jump_num = int(p[0].lower().replace("j", ""))
        except ValueError:
            jump_num = 1
        self._nodes = [input_parser.mcnp_input.Jump()] * jump_num

    def _expand_interpolate(self, p):
        if hasattr(p, "LOG_INTERPOLATE"):
            is_log = True
        else:
            is_log = False
        begin = p[0].value
        self._nodes = [p[0]]
        end = p[2].value
        match = self._num_finder.search(p[1])
        if match:
            number = match.group(0)
        else:
            number = 1
        if is_log:
            begin = math.log(begin, 10)
            end = math.log(end, 10)
        spacing = (end - begin) / (number + 1)
        for i in range(number):
            if is_log:
                new_val = 10 ** (begin + spacing * (i + 1))
            else:
                new_val = begin + spacing * (i + 1)
            self.append(new_val)
        self.append(p[2])


class ClassifierNode(SyntaxNodeBase):
    def __init__(self):
        super().__init__("classifier")
        self._prefix = None
        self._number = None
        self._particles = None
        self._modifier = None
        self._nodes = []

    @property
    def prefix(self):
        return self._prefix

    @prefix.setter
    def prefix(self, pref):
        self.append(pref)
        self._prefix = pref

    @property
    def number(self):
        return self._number

    @number.setter
    def number(self, number):
        self.append(number)
        self._number = number

    @property
    def particles(self):
        return self._particles

    @particles.setter
    def particles(self, part):
        self.append(part)
        self._particles = part

    @property
    def modifier(self):
        return self._modifier

    @modifier.setter
    def modifier(self, mod):
        self.append(mod)
        self._modifier = mod

    def format(self):
        if self.modifier:
            ret = self.modifier
        else:
            ret = ""
        ret += self.prefix
        if self.number:
            ret += self.number
        if self.particles:
            ret += self.particles
        return ret


class ParametersNode(SyntaxNodeBase):
    def __init__(self):
        super().__init__("parameters")
        self._nodes = {}

    def append(self, *argv):
        if len(argv) == 3:
            key, seperator, value = argv
            self._nodes[key.lower()] = (value, key, seperator)
        elif len(argv) == 4:
            key, particle, seperator, value = argv
            self._nodes[key.lower() + particle.lower()] = (
                value,
                key,
                particle,
                seperator,
            )

    def get_value(self, key):
        return self.nodes[key.lower()][0].value

    def __str__(self):
        return f"(Parameters, {self.nodes})"

    def __repr__(self):
        return str(self)

    def __getitem__(self, key):
        return self.nodes[key.lower()]

    def __contains__(self, key):
        return key.lower() in self.nodes

    def format(self):
        ret = ""
        for node in self.nodes.values():
            ret += "".join(node[1:-1]) + node[-1].format() + node[0].format()
        return ret

from abc import ABC, abstractmethod
import collections
import enum
import math
from mcnpy import input_parser
from mcnpy import constants
from mcnpy.constants import rel_tol, abs_tol
from mcnpy.input_parser.shortcuts import Shortcuts
from mcnpy.geometry_operators import Operator
from mcnpy.particle import Particle
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

    @property
    @abstractmethod
    def comments(self):
        pass

    def get_trailing_comment(self):
        tail = self.nodes[-1]
        if isinstance(tail, SyntaxNodeBase):
            return tail.get_trailing_comment()

    def _delete_trailing_comment(self):
        tail = self.nodes[-1]
        if isinstance(tail, SyntaxNodeBase):
            tail._delete_trailing_comment()


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
            if isinstance(node, ValueNode):
                if node.value is not None:
                    ret += node.format()
            else:
                ret += node.format()
        return ret

    @property
    def comments(self):
        for node in self.nodes.values():
            yield from node.comments

    def get_trailing_comment(self):
        tail = next(reversed(self.nodes.items()))
        return tail[1].get_trailing_comment()

    def _delete_trailing_comment(self):
        tail = next(reversed(self.nodes.items()))
        tail[1]._delete_trailing_comment()


class GeometryTree(SyntaxNodeBase):
    def __init__(self, name, tokens, op, left, right=None):
        super().__init__(name)
        self._nodes = tokens
        self._operator = Operator(op)
        self._left_side = left
        self._right_side = right

    def __str__(self):
        return f"Geometry: ( {self._left_side} {self._operator} {self._right_side} )"

    def __repr__(self):
        return str(self)

    def get_geometry_identifiers(self):
        surfaces = []
        cells = []
        for node in (self._left_side, self._right_side):
            if node is None:
                continue
            if isinstance(node, type(self)):
                child_surfs, child_cells = node.get_geometry_identifiers()
                surfaces += child_surfs
                cells += child_cells
            elif isinstance(node, ValueNode):
                identifier = abs(int(node.value))
                if self._operator == Operator.COMPLEMENT:
                    cells.append(identifier)
                else:
                    surfaces.append(identifier)
        return (surfaces, cells)

    def format(self):
        ret = ""
        for node in self.nodes.values():
            ret += node.format()
        return ret

    @property
    def comments(self):
        for node in self.nodes:
            yield from node.comments

    @property
    def left(self):
        return self._left_side

    @property
    def right(self):
        return self._right_side

    @property
    def operator(self):
        return self._operator


class PaddingNode(SyntaxNodeBase):
    def __init__(self, token=None, is_comment=False):
        super().__init__("padding")
        if token is not None:
            self.append(token, is_comment)

    def __str__(self):
        return f"(Padding, {self._nodes})"

    def __repr__(self):
        return str(self)

    @property
    def value(self):
        return "".join([val.format() for val in self.nodes])

    def is_space(self, i):
        val = self.nodes[i]
        return len(val.strip()) == 0 and val != "\n"

    def append(self, val, is_comment=False):
        if is_comment:
            if not isinstance(val, CommentNode):
                val = CommentNode(val)
            self.nodes.append(val)
            return
        parts = val.split("\n")
        if len(parts) > 1:
            for part in parts[:-1]:
                if part:
                    self._nodes += [part, "\n"]
                else:
                    self._nodes.append("\n")
            if parts[-1]:
                self._nodes.append(parts[-1])
        else:
            self._nodes.append(val)

    def format(self):
        ret = ""
        for node in self.nodes:
            if isinstance(node, str):
                ret += node
            else:
                ret += node.format()
        return ret

    @property
    def comments(self):
        for node in self.nodes:
            if isinstance(node, CommentNode):
                yield node

    def _get_first_comment(self):
        for i, item in enumerate(self.nodes):
            if isinstance(item, CommentNode):
                return i
        return None

    def get_trailing_comment(self):
        i = self._get_first_comment()
        if i is not None:
            return self.nodes[i:]
        return None

    def _delete_trailing_comment(self):
        i = self._get_first_comment()
        if i is not None:
            del self._nodes[i:]

    def _grab_beginning_comment(self, extra_padding):
        if extra_padding[-1] != "\n":
            extra_padding.append("\n")
        self._nodes = extra_padding + self.nodes


class CommentNode(SyntaxNodeBase):
    """
    Object to represent a comment in an MCNP problem.

    :param input: the token from the lexer
    :type input: Token
    """

    _MATCHER = re.compile(
        rf"""(?P<delim>
                (\s{{0,{constants.BLANK_SPACE_CONTINUE-1}}}C\s?)
                |(\$\s)
             )
            (?P<contents>.*)""",
        re.I | re.VERBOSE,
    )

    def __init__(self, input):
        super().__init__("comment")
        is_dollar, node = self._convert_to_node(input)
        self._is_dollar = is_dollar
        self._nodes = [node]

    def _convert_to_node(self, token):
        match = self._MATCHER.match(token)
        start = match["delim"]
        comment_line = match["contents"]
        is_dollar = "$" in start
        return (
            is_dollar,
            SyntaxNode(
                "comment",
                {
                    "delimiter": ValueNode(start, str),
                    "data": ValueNode(comment_line, str),
                },
            ),
        )

    def append(self, token):
        is_dollar, node = self._convert_to_node(token)
        if is_dollar or self._is_dollar:
            raise TypeError(
                f"Cannot append multiple comments to a dollar comment. {token} given."
            )
        self._nodes.append(node)

    @property
    def is_dollar(self):
        """
        Whether or not this CommentNode is a dollar sign ($) comment.

        :returns: True iff this is a dollar sign comment.
        :rtype: bool
        """
        return self._is_dollar

    @property
    def contents(self):
        """
        The contents of the comments without delimiters (i.e., $/C).

        :returns: String of the contents
        :rtype: str
        """
        return "\n".join([node["data"].value for node in self.nodes])

    def format(self):
        ret = ""
        for node in self.nodes:
            ret += node.format()
        return ret

    def comments(self):
        yield from [self]

    def __str__(self):
        return self.format()

    def __repr__(self):
        ret = f"COMMENT:\n"
        for node in self.nodes:
            ret += node.format()
        return ret


class ValueNode(SyntaxNodeBase):
    _FORMATTERS = {
        float: {
            "value_length": 0,
            "precision": 16,
            "zero_padding": 0,
            "sign": "-",
            "divider": "e",
            "exponent_length": 0,
            "exponent_zero_pad": 0,
            "as_int": False,
            "int_tolerance": 1e-6,
        },
        int: {"value_length": 0, "zero_padding": 0, "sign": "-"},
        str: {"value_length": 0},
    }

    _SCIENTIFIC_FINDER = re.compile(
        r"""
            [+\-]?                      # leading sign if any
            (?P<significand>\d+\.*\d*)  # the actual number
            ((?P<e>[eE])                 # non-optional e with +/-
            [+\-]?|
            [+\-])                  #non-optional +/- if fortran float is used
            (?P<exponent>\d+)                    #exponent
        """,
        re.VERBOSE,
    )

    def __init__(self, token, token_type, padding=None):
        super().__init__("")
        self._token = token
        self._type = token_type
        self._formatter = self._FORMATTERS[token_type].copy()
        self._is_neg_id = False
        self._is_neg_val = False
        self._og_value = None
        if token is None:
            self._value = None
        elif token_type == float:
            if isinstance(token, input_parser.mcnp_input.Jump):
                self._value = None
            else:
                self._value = fortran_float(token)
        elif token_type == int:
            if isinstance(token, input_parser.mcnp_input.Jump):
                self._value = None
            else:
                self._value = int(token)
        else:
            self._value = token
        self._og_value = self.value
        self._padding = padding
        self._nodes = [self]
        self._is_scientific = False
        self._is_reversed = False

    def _convert_to_int(self):
        self._type = int
        if self._token is not None and not isinstance(
            self._token, input_parser.mcnp_input.Jump
        ):
            self._value = int(self._token)
        self._formatter = self._FORMATTERS[int].copy()

    def _convert_to_enum(
        self, enum_class, allow_none=False, format_type=str, switch_to_upper=False
    ):
        self._type = enum_class
        if switch_to_upper:
            value = self._value.upper()
        else:
            value = self._value
        if not (allow_none and self._value is None):
            self._value = enum_class(value)
        self._formatter = self._FORMATTERS[format_type].copy()

    @property
    def is_negatable_identifier(self):
        return self._is_neg_id

    @is_negatable_identifier.setter
    def is_negatable_identifier(self, val):
        if val == True:
            self._convert_to_int()
            if self.value is not None:
                self._is_neg = self.value < 0
                self._value = abs(self._value)
            else:
                self._is_neg = False
        self._is_neg_id = val

    @property
    def is_negetable_float(self):
        return self._is_neg_val

    @is_negetable_float.setter
    def is_negetable_float(self, val):
        if val == True:
            self._is_neg = self.value < 0
            self._value = abs(self._value)
        self._is_neg_val = val

    @property
    def is_negative(self):
        if self.is_negatable_identifier or self.is_negetable_float:
            return self._is_neg
        if self._type in {int, float} and self.value is not None:
            return self.value < 0

    @is_negative.setter
    def is_negative(self, val):
        if self.is_negatable_identifier:
            self._is_neg = val

    def _reverse_engineer_formatting(self):
        if not self._is_reversed and self._token is not None:
            self._is_reversed = True
            token = self._token
            if isinstance(token, input_parser.mcnp_input.Jump):
                token = "J"
            self._formatter["value_length"] = len(token)
            if self.padding:
                if self.padding.is_space(0):
                    self._formatter["value_length"] += len(self.padding.nodes[0])

            if self._type == float or self._type == int:
                no_zero_pad = token.lstrip("0+-")
                delta = len(token) - len(no_zero_pad)
                if token.startswith("+") or token.startswith("-"):
                    delta -= 1
                if delta > 0:
                    self._formatter["zero_padding"] = delta
                if token.startswith("+"):
                    self._formatter["sign"] = "+"
                if self._type == float:
                    self._reverse_engineer_float()

    def _reverse_engineer_float(self):
        token = self._token
        if isinstance(token, input_parser.mcnp_input.Jump):
            token = "J"
        if match := self._SCIENTIFIC_FINDER.match(token):
            groups = match.groupdict(default="")
            self._is_scientific = True
            significand = groups["significand"]
            self._formatter["divider"] = groups["e"]
            # extra space for the "e" in scientific and... stuff
            self._formatter["zero_padding"] += 4
            exponent = groups["exponent"]
            temp_exp = exponent = lstrip("0")
            if exponent != temp_exp:
                self._formatter["exponent_length"] = len(exponent)
                self._formatter["exponent_zero_pad"] = len(exponent) - len(temp_exp)
        else:
            significand = self._token
        parts = significand.split(".")
        if len(parts) == 2:
            precision = len(parts[1])
            self._formatter["zero_padding"] += precision
        else:
            precision = self._FORMATTERS[float]["precision"]
            self._formatter["as_int"] = True

        self._formatter["precision"] = precision

    def _can_float_to_int_happen(self):
        if self._type != float or not self._formatter["as_int"]:
            return False
        nearest_int = round(self.value)
        if not math.isclose(nearest_int, self.value, rel_tol=rel_tol, abs_tol=abs_tol):
            return False
        return True

    @property
    def _print_value(self):
        if self._type == int and self.is_negative:
            return -self.value
        return self.value

    @property
    def _value_changed(self):
        if self.value is None and self._og_value is None:
            return False
        if self.value is None or self._og_value is None:
            return True
        if self._type in {float, int}:
            return not math.isclose(
                self.value, self._og_value, rel_tol=rel_tol, abs_tol=abs_tol
            )
        return self.value != self._og_value

    def format(self):
        # TODO throw warning when things expand
        if not self._value_changed:
            return f"{self._token}{self.padding.format() if self.padding else ''}"
        if self.value is None:
            return ""
        self._reverse_engineer_formatting()
        if issubclass(self.type, enum.Enum):
            value = self.value.value
        else:
            value = self._print_value
        if self._type == int or self._can_float_to_int_happen():
            temp = "{value:0={sign}{zero_padding}d}".format(
                value=int(value), **self._formatter
            )
        elif self._type == float:
            if self._is_scientific:
                temp = "{value:0={sign}{zero_padding}.{precision}e}".format(
                    value=value, **self._formatter
                )
                temp = temp.replace("e", self._formatter["divider"])
                temp_match = self._SCIENTIFIC_FINDER.match(temp)
                exponent = temp_match.group("exponent")
                start, end = temp_math.span("exponent")
                new_exp_temp = "{value:0<{zero_padding}}.d".format(
                    value=int(exponent),
                    zero_padding=self._formatter["exponent_zero_pad"],
                )
                new_exp = "{temp:<{value_length}}".format(
                    temp=new_exp_temp, value_length=self._FORMATTER["exponent_length"]
                )
                temp = temp[0:start] + new_exp + temp[end:]
            elif self._formatter["as_int"]:
                temp = "{value:0={sign}0{zero_padding}g}".format(
                    value=value, **self._formatter
                )
            else:
                temp = "{value:0={sign}0{zero_padding}.{precision}f}".format(
                    value=value, **self._formatter
                )
        else:
            temp = str(value)
        if self.padding:
            if self.padding.is_space(0):
                if len(temp) >= self._formatter["value_length"]:
                    pad_str = " "
                else:
                    pad_str = ""
                pad_str += "".join([x.format() for x in self.padding.nodes[1:]])
            else:
                pad_str = "".join([x.format() for x in self.padding.nodes])
        else:
            pad_str = ""
        temp = "{temp:<{value_length}}{padding}".format(
            temp=temp, padding=pad_str, **self._formatter
        )
        return temp

    @property
    def comments(self):
        if self.padding is not None:
            yield from self.padding.comments
        else:
            yield from []

    def get_trailing_comment(self):
        if self.padding is None:
            return
        return self.padding.get_trailing_comment()

    def _delete_trailing_comment(self):
        if self.padding is None:
            return
        self.padding._delete_trailing_comment()

    @property
    def padding(self):
        return self._padding

    @padding.setter
    def padding(self, pad):
        self._padding = pad

    @property
    def type(self):
        return self._type

    @property
    def token(self):
        return self._token

    def __str__(self):
        return f"(Value, {self._value}, padding: {self._padding})"

    def __repr__(self):
        return str(self)

    @property
    def value(self):
        return self._value

    @value.setter
    def value(self, value):
        self._value = value

    def __eq__(self, other):
        if not isinstance(other, (type(self), str, int, float)):
            raise TypeError(
                f"ValueNode can't be equal to {type(other)} type. {other} given."
            )
        if isinstance(other, ValueNode):
            other_val = other.value
            if self.type != other.type:
                return False
        else:
            other_val = other
            if self.type != type(other):
                return False
        if self.type == float:
            return math.isclose(self.value, other_val, rel_tol=rel_tol, abs_tol=abs_tol)
        return self.value == other_val


class ParticleNode(SyntaxNodeBase):
    _letter_finder = re.compile(r"([a-zA-Z])")

    def __init__(self, name, token):
        super().__init__(name)
        self._nodes = [self]
        self._token = token
        self._order = []
        classifier_chunks = token.replace(":", "").split(",")
        self._particles = set()
        self._formatter = {"upper": False}
        for chunk in classifier_chunks:
            part = Particle(chunk.upper())
            self._particles.add(part)
            self._order.append(part)

    @property
    def particles(self):
        return self._particles

    @particles.setter
    def particles(self, values):
        if not isinstance(values, (list, set)):
            raise ValueError(f"Particles must be a set. {values} given.")
        for value in values:
            if not isinstance(value, Particle):
                raise ValueError(f"All particles must be a Particle. {value} given")
        if isinstance(values, list):
            self._order = values
            values = set(values)
        self._particles = values

    def add(self, value):
        if not isinstance(value, Particle):
            raise ValueError(f"All particles must be a Particle. {value} given")
        self._order.append(value)
        self._particles.add(value)

    def remove(self, value):
        if not isinstance(value, Particle):
            raise ValueError(f"All particles must be a Particle. {value} given")
        self._particles.remove(value)
        self._order.remove(value)

    @property
    def _particles_sorted(self):
        ret = self._order
        ret_set = set(ret)
        remainder = self.particles - ret_set
        extras = ret_set - self.particles
        for straggler in sorted(remainder):
            ret.append(straggler)
        for useless in extras:
            ret.remove(useless)
        return ret

    def format(self):
        self._reverse_engineer_format()
        if self._formatter["upper"]:
            parts = [p.value.upper() for p in self._particles_sorted]
        else:
            parts = [p.value.lower() for p in self._particles_sorted]
        return f":{','.join(parts)}"

    def _reverse_engineer_format(self):
        total_match = 0
        upper_match = 0
        for match in self._letter_finder.finditer(self._token):
            if match:
                if match.group(0).isupper():
                    upper_match += 1
                total_match += 1
        if upper_match / total_match >= 0.5:
            self._formatter["upper"] = True

    @property
    def comments(self):
        yield from []

    def __repr__(self):
        return self.format()

    def __iter__(self):
        return iter(self.particles)


class ListNode(SyntaxNodeBase):
    def __init__(self, name):
        super().__init__(name)
        self._shortcuts = []

    def __repr__(self):
        return f"(list: {self.name}, {self.nodes})"

    def update_with_new_values(self, new_vals):
        new_vals_cache = {id(v): v for v in new_vals}
        # bind shortcuts to single site in new values
        for shortcut in self._shortcuts:
            for node in shortcut.nodes:
                if id(node) in new_vals_cache:
                    new_vals_cache[id(node)] = shortcut
                    shortcut.nodes.clear()
                    break
        self._expand_shortcuts(new_vals, new_vals_cache)
        self._shortcuts = []
        self._nodes = []
        for key, node in new_vals_cache.items():
            if isinstance(node, ShortcutNode):
                if (
                    len(self._shortcuts) > 0 and node is not self._shortcuts[-1]
                ) or len(self._shortcuts) == 0:
                    self._shortcuts.append(node)
                    self._nodes.append(node)
            else:
                self._nodes.append(node)
        end = self._nodes[-1]
        # pop off final shortcut if it's a jump the user left off
        if (
            isinstance(end, ShortcutNode)
            and end._type == Shortcuts.JUMP
            and len(end._original) == 0
        ):
            self._nodes.pop()
            self._shortcuts.pop()

    def _expand_shortcuts(self, new_vals, new_vals_cache):
        def try_expansion(shortcut, value):
            status = shortcut.consume_edge_node(value, 1)
            if status:
                new_vals_cache[id(value)] = shortcut
            else:
                new_vals_cache[id(value)] = value
            return status

        def try_reverse_expansion(shortcut, i, last_end):
            if i > 1:
                for value in new_vals[i - 1 : last_end : -1]:
                    if shortcut.consume_edge_node(value, -1):
                        new_vals_cache[id(value)] = shortcut
                    else:
                        new_vals_cache[id(value)] = value
                        return

        def check_for_orphan_jump(value):
            nonlocal shortcut
            if value.value is None and shortcut is None:
                shortcut = ShortcutNode(p=None, short_type=Shortcuts.JUMP)
                if shortcut.consume_edge_node(value, 1):
                    new_vals_cache[id(value)] = shortcut

        shortcut = None
        last_end = 0
        for i, value in enumerate(new_vals_cache.values()):
            # found a new shortcut
            if isinstance(value, ShortcutNode):
                # shortcuts bumped up against each other
                if shortcut is not None:
                    last_end = i - 1
                shortcut = value
                if try_expansion(shortcut, new_vals[i]):
                    try_reverse_expansion(shortcut, i, last_end)
                else:
                    shortcut = None
            # otherwise it is actually a value to expand as well
            else:
                if shortcut is not None:
                    if not try_expansion(shortcut, new_vals[i]):
                        last_end = i - 1
                        shortcut = None
                        check_for_orphan_jump(new_vals[i])
                else:
                    check_for_orphan_jump(new_vals[i])

    def append(self, val):
        if isinstance(val, ShortcutNode):
            self._shortcuts.append(val)
        super().append(val)

    @property
    def value(self):
        strings = []
        for node in self.nodes:
            if isinstance(node, SyntaxNodeBase):
                strings.append(str(node.value))
            elif isinstance(node, input_parser.mcnp_input.Jump):
                strings.append(str(node))

            else:
                strings.append(node)
        return " ".join(strings)

    @property
    def comments(self):
        for node in self.nodes:
            yield from node.comments

    def format(self):
        ret = ""
        length = len(self.nodes)
        for i, node in enumerate(self.nodes):
            if isinstance(node, ValueNode) and node.padding is None and i < length - 1:
                node.padding = PaddingNode(" ")
            ret += node.format()
        return ret

    def __iter__(self):
        for node in self.nodes:
            if isinstance(node, ShortcutNode):
                yield from node.nodes
            else:
                yield node

    def __getitem__(self, indx):
        if isinstance(indx, slice):
            return self.__get_slice(indx)
        if indx >= 0:
            for i, item in enumerate(self):
                if i == indx:
                    return item
        else:
            items = list(self)
            return items[indx]
        raise IndexError(f"{indx} not in ListNode")

    def __get_slice(self, i: slice):
        rstep = i.step if i.step is not None else 1
        rstart = i.start
        rstop = i.stop
        if rstep < 0:  # Backwards
            if rstart is None:
                rstart = len(self.nodes) - 1
            if rstop is None:
                rstop = 0
            rstop -= 1
        else:  # Forwards
            if rstart is None:
                rstart = 0
            if rstop is None:
                rstop = len(self.nodes) - 1
            rstop += 1
        buffer = []
        allowed_indices = range(rstart, rstop, rstep)
        for i, item in enumerate(self):
            if i in allowed_indices:
                buffer.append(item)
        ret = ListNode(f"{self.name}_slice")
        if rstep < 0:
            buffer = buffer.reverse
        for val in buffer:
            ret.append(val)
        return ret

    def remove(self, obj):
        self.nodes.remove(obj)

    def __eq__(self, other):
        if not isinstance(other, (type(self), list)):
            raise TypeError(
                f"ListNode can only be compared to a ListNode or List. {other} given."
            )
        if len(self) != len(other):
            return False
        for lhs, rhs in zip(self, other):
            if lhs != rhs:
                return False
        return True


class IsotopesNode(SyntaxNodeBase):
    def __init__(self, name):
        super().__init__(name)

    def append(self, isotope_fraction):
        isotope, concentration = isotope_fraction[1:3]
        self._nodes.append((isotope, concentration))

    def format(self):
        ret = ""
        for isotope, concentration in self.nodes:
            ret += isotope.format() + concentration.format()
        return ret

    def __repr__(self):
        return f"(Isotopes: {self.nodes})"

    def __iter__(self):
        return iter(self.nodes)

    @property
    def comments(self):
        for node in self.nodes:
            for value in node:
                yield from value.comments

    def get_trailing_comment(self):
        tail = self.nodes[-1]
        tail = tail[1]
        return tail.get_trailing_comment()

    def _delete_trailing_comment(self):
        tail = self.nodes[-1]
        tail = tail[1]
        tail._delete_trailing_comment()


class ShortcutNode(ListNode):
    _shortcut_names = {
        "REPEAT": Shortcuts.REPEAT,
        "JUMP": Shortcuts.JUMP,
        "INTERPOLATE": Shortcuts.INTERPOLATE,
        "LOG_INTERPOLATE": Shortcuts.LOG_INTERPOLATE,
        "MULTIPLY": Shortcuts.MULTIPLY,
    }
    _num_finder = re.compile(r"\d+")

    def __init__(self, p=None, short_type=None):
        self._type = None
        self._end_pad = None
        self._nodes = collections.deque()
        self._original = []
        if p is not None:
            for search_str, shortcut in self._shortcut_names.items():
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
        elif short_type is not None:
            if not isinstance(short_type, Shortcuts):
                raise TypeError(f"Shortcut type must be Shortcuts. {short_type} given.")
            self._type = short_type
            self._end_pad = PaddingNode(" ")

    @property
    def end_padding(self):
        return self._end_pad

    @end_padding.setter
    def end_padding(self, padding):
        if not isinstance(padding, PaddingNode):
            raise TypeError(
                f"End padding must be of type PaddingNode. {padding} given."
            )
        self._end_pad = padding

    def __repr__(self):
        return f"(shortcut:{self._type}: {self.nodes})"

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
        for i in range(jump_num):
            self._nodes.append(ValueNode(input_parser.mcnp_input.Jump(), float))

    def _expand_interpolate(self, p):
        if hasattr(p, "LOG_INTERPOLATE"):
            is_log = True
        else:
            is_log = False
        if hasattr(p, "geometry_term"):
            term = p.geometry_term
            if isinstance(term, GeometryTree):
                surfs, _ = term.get_geometry_identifiers()
                begin = surfs[-1]
            else:
                begin = term.value
            end = p.number_phrase.value
        else:
            begin = p.number_phrase0.value
            end = p.number_phrase1.value
        self._nodes = [p[0]]
        match = self._num_finder.search(p[1])
        if match:
            number = int(match.group(0))
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
            self.append(ValueNode(str(new_val), float))
        self._begin = begin
        self._end = end
        self._spacing = spacing
        if hasattr(p, "geometry_term"):
            self.append(p.number_phrase)
        else:
            self.append(p.number_phrase1)

    def _can_consume_node(self, node, direction):
        if self._type == Shortcuts.JUMP:
            if node.value is None:
                return True

        # REPEAT
        elif self._type == Shortcuts.REPEAT:
            if len(self.nodes) == 0 and not isinstance(
                node, input_parser.mcnp_input.Jump
            ):
                return True
            if direction == 1:
                edge = self.nodes[-1]
            else:
                edge = self.nodes[0]
            if edge.type != node.type:
                return False
            if edge.type in {int, float} and math.isclose(
                edge.value, node.value, rel_tol=rel_tol, abs_tol=abs_tol
            ):
                return True
            elif edge.value == node.value:
                return True

        # INTERPOLATE
        elif self._type in {Shortcuts.INTERPOLATE, Shortcuts.LOG_INTERPOLATE}:
            return self._is_valid_interpolate_edge(node, direction)
        # Multiply can only ever have 1 value
        elif self._type == Shortcuts.MULTIPLY:
            if len(self.nodes) == 0:
                return True
        return False

    def _is_valid_interpolate_edge(self, node, direction):
        if direction == 1:
            edge = self._end
        else:
            edge = self._begin
        if self._type == Shortcuts.LOG_INTERPOLATE:
            new_val = 10 ** (edge + direction * self._spacing)
        else:
            new_val = edge + direction * self._spacing
        return math.isclose(new_val, node.value, rel_tol=rel_tol, abs_tol=abs_tol)

    def consume_edge_node(self, node, direction):
        if self._can_consume_node(node, direction):
            if direction == 1:
                self._nodes.append(node)
            else:
                self._nodes.appendleft(node)
            return True
        return False

    def _can_recompress(self):
        if self._type == Shortcuts.JUMP:
            for node in self.nodes:
                if not isinstance(node, input_parser.mcnp_input.Jump):
                    return False
            return True
        elif self._type == Shortcuts.REPEAT:
            start_val = self.nodes[0].value
            for node in self.nodes:
                if not math.isclose(
                    start_val, node.value, rel_tol=rel_tol, abs_tol=abs_tol
                ):
                    return False
            return True
        elif self._type == Shortcuts.MULTIPLY:
            return self.nodes[0].type == self.nodes[-1].type
        else:
            if self._type == Shortcuts.LOG_INTERPOLATE:
                is_log = True
            else:
                is_log = False
            for i, node in enumerate(self.nodes):
                new_val = self._begin + self._spacing * (i + 1)
                if is_log:
                    new_val = 10**new_val
                if not math.isclose(
                    new_val, node.value, rel_tol=rel_tol, abs_tol=abs_tol
                ):
                    return False
            return True

    def format(self):
        if not self._can_recompress:
            ret = ""
            for node in self.nodes:
                ret += node.format()
            return ret

        if self._type == Shortcuts.JUMP:
            temp = self._format_jump()
        # repeat
        elif self._type == Shortcuts.REPEAT:
            temp = self._format_repeat()
        elif self._type == Shortcuts.MULTIPY:
            temp = self._format_multiply()
        if self.end_padding:
            pad_str = self.end_padding.format()
        else:
            pad_str = ""
        return f"{temp}{pad_str}"

    def _format_jump(self):
        num_jumps = len(self.nodes)
        if num_jumps == 0:
            return ""
        if len(self._original) > 0 and "j" in self._original[0]:
            j = "j"
        else:
            j = "J"
        length = len(self._original)
        if num_jumps == 1 and (
            length == 0 or (length > 0 and "1" not in self._original[0])
        ):
            num_jumps = ""

        return f"{num_jumps}{j}"

    def _format_repeat(self):
        first_val = self.nodes[0].format()
        num_repeats = len(self.nodes) - 1
        if "r" in self.original[1]:
            r = "r"
        else:
            r = "R"
        if num_repeats == 1 and "1" not in self._original[1]:
            num_repeats = ""
        return f"{first_val}{num_repeats}{r}"

    def _format_multiply(self):
        first_val = self.nodes[0].format()
        multiplier = self.nodes[1].value / self.nodes[0].value
        # TODO create phony ValueNode to format multiplier
        return ""


class ClassifierNode(SyntaxNodeBase):
    def __init__(self):
        super().__init__("classifier")
        self._prefix = None
        self._number = None
        self._particles = None
        self._modifier = None
        self._padding = None
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

    @property
    def padding(self):
        return self._padding

    @padding.setter
    def padding(self, val):
        self.append(val)
        self._padding = val

    def format(self):
        if self.modifier:
            ret = self.modifier.format()
        else:
            ret = ""
        ret += self.prefix.format()
        if self.number:
            ret += self.number.format()
        if self.particles:
            ret += self.particles.format()
        if self.padding:
            ret += self.padding.format()
        return ret

    def __str__(self):
        return self.format()

    def __repr__(self):
        return (
            f"(Classifier: mod: {self.modifier}, prefix: {self.prefix}, "
            f"number: {self.number}, particles: {self.particles})"
        )

    @property
    def comments(self):
        if self.padding is not None:
            yield from self.padding.comments
        else:
            yield from []


class ParametersNode(SyntaxNodeBase):
    def __init__(self):
        super().__init__("parameters")
        self._nodes = {}

    def append(self, val):
        classifier = val["classifier"]
        key = (
            classifier.prefix.value
            + (str(classifier.particles) if classifier.particles else "")
        ).lower()
        if key in self._nodes:
            raise ValueError(f"Second parameter given for {key}.")
        self._nodes[key] = val

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
            ret += node.format()
        return ret

    def get_trailing_comment(self):
        tail = next(reversed(self.nodes.items()))
        return tail[1].get_trailing_comment()

    def _delete_trailing_comment(self):
        tail = next(reversed(self.nodes.items()))
        tail[1]._delete_trailing_comment()

    @property
    def comments(self):
        for node in self.nodes:
            if isinstance(node, SyntaxNodeBase):
                yield from node.comments

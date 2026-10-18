# Copyright 2024-2026, Battelle Energy Alliance, LLC All Rights Reserved.
from montepy.input_parser.data_parser import DataParser
from montepy.input_parser.tokens import TallyLexer
from montepy.input_parser import syntax_node


def _is_run(node) -> bool:
    # type() is, not isinstance(): ShortcutNode is a ListNode subclass.
    return type(node) is syntax_node.ListNode and node.name == "tally number run"


def _iter_runs(node: syntax_node.SyntaxNode):
    """Every ``"tally number run"`` under ``node``, groups included."""
    for child in node.nodes.values():
        if _is_run(child):
            yield child
        elif isinstance(child, syntax_node.SyntaxNode):
            yield from _iter_runs(child)


def _next_key(parent: syntax_node.SyntaxNode, kind: str) -> tuple[str, int]:
    """The next ``(kind, n)`` key for a child of ``parent``.

    .. warning::

        ``n`` only makes the key unique within ``parent``; it is *not* the
        child's position, or its position among children of the same kind.
        The order of ``parent.nodes`` is the order. ``n`` is one more than
        the highest in use, so a removed child's number is never reused
        while a later one exists.
    """
    used = [k[1] for k in parent.nodes if isinstance(k, tuple) and k[0] == kind]
    return (kind, max(used, default=-1) + 1)


def _set_end_flag(tally_list: syntax_node.SyntaxNode, flag: str | None) -> None:
    """Write ``flag`` (``"T"`` or ``"C"``, or ``None`` to remove it) after the bins.

    ``tally_list`` is the ``"tally list"`` node, holding the bins under
    ``"tally"`` and the flag under ``"end"``.
    """
    end_node = tally_list["end"]
    if flag is None:
        # "" rather than None: a None value isn't written, and neither is
        # its padding, which can hold a trailing comment.
        if end_node.value is not None:
            end_node.value = ""
        return
    text = tally_list["tally"].format()
    comments = list(tally_list["tally"].comments)
    # After a trailing comment, the flag is already moved to a new line.
    ends_in_comment = bool(comments) and text.endswith(comments[-1].format())
    if (
        not text[-1:].isspace()
        and not ends_in_comment
        and "end_padding" not in tally_list.nodes
    ):
        # The last bin has no trailing padding (e.g. "f4:n 1 2"), so the
        # flag would be glued to it as "2T".
        end = tally_list.nodes.pop("end")
        tally_list.nodes["end_padding"] = syntax_node.PaddingNode(" ")
        tally_list.nodes["end"] = end
    end_node.value = flag


def _item_kind(item) -> str:
    if isinstance(item, syntax_node.SyntaxNode) and item.name == "tally group":
        return "group"
    if isinstance(item, syntax_node.ListNode) and item.name == "lattice phrase":
        return "lattice"
    if isinstance(item, syntax_node.ListNode) and item.name == "universe phrase":
        return "universe"
    if isinstance(item, syntax_node.ValueNode) and item.type is str:
        return "sep"
    return "run"


def _append_tally_item(parent: syntax_node.SyntaxNode, item) -> None:
    """Add ``item`` as the last child of ``parent``, collecting numbers into runs.

    Each run is a ``"tally number run"`` ``ListNode`` holding only numbers
    and shortcuts, which it owns, so it can be re-zipped with
    :meth:`~montepy.input_parser.syntax_node.ListNode.update_with_new_values`
    without touching the parens, ``<``, lattice, or ``u=`` around it.
    Everything else is keyed by its kind; see :func:`_next_key`.
    """
    kind = _item_kind(item)
    if kind != "run":
        parent.nodes[_next_key(parent, kind)] = item
        return
    last = next(reversed(parent.nodes.values()), None)
    if not _is_run(last):
        last = syntax_node.ListNode("tally number run")
        parent.nodes[_next_key(parent, "run")] = last
    # A chain of shortcuts (e.g. "1 2r 3i 5") arrives as one ListNode.
    is_chain = type(item) is syntax_node.ListNode and item.name == "next_shortcuts"
    for node in item.nodes if is_chain else [item]:
        last.append(node)


class TallyParser(DataParser):
    """A parser for ``F`` tally inputs.

    Cell/surface numbers, including the values a shortcut (e.g. ``3i``)
    expands to, are parsed as ``int``. See :class:`TallyMultiplierParser`
    for ``FM`` inputs, whose numbers are ``float``.

    Returns
    -------
    SyntaxNode
        a syntax tree for the data input.
    """

    debugfile = None
    _lexer_class = TallyLexer

    @_("introduction tally_specification")
    def tally(self, p):
        ret = {}
        for key, node in p.introduction.nodes.items():
            ret[key] = node
        ret["data"] = p.tally_specification
        return syntax_node.SyntaxNode("data", ret)

    @_("tally_numbers", "tally_numbers end_phrase")
    def tally_specification(self, p):
        if hasattr(p, "end_phrase"):
            text = p.end_phrase
        else:
            text = syntax_node.ValueNode(None, str)

        return syntax_node.SyntaxNode(
            "tally list", {"tally": p.tally_numbers, "end": text}
        )

    @_("PARTICLE", "PARTICLE padding", "TEXT", "TEXT padding")
    def end_phrase(self, p):
        """A non-zero number with or without padding.

        Returns
        -------
        ValueNode
            a float ValueNode

        Notes
        -----
        ``T`` (total) happens to lex as ``PARTICLE`` (the triton letter), but
        ``C`` (cumulative, FM cards only) isn't a particle letter and lexes
        as ``TEXT`` instead -- both alternatives are needed here.
        """
        return self._flush_phrase(p, str)

    # tally_numbers uses fresh rules (no number_sequence) so that the inherited
    # `number_sequence → "(" number_sequence ")"` production is unreachable from
    # the `tally` start symbol and cannot create a shift/reduce conflict with
    # lparen_phrase inside tally_group.
    @_(
        "tally_flat_item",
        "tally_group",
        "tally_numbers tally_flat_item",
        "tally_numbers tally_group",
    )
    def tally_numbers(self, p):
        if hasattr(p, "tally_numbers"):
            ret = p.tally_numbers
            item = p.tally_flat_item if hasattr(p, "tally_flat_item") else p.tally_group
        else:
            ret = syntax_node.SyntaxNode("tally bins", {})
            item = p[0]
        _append_tally_item(ret, item)
        return ret

    @_("identifier_phrase", "null_ident_phrase", "tally_shortcut_phrase")
    def tally_flat_item(self, p):
        return p[0]

    @_("lparen_phrase tally_group_body rparen_phrase")
    def tally_group(self, p):
        nodes = {"start_pad": p.lparen_phrase}
        nodes.update(p.tally_group_body.nodes)
        nodes["end_pad"] = p.rparen_phrase
        return syntax_node.SyntaxNode("tally group", nodes)

    @_("tally_group_item", "tally_group_body tally_group_item")
    def tally_group_body(self, p):
        if hasattr(p, "tally_group_body"):
            ret = p.tally_group_body
        else:
            ret = syntax_node.SyntaxNode("tally group body", {})
        _append_tally_item(ret, p.tally_group_item)
        return ret

    @_(
        "identifier_phrase",
        "null_ident_phrase",
        "tally_shortcut_phrase",
        "path_sep",
        "lattice_phrase",
        "universe_phrase",
        "tally_group",
    )
    def tally_group_item(self, p):
        return p[0]

    @_("identifier_phrase", "tally_shortcut_phrase")
    def tally_shortcut_start(self, p):
        return p[0]

    # Mirrors MCNP_Parser.shortcut_sequence, but with int values like
    # CellParser's geometry shortcuts.
    @_(
        "tally_shortcut_start NUM_REPEAT",
        "tally_shortcut_start REPEAT",
        "tally_shortcut_start NUM_MULTIPLY",
        "tally_shortcut_start MULTIPLY",
        "tally_shortcut_start NUM_INTERPOLATE padding number_phrase",
        "tally_shortcut_start INTERPOLATE padding number_phrase",
        "tally_shortcut_start NUM_LOG_INTERPOLATE padding number_phrase",
        "tally_shortcut_start LOG_INTERPOLATE padding number_phrase",
        "NUM_JUMP",
        "JUMP",
    )
    def tally_shortcut_sequence(self, p):
        """A tally shortcut (repeat, multiply, interpolate, or jump).

        Returns
        -------
        ShortcutNode
            the parsed shortcut, with ``int`` values.
        """
        if hasattr(p, "number_phrase"):
            # ShortcutNode reads the interpolate end point by this name.
            p.number_phrase.convert_to_int()
        short_cut = syntax_node.ShortcutNode(p, data_type=int)
        if isinstance(p[0], syntax_node.ShortcutNode):
            list_node = syntax_node.ListNode("next_shortcuts")
            list_node.append(p[0])
            list_node.append(short_cut)
            return list_node
        if isinstance(p[0], syntax_node.ListNode):
            p[0].append(short_cut)
            return p[0]
        return short_cut

    @_("tally_shortcut_sequence", "tally_shortcut_sequence padding")
    def tally_shortcut_phrase(self, p):
        """A complete tally shortcut; see :meth:`tally_shortcut_sequence`.

        Returns
        -------
        ShortcutNode
            the parsed shortcut.
        """
        sequence = p.tally_shortcut_sequence
        if len(p) == 2:
            sequence.end_padding = p.padding
        return sequence

    @_("PARTICLE_SPECIAL", "PARTICLE_SPECIAL padding")
    def path_sep(self, p):
        return self._flush_phrase(p, str)

    @_('"[" lattice_body "]"', '"[" lattice_body "]" padding')
    def lattice_phrase(self, p):
        ret = syntax_node.ListNode("lattice phrase")
        ret.append(syntax_node.PaddingNode(p[0]))
        for node in p.lattice_body.nodes:
            ret.append(node)
        if hasattr(p, "padding"):
            ret.append(syntax_node.PaddingNode(p[2]))
            ret.append(p.padding)
        else:
            ret.append(syntax_node.PaddingNode(p[2]))
        return ret

    @_(
        "lattice_item",
        "lattice_body lattice_item",
        'lattice_body "," lattice_item',
        'lattice_body "," padding lattice_item',
    )
    def lattice_body(self, p):
        if hasattr(p, "lattice_body"):
            ret = p.lattice_body
        else:
            ret = syntax_node.ListNode("lattice body")
        if hasattr(p, "padding"):
            # lattice_body "," padding lattice_item
            ret.append(syntax_node.PaddingNode(p[1]))
            ret.append(p.padding)
        elif len(p) > 1 and isinstance(p[1], str) and p[1] == ",":
            # lattice_body "," lattice_item
            ret.append(syntax_node.PaddingNode(p[1]))
        ret.append(p.lattice_item)
        return ret

    @_(
        "identifier_phrase",
        "null_ident_phrase",
        'identifier_phrase ":" identifier_phrase',
        'null_ident_phrase ":" identifier_phrase',
        'identifier_phrase ":" null_ident_phrase',
        'null_ident_phrase ":" null_ident_phrase',
    )
    def lattice_item(self, p):
        if len(p) > 1:
            ret = syntax_node.ListNode("lattice range")
            ret.append(p[0])
            ret.append(syntax_node.PaddingNode(p[1]))
            ret.append(p[2])
            return ret
        return p[0]

    @_(
        "KEYWORD equals_sign identifier_phrase",
        "PARTICLE equals_sign identifier_phrase",
    )
    def universe_phrase(self, p):
        token_val = p.KEYWORD if hasattr(p, "KEYWORD") else p.PARTICLE
        ret = syntax_node.ListNode("universe phrase")
        ret.append(syntax_node.ValueNode(token_val, str))
        ret.append(p.equals_sign)
        ret.append(p.identifier_phrase)
        return ret


class TallyMultiplierParser(TallyParser):
    """A parser for ``FM`` tally multiplier inputs.

    Shares the bin structure of :class:`TallyParser`, but its numbers
    (constants, material numbers, reactions) are ``float``, and its groups
    allow the reaction-list operators instead of path/lattice/universe
    syntax.

    Returns
    -------
    SyntaxNode
        a syntax tree for the data input.
    """

    start = "tally"
    # FM keeps a flat structure: its numbers aren't re-zipped like F's.
    dont_copy = {
        "tally_numbers",
        "tally_group",
        "tally_group_body",
        "tally_flat_item",
        "tally_group_item",
    }

    @_(
        "tally_flat_item",
        "tally_group",
        "tally_numbers tally_flat_item",
        "tally_numbers tally_group",
    )
    def tally_numbers(self, p):
        if hasattr(p, "tally_numbers"):
            ret = p.tally_numbers
            item = p.tally_flat_item if hasattr(p, "tally_flat_item") else p.tally_group
        else:
            ret = syntax_node.ListNode("tally numbers")
            item = p[0]
        # type() is, not isinstance(): ShortcutNode is a ListNode subclass
        # and must stay unflattened, same as number_sequence in parser_base.py.
        if type(item) is syntax_node.ListNode and item.name != "tally group":
            for node in item.nodes:
                ret.append(node)
        else:
            ret.append(item)
        return ret

    @_("tally_group_item", "tally_group_body tally_group_item")
    def tally_group_body(self, p):
        if hasattr(p, "tally_group_body"):
            ret = p.tally_group_body
        else:
            ret = syntax_node.ListNode("tally group body")
        ret.append(p.tally_group_item)
        return ret

    @_("lparen_phrase tally_group_body rparen_phrase")
    def tally_group(self, p):
        ret = syntax_node.ListNode("tally group")
        ret.append(p.lparen_phrase)
        for node in p.tally_group_body.nodes:
            ret.append(node)
        ret.append(p.rparen_phrase)
        return ret

    @_("number_phrase", "null_phrase", "shortcut_phrase")
    def tally_flat_item(self, p):
        return p[0]

    @_(
        "number_phrase",
        "null_phrase",
        "shortcut_phrase",
        "tally_group",
        "reaction_operator",
    )
    def tally_group_item(self, p):
        return p[0]

    @_('":"', '":" padding', "COMPLEMENT", "COMPLEMENT padding")
    def reaction_operator(self, p):
        """An FM reaction-list operator: ``:`` (add) or ``#`` (subtract).

        Returns
        -------
        ValueNode
            a str ValueNode holding the raw operator symbol.
        """
        return self._flush_phrase(p, str)

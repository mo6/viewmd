"""Mermaid flowchart (`graph`/`flowchart`) parsing, ported from cmd/parse.go.

Produces a `GraphProperties` -- the same parse-domain intermediate the
upstream Go source builds -- which `flowchart/graph.py` then converts into the
render-domain `Graph` model.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum

from viewmd.mermaid.grid.label import GraphLabel, new_graph_label

BOX_BORDER_PADDING = 1
PADDING_X = 5
PADDING_Y = 5

GRAPH_KEYWORDS = ("graph", "flowchart")


class ParseError(Exception):
    pass


class NodeShape(str, Enum):
    """Mermaid flowchart node shapes recognized by `parse_node` (VIEWMD-0022).

    Bare nodes (no shape delimiters) use RECTANGLE -- the same default Mermaid
    renders -- so layout/drawing always have a concrete shape to key on.
    """

    RECTANGLE = "rectangle"
    ROUND = "round"
    STADIUM = "stadium"
    CIRCLE = "circle"
    SUBROUTINE = "subroutine"
    CYLINDER = "cylinder"
    DIAMOND = "diamond"


# Longest openers first so `((` / `([` / `[[` / `[(` win over `(` / `[`.
_SHAPE_DELIMITERS: tuple[tuple[NodeShape, str, str], ...] = (
    (NodeShape.CIRCLE, "((", "))"),
    (NodeShape.STADIUM, "([", "])"),
    (NodeShape.SUBROUTINE, "[[", "]]"),
    (NodeShape.CYLINDER, "[(", ")]"),
    (NodeShape.ROUND, "(", ")"),
    (NodeShape.DIAMOND, "{", "}"),
    (NodeShape.RECTANGLE, "[", "]"),
)


@dataclass
class TextNode:
    name: str
    label: GraphLabel
    has_label: bool = False
    style_class: str = ""
    shape: NodeShape = NodeShape.RECTANGLE


@dataclass
class GraphNodeSpec:
    # Deliberately not `new_graph_label("")` -- an *unset* spec (zero lines) is
    # distinguishable from a node explicitly labelled with an empty string, the
    # same distinction cmd/parse.go's zero-value `graphLabel{}` makes.
    label: GraphLabel = field(default_factory=lambda: GraphLabel(lines=[], width=0))
    label_is_explicit: bool = False
    style_class: str = ""
    shape: NodeShape = NodeShape.RECTANGLE


@dataclass
class TextEdge:
    parent: TextNode
    child: TextNode
    label: str
    is_bidirectional: bool


@dataclass
class TextSubgraph:
    id: str
    name: str
    label: GraphLabel
    nodes: list[str] = field(default_factory=list)
    parent: TextSubgraph | None = None
    children: list[TextSubgraph] = field(default_factory=list)


@dataclass
class StyleClass:
    name: str
    styles: dict[str, str]


@dataclass
class GraphProperties:
    data: dict[str, list[TextEdge]]
    node_specs: dict[str, GraphNodeSpec]
    style_classes: dict[str, StyleClass]
    box_border_padding: int
    graph_direction: str
    padding_x: int
    padding_y: int
    subgraphs: list[TextSubgraph]
    use_ascii: bool = False


def _has_graph_keyword(line: str) -> bool:
    lower = line.strip().lower()
    for kw in GRAPH_KEYWORDS:
        if lower.startswith(kw):
            rest = lower[len(kw) :]
            if rest == "" or rest[0] in (" ", "\t"):
                return True
    return False


def sniff(text: str) -> bool:
    """Whether `text` opens with the `graph`/`flowchart` keyword (ignoring
    blank lines and %% comments)."""
    for line in text.split("\n"):
        trimmed = line.strip()
        if trimmed == "" or trimmed.startswith("%%"):
            continue
        return _has_graph_keyword(trimmed)
    return False


_SUBGRAPH_HEADER_RE = re.compile(r"^(\S+)\s*\[(.+)\]$")


def _parse_subgraph_header(header: str) -> TextSubgraph:
    trimmed = header.strip()
    label_text = trimmed
    id_ = ""
    m = _SUBGRAPH_HEADER_RE.match(trimmed)
    if m:
        id_ = m.group(1).strip()
        label_text = m.group(2).strip().strip('"')
    return TextSubgraph(id=id_, name=label_text, label=new_graph_label(label_text), nodes=[])


def split_graph_lines(mermaid: str) -> list[str]:
    """Split on real/escaped newlines, but not inside `[...]` node labels or
    quoted strings -- so a label containing a literal newline stays one
    logical line. Ported from cmd/parse.go's `splitGraphLines`."""
    lines: list[str] = []
    current: list[str] = []
    bracket_depth = 0
    in_quotes = False
    i = 0
    n = len(mermaid)
    while i < n:
        ch = mermaid[i]
        if ch == '"':
            in_quotes = not in_quotes
        elif ch == "[":
            if not in_quotes:
                bracket_depth += 1
        elif ch == "]":
            if not in_quotes and bracket_depth > 0:
                bracket_depth -= 1
        elif ch == "\n":
            if bracket_depth == 0:
                lines.append("".join(current))
                current = []
                i += 1
                continue
        elif ch == "\\":
            if i + 1 < n and mermaid[i + 1] == "n" and bracket_depth == 0:
                lines.append("".join(current))
                current = []
                i += 2
                continue
        current.append(ch)
        i += 1
    lines.append("".join(current))
    return lines


def parse_node(line: str) -> TextNode:
    trimmed = line.strip()
    style_class = ""
    idx = trimmed.rfind(":::")
    if idx != -1:
        style_class = trimmed[idx + 3 :].strip()
        trimmed = trimmed[:idx].strip()

    for shape, open_delim, close_delim in _SHAPE_DELIMITERS:
        if not trimmed.endswith(close_delim):
            continue
        open_idx = trimmed.find(open_delim)
        if open_idx <= 0:
            continue
        name = trimmed[:open_idx].strip()
        if not name:
            continue
        label_text = trimmed[open_idx + len(open_delim) : len(trimmed) - len(close_delim)]
        label_text = label_text.strip().strip('"')
        return TextNode(
            name=name,
            label=new_graph_label(label_text),
            has_label=True,
            style_class=style_class,
            shape=shape,
        )

    return TextNode(
        name=trimmed,
        label=new_graph_label(trimmed),
        style_class=style_class,
        shape=NodeShape.RECTANGLE,
    )


def _parse_style_class(class_name: str, styles: str) -> StyleClass:
    style_map: dict[str, str] = {}
    for style in styles.split(","):
        kv = style.split(":")
        style_map[kv[0]] = kv[1]
    return StyleClass(name=class_name, styles=style_map)


def _remember_node(node: TextNode, node_specs: dict[str, GraphNodeSpec]) -> None:
    spec = node_specs.get(node.name, GraphNodeSpec())
    if node.has_label or len(spec.label.lines) == 0:
        spec.label = node.label
        spec.label_is_explicit = node.has_label
    # Bare later references (`B`) must not wipe a shape from an earlier
    # shaped declaration (`B{Decision}`) -- that's the topology fix.
    if node.has_label:
        spec.shape = node.shape
    if node.style_class:
        spec.style_class = node.style_class
    node_specs[node.name] = spec


def _add_node(
    node: TextNode, data: dict[str, list[TextEdge]], node_specs: dict[str, GraphNodeSpec]
) -> None:
    _remember_node(node, node_specs)
    data.setdefault(node.name, [])


def _set_data(
    parent: TextNode,
    edge: TextEdge,
    data: dict[str, list[TextEdge]],
    node_specs: dict[str, GraphNodeSpec],
) -> None:
    _remember_node(parent, node_specs)
    _remember_node(edge.child, node_specs)
    data.setdefault(parent.name, []).append(edge)
    data.setdefault(edge.child.name, [])


def _set_arrow_with_label(
    lhs: list[TextNode],
    rhs: list[TextNode],
    label: str,
    is_bidirectional: bool,
    gp: GraphProperties,
) -> list[TextNode]:
    for left in lhs:
        for right in rhs:
            edge = TextEdge(
                parent=left, child=right, label=label, is_bidirectional=is_bidirectional
            )
            _set_data(left, edge, gp.data, gp.node_specs)
    return rhs


_EMPTY_RE = re.compile(r"^\s*$")
_BIDIR_LABEL_RE = re.compile(r"^(.+)\s*<-->\s*\|(.+)\|\s*(.+)$", re.DOTALL)
_BIDIR_RE = re.compile(r"^(.+)\s*<-->\s*(.+)$", re.DOTALL)
_ARROW_LABEL_RE = re.compile(r"^(.+)\s*-->\s*\|(.+)\|\s*(.+)$", re.DOTALL)
_ARROW_RE = re.compile(r"^(.+)\s*-->\s*(.+)$", re.DOTALL)
_CLASSDEF_RE = re.compile(r"^classDef\s+(.+)\s+(.+)$")
_FANOUT_RE = re.compile(r"^(.+) & (.+)$", re.DOTALL)


def _parse_string(line: str, gp: GraphProperties) -> list[TextNode]:
    """Ported from cmd/parse.go's `graphProperties.parseString`: an ordered
    regex-and-recurse grammar over a single logical line. Patterns are tried
    in order; the first to match wins (no backtracking across patterns)."""
    if _EMPTY_RE.match(line):
        return []

    m = _BIDIR_LABEL_RE.match(line)
    if m:
        lhs = _parse_fragment(m.group(1), gp)
        rhs = _parse_fragment(m.group(3), gp)
        return _set_arrow_with_label(lhs, rhs, m.group(2), True, gp)

    m = _BIDIR_RE.match(line)
    if m:
        lhs = _parse_fragment(m.group(1), gp)
        rhs = _parse_fragment(m.group(2), gp)
        return _set_arrow_with_label(lhs, rhs, "", True, gp)

    m = _ARROW_LABEL_RE.match(line)
    if m:
        lhs = _parse_fragment(m.group(1), gp)
        rhs = _parse_fragment(m.group(3), gp)
        return _set_arrow_with_label(lhs, rhs, m.group(2), False, gp)

    m = _ARROW_RE.match(line)
    if m:
        lhs = _parse_fragment(m.group(1), gp)
        rhs = _parse_fragment(m.group(2), gp)
        return _set_arrow_with_label(lhs, rhs, "", False, gp)

    m = _CLASSDEF_RE.match(line)
    if m:
        sc = _parse_style_class(m.group(1), m.group(2))
        gp.style_classes[sc.name] = sc
        return []

    m = _FANOUT_RE.match(line)
    if m:
        lhs = _parse_fragment(m.group(1), gp)
        rhs = _parse_fragment(m.group(2), gp)
        return lhs + rhs

    raise ParseError(f"could not parse line: {line}")


def _parse_fragment(fragment: str, gp: GraphProperties) -> list[TextNode]:
    try:
        return _parse_string(fragment, gp)
    except ParseError:
        return [parse_node(fragment)]


_PADDING_RE = re.compile(r"^padding([xy])\s*=\s*(\d+)$", re.IGNORECASE)
_SUBGRAPH_RE = re.compile(r"^\s*subgraph\s+(.+)$")
_END_RE = re.compile(r"^\s*end\s*$")


def parse(text: str) -> GraphProperties:
    """Ported from cmd/parse.go's `mermaidFileToMap`."""
    raw_lines = split_graph_lines(text)

    lines: list[str] = []
    for line in raw_lines:
        if line == "---":
            break
        if line.strip().startswith("%%"):
            continue
        idx = line.find("%%")
        if idx != -1:
            line = line[:idx].strip()
        if line.strip():
            lines.append(line)

    gp = GraphProperties(
        data={},
        node_specs={},
        style_classes={},
        box_border_padding=BOX_BORDER_PADDING,
        graph_direction="",
        padding_x=PADDING_X,
        padding_y=PADDING_Y,
        subgraphs=[],
    )

    while lines:
        trimmed = lines[0].strip()
        if trimmed == "":
            lines = lines[1:]
            continue
        m = _PADDING_RE.match(trimmed)
        if m:
            value = int(m.group(2))
            if m.group(1).lower() == "x":
                gp.padding_x = value
            else:
                gp.padding_y = value
            lines = lines[1:]
            continue
        break

    if not lines:
        raise ParseError("missing graph definition")

    fields = lines[0].rstrip("; \t\r").split()
    if not fields or fields[0] not in ("graph", "flowchart"):
        raise ParseError(
            f"unsupported graph type '{lines[0].strip()}'. Supported types: 'graph' or 'flowchart' "
            "with an optional direction (TD, TB, BT, LR, RL)"
        )
    if len(fields) > 2:
        raise ParseError(f'unexpected tokens after graph direction: "{" ".join(fields[2:])}"')

    gp.graph_direction = "TD"
    if len(fields) == 2:
        if fields[1] in ("LR", "RL"):
            gp.graph_direction = "LR"
        elif fields[1] in ("TD", "TB", "BT"):
            gp.graph_direction = "TD"
        else:
            raise ParseError(
                f"unsupported graph direction '{fields[1]}'. "
                "Supported directions: TD, TB, BT, LR, RL"
            )
    lines = lines[1:]

    subgraph_stack: list[TextSubgraph] = []

    for line in lines:
        trimmed = line.strip()

        m = _SUBGRAPH_RE.match(trimmed)
        if m:
            header = _parse_subgraph_header(m.group(1))
            new_sg = TextSubgraph(
                id=header.id, name=header.name, label=header.label, nodes=[], children=[]
            )
            if subgraph_stack:
                parent = subgraph_stack[-1]
                new_sg.parent = parent
                parent.children.append(new_sg)
            subgraph_stack.append(new_sg)
            gp.subgraphs.append(new_sg)
            continue

        if _END_RE.match(trimmed):
            if subgraph_stack:
                subgraph_stack.pop()
            continue

        existing_nodes = set(gp.data.keys())
        try:
            nodes = _parse_string(line, gp)
            for node in nodes:
                _add_node(node, gp.data, gp.node_specs)
        except ParseError:
            node = parse_node(line)
            _add_node(node, gp.data, gp.node_specs)

        if subgraph_stack:
            for node_name in gp.data.keys():
                if node_name not in existing_nodes:
                    for sg in subgraph_stack:
                        if node_name not in sg.nodes:
                            sg.nodes.append(node_name)

    return gp

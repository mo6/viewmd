import re

import pytest

from viewmd.mermaid.flowchart.parser import NodeShape, ParseError, parse, parse_node, sniff


@pytest.mark.parametrize(
    ("source", "message"),
    [
        ("", "missing graph definition"),
        ("A-->B", "unsupported graph type 'A-->B'"),
        ("classDiagram\nfoo", "unsupported graph type 'classDiagram'"),
        ("graph FOO\nA-->B", "unsupported graph direction 'FOO'"),
        ("graph TD extra tokens\nA-->B", 'unexpected tokens after graph direction: "extra tokens"'),
    ],
)
def test_parse_errors(source, message):
    with pytest.raises(ParseError, match=re.escape(message)):
        parse(source)


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("graph TD\nA-->B", True),
        ("flowchart LR\nA-->B", True),
        ("GRAPH TD\nA-->B", True),
        ("graph\nA-->B", True),
        ("graphFoo\nA-->B", False),
        ("sequenceDiagram\nA->>B: hi", False),
        ("", False),
        ("%% just a comment", False),
    ],
)
def test_sniff(source, expected):
    assert sniff(source) == expected


def test_bare_graph_defaults_to_td():
    gp = parse("graph\nA-->B")
    assert gp.graph_direction == "TD"


@pytest.mark.parametrize(
    ("direction", "expected"),
    [("LR", "LR"), ("RL", "LR"), ("TD", "TD"), ("TB", "TD"), ("BT", "TD")],
)
def test_direction_aliasing(direction, expected):
    """BT/RL are accepted syntax but aliased to TD/LR, never actually
    reversed, matching the upstream Go reference (VIEWMD-0015 req. 1)."""
    gp = parse(f"graph {direction}\nA-->B")
    assert gp.graph_direction == expected


def test_square_bracket_label():
    node = parse_node("A[Hello world]")
    assert node.name == "A"
    assert node.label.lines == ["Hello world"]
    assert node.has_label is True
    assert node.shape == NodeShape.RECTANGLE


@pytest.mark.parametrize(
    ("shape_source", "name", "label", "shape"),
    [
        ("B(Round)", "B", "Round", NodeShape.ROUND),
        ("B{Diamond}", "B", "Diamond", NodeShape.DIAMOND),
        ("B((Circle))", "B", "Circle", NodeShape.CIRCLE),
        ("B([Stadium])", "B", "Stadium", NodeShape.STADIUM),
        ("B[[Sub]]", "B", "Sub", NodeShape.SUBROUTINE),
        ("DB[(Database)]", "DB", "Database", NodeShape.CYLINDER),
    ],
)
def test_shaped_node_parsing(shape_source, name, label, shape):
    """VIEWMD-0022: each Mermaid shape delimiter extracts name vs label and
    records a distinct NodeShape -- no longer flattened to a bare name."""
    node = parse_node(shape_source)
    assert node.name == name
    assert node.label.lines == [label]
    assert node.has_label is True
    assert node.shape == shape


def test_shaped_declaration_and_bare_reference_share_node_name():
    """The branching topology fix: `B{Decision}` and a later bare `B` are the
    same node, so yes/no edges rejoin on the diamond (VIEWMD-0022)."""
    gp = parse(
        "graph TD\nA[Start] --> B{Decision}\nB -->|yes| C[Do it]\nB -->|no| D[Skip]"
    )
    assert "B{Decision}" not in gp.data
    assert "B" in gp.data
    assert gp.node_specs["B"].shape == NodeShape.DIAMOND
    assert gp.node_specs["B"].label.lines == ["Decision"]
    assert {e.child.name for e in gp.data["B"]} == {"C", "D"}


def test_doubled_brace_shape_falls_back_to_bare_label():
    """`{{Hexagon}}` isn't a recognized shape -- it must not mismatch as a
    DIAMOND `{...}` with a mangled label (`{Hexagon}`, stray inner brace).
    Same fallback discipline as any other unsupported shape (VIEWMD-0022
    req. 4 / VIEWMD-0015 req. 6): bare node, literal name."""
    node = parse_node("A{{Hexagon}}")
    assert node.name == "A{{Hexagon}}"
    assert node.has_label is False
    assert node.shape == NodeShape.RECTANGLE


def test_style_class_suffix():
    node = parse_node("A[Start]:::red")
    assert node.name == "A"
    assert node.style_class == "red"
    assert node.label.lines == ["Start"]
    assert node.shape == NodeShape.RECTANGLE


def test_classdef_must_be_unindented():
    """A real quirk of the upstream parser: `classDef` only matches when the
    line has zero leading whitespace; an indented one silently falls back to
    a bare node instead of registering a style class (confirmed against the
    real Go binary)."""
    gp = parse("graph TD\n  classDef red fill:#f96\n  A-->B")
    assert "red" not in gp.style_classes
    # parse_node() strips leading whitespace itself, so the fallback bare
    # node's name has no leading spaces even though the raw line did.
    assert "classDef red fill:#f96" in gp.data

    gp = parse("graph TD\nclassDef red fill:#f96\nA-->B")
    assert "red" in gp.style_classes
    assert gp.style_classes["red"].styles == {"fill": "#f96"}


def test_chained_arrow():
    gp = parse("graph TD\nA-->B-->C")
    assert [e.child.name for e in gp.data["A"]] == ["B"]
    assert [e.child.name for e in gp.data["B"]] == ["C"]


def test_fanout():
    gp = parse("graph TD\nA & B --> C")
    assert [e.child.name for e in gp.data["A"]] == ["C"]
    assert [e.child.name for e in gp.data["B"]] == ["C"]


def test_labelled_edge():
    gp = parse("graph TD\nA -->|yes| B")
    assert gp.data["A"][0].label == "yes"
    assert gp.data["A"][0].is_bidirectional is False


def test_bidirectional_edge():
    gp = parse("graph TD\nA <--> B")
    assert gp.data["A"][0].is_bidirectional is True


def test_subgraph_nesting():
    gp = parse(
        """graph TD
subgraph outer
A --> B
subgraph inner
B --> C
end
end
"""
    )
    assert len(gp.subgraphs) == 2
    outer, inner = gp.subgraphs
    assert outer.name == "outer"
    assert inner.name == "inner"
    assert inner.parent is outer
    assert inner in outer.children
    assert set(outer.nodes) == {"A", "B", "C"}
    # A subgraph only picks up nodes *newly discovered* while it was open --
    # B was already known (from "A --> B") by the time "subgraph inner"
    # starts, so it isn't added to inner even though it's referenced inside
    # it; only the newly-discovered C is (confirmed against the real Go
    # binary, visually: B's node box sits outside inner's frame).
    assert set(inner.nodes) == {"C"}


def test_padding_directive():
    gp = parse("paddingX=10\npaddingY=3\ngraph TD\nA-->B")
    assert gp.padding_x == 10
    assert gp.padding_y == 3

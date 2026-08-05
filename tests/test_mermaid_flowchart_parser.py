import re

import pytest

from viewmd.mermaid.flowchart.parser import ParseError, parse, parse_node, sniff


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


@pytest.mark.parametrize("shape_source", ["B(Round)", "B{Diamond}", "B((Circle))"])
def test_non_bracket_shapes_fall_back_to_bare_label(shape_source):
    """Only `[...]` renders as a distinct shape upstream; every other mermaid
    shape syntax is silently flattened to a bare node whose name is the
    literal, unparsed text (VIEWMD-0015 req. 1 -- confirmed against the real
    Go binary, not assumed)."""
    node = parse_node(shape_source)
    assert node.name == shape_source
    assert node.has_label is False


def test_style_class_suffix():
    node = parse_node("A[Start]:::red")
    assert node.name == "A"
    assert node.style_class == "red"
    assert node.label.lines == ["Start"]


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

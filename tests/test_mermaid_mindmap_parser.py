"""Tests for the mindmap diagram parser (VIEWMD-0045)."""

from __future__ import annotations

import pytest

from viewmd.mermaid.mindmap.parser import ParseError, parse, sniff


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("mindmap\n  Root\n", True),
        ("MINDMAP\n  Root\n", True),
        ("mindmapFoo\n  Root\n", True),  # sniff is a prefix match, like the other diagrams
        ("pie\n\"A\":1", False),
        ("sequenceDiagram\nA->>B: hi", False),
        ("", False),
    ],
)
def test_sniff(source, expected):
    assert sniff(source) is expected


def test_sniff_and_parse_tolerate_leading_front_matter():
    source = "---\ntitle: x\n---\nmindmap\n  Root\n    Child\n"
    assert sniff(source) is True
    d = parse(source)
    assert d.root is not None
    assert d.root.plain == "Root"
    assert [c.plain for c in d.root.children] == ["Child"]


def test_simple_flat_tree():
    d = parse("mindmap\n  Root\n    A\n    B\n")
    assert d.root.plain == "Root"
    assert [c.plain for c in d.root.children] == ["A", "B"]
    assert d.root.children[0].children == []


def test_nested_depth():
    d = parse("mindmap\n  R\n    A\n      A1\n      A2\n    B\n")
    assert d.root.plain == "R"
    assert len(d.root.children) == 2
    a = d.root.children[0]
    assert a.plain == "A"
    assert [c.plain for c in a.children] == ["A1", "A2"]
    assert d.root.children[1].plain == "B"


def test_single_root_with_no_children():
    d = parse("mindmap\n  Only\n")
    assert d.root.plain == "Only"
    assert d.root.children == []


def test_empty_mindmap_block_raises():
    with pytest.raises(ParseError, match="at least one"):
        parse("mindmap")


@pytest.mark.parametrize(
    ("raw", "plain"),
    [
        ("(Round)", "Round"),
        ("[Square]", "Square"),
        ("((Circle))", "Circle"),
        ("{{Hexagon}}", "Hexagon"),
        (")Cloud(", "Cloud"),
        ("root((mindmap))", "mindmap"),
    ],
)
def test_shape_markers_stripped_to_plain_text(raw, plain):
    d = parse(f"mindmap\n  {raw}\n")
    assert d.root.plain == plain


def test_inline_comments_and_blank_lines_ignored():
    d = parse(
        "mindmap\n"
        "  Root %% comment\n"
        "\n"
        "    Child\n"
        "\n"
        "    Other %% trailing\n"
    )
    assert d.root.plain == "Root"
    assert [c.plain for c in d.root.children] == ["Child", "Other"]


def test_full_line_comments_ignored():
    d = parse("mindmap\n%% ignore me\n  Root\n%% also\n    Child\n")
    assert d.root.plain == "Root"
    assert [c.plain for c in d.root.children] == ["Child"]


def test_markdown_bold_italic_spans_parsed_after_shape_strip():
    d = parse("mindmap\n  ((**bold**))\n    *italic*\n    ***both***\n")
    assert d.root.plain == "bold"
    assert d.root.segments == [("bold", True, False)]
    assert d.root.children[0].segments == [("italic", False, True)]
    assert d.root.children[1].segments == [("both", True, True)]

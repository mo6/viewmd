"""Unit tests for the block-beta parser (VIEWMD-0040).

No upstream reference implementation to differentially test against
(mermaid-ascii has no block-beta support) -- hand-written against Mermaid's
own block syntax and the issue's reference examples, same posture as the
pie/quadrant/packet/kanban parsers.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from viewmd.mermaid.block.parser import ParseError, parse, sniff

FIXTURES = Path(__file__).parent / "fixtures" / "mermaid_block"


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("block-beta\nA[\"Hello\"]\n", True),
        ("BLOCK-BETA\nA[\"Hello\"]\n", True),
        ("---\ntitle: T\n---\nblock-beta\nA[\"Hello\"]\n", True),
        ("%% comment\nblock-beta\nA[\"Hello\"]\n", True),
        ("block\nA[\"Hello\"]\n", False),  # un-suffixed `block` is not this issue
        ("block-betaFoo\nA[\"Hello\"]\n", False),
        ("sequenceDiagram\nA->>B: hi", False),
        ("", False),
        ("%% just a comment", False),
    ],
)
def test_sniff(source, expected):
    assert sniff(source) == expected


def test_bare_block_declarations_in_order():
    d = parse('block-beta\n    A["Hello World"]\n    B["Goodbye"]\n')
    assert [b.id for b in d.blocks] == ["A", "B"]
    assert [b.label for b in d.blocks] == ["Hello World", "Goodbye"]
    assert [b.span for b in d.blocks] == [1, 1]
    assert [b.columns for b in d.blocks] == [None, None]
    assert d.edges == []


def test_multiple_blocks_on_one_line():
    d = parse('block-beta\n    columns 3\n    B["Left"] C["Center"] D["Right"]\n')
    assert [b.id for b in d.blocks] == ["B", "C", "D"]
    assert [b.label for b in d.blocks] == ["Left", "Center", "Right"]


def test_columns_directive_applies_to_blocks_declared_after_it():
    d = parse('block-beta\n    columns 3\n    A["Header"]:3\n    B["Left"]\n')
    assert d.blocks[0].columns == 3
    assert d.blocks[1].columns == 3
    assert d.blocks[0].span == 3


def test_mid_diagram_columns_change():
    d = parse(
        "block-beta\n"
        '    columns 3\n    A["A"] B["B"] C["C"]\n'
        '    columns 1\n    D["D"] E["E"]\n'
    )
    assert [b.columns for b in d.blocks] == [3, 3, 3, 1, 1]
    assert [b.id for b in d.blocks] == ["A", "B", "C", "D", "E"]


def test_span_suffix():
    d = parse('block-beta\n    columns 3\n    A["Header"]:3\n')
    assert d.blocks[0].id == "A"
    assert d.blocks[0].label == "Header"
    assert d.blocks[0].span == 3


def test_edge_between_declared_ids():
    d = parse('block-beta\n    A["Source"]\n    B["Target"]\n    A-->B\n')
    assert len(d.edges) == 1
    assert d.edges[0].src == "A"
    assert d.edges[0].dst == "B"


def test_edge_with_spaces_around_arrow():
    d = parse('block-beta\n    A["Source"]\n    B["Target"]\n    A --> B\n')
    assert d.edges[0].src == "A" and d.edges[0].dst == "B"


def test_edge_referencing_undeclared_id_is_a_parse_error():
    with pytest.raises(ParseError, match="undeclared id"):
        parse('block-beta\n    A["Source"]\n    A-->B\n')


def test_duplicate_block_id_is_a_parse_error():
    with pytest.raises(ParseError, match="duplicate block id"):
        parse('block-beta\n    A["One"]\n    A["Two"]\n')


def test_span_exceeding_columns_is_a_parse_error():
    with pytest.raises(ParseError, match="exceeds columns"):
        parse('block-beta\n    columns 2\n    A["Header"]:3\n')


def test_unknown_syntax_is_a_parse_error():
    with pytest.raises(ParseError, match="could not parse"):
        parse("block-beta\n    space\n")


def test_parse_tolerates_leading_front_matter_and_comments():
    d = parse(
        '---\ntitle: Ignored\n---\n'
        '%% a comment\n'
        'block-beta\n'
        '    A["Hello"] %% inline\n'
        '    B["World"]\n'
    )
    assert [b.label for b in d.blocks] == ["Hello", "World"]


def test_hello_fixture_parses():
    d = parse((FIXTURES / "hello.mmd").read_text())
    assert [b.id for b in d.blocks] == ["A", "B"]

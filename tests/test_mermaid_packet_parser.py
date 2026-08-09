import re

import pytest

from viewmd.mermaid.packet.parser import Field, ParseError, parse, sniff


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ('packet-beta\n0-15: "A"', True),
        ('PACKET-BETA\n0-15: "A"', True),
        ('packet\n0-15: "A"', True),
        ('PACKET\n0-15: "A"', True),
        ('packet-beta title Foo\n0-15: "A"', False),  # no trailing tokens allowed
        ("packetFoo\nA-->B", False),
        ("sequenceDiagram\nA->>B: hi", False),
        ("", False),
        ("%% just a comment", False),
    ],
)
def test_sniff(source, expected):
    assert sniff(source) == expected


@pytest.mark.parametrize(
    ("source", "message"),
    [
        ("", 'expected "packet-beta" or "packet" keyword'),
        ("packetFoo\n0-15: \"A\"", 'expected "packet-beta" or "packet" keyword'),
        ('packet-beta\nnot a field line', "could not parse field line"),
        ('packet-beta\n5-2: "A"', "end must be greater than or equal to start"),
        ('packet-beta\n+0: "A"', "cannot have a zero-bit field"),
        ('packet-beta\n0-7: "A"\n9-15: "B"', "not contiguous, it should start from 8"),
        ('packet-beta\n0-7: "A"\n7-15: "B"', "not contiguous, it should start from 8"),
    ],
)
def test_parse_errors(source, message):
    with pytest.raises(ParseError, match=re.escape(message)):
        parse(source)


def test_empty_packet_has_no_fields():
    d = parse("packet-beta")
    assert d.fields == []
    assert d.title == ""


def test_multi_bit_field():
    d = parse('packet-beta\n0-15: "Source Port"')
    assert d.fields == [Field(start=0, end=15, label="Source Port")]


def test_single_bit_shorthand():
    d = parse('packet-beta\n0: "Flag"')
    assert d.fields == [Field(start=0, end=0, label="Flag")]


def test_declaration_order_preserved():
    d = parse('packet-beta\n0-7: "A"\n8-15: "B"\n16-23: "C"')
    assert [f.label for f in d.fields] == ["A", "B", "C"]


def test_bits_shorthand_from_zero():
    d = parse('packet-beta\n+8: "A"')
    assert d.fields == [Field(start=0, end=7, label="A")]


def test_bits_shorthand_continues_from_previous_field():
    d = parse('packet-beta\n+8: "A"\n+8: "B"')
    assert d.fields == [
        Field(start=0, end=7, label="A"),
        Field(start=8, end=15, label="B"),
    ]


def test_bits_shorthand_mixed_with_explicit_ranges():
    d = parse('packet-beta\n+8: "Type"\n+8: "Code"\n16-31: "Checksum"')
    assert d.fields == [
        Field(start=0, end=7, label="Type"),
        Field(start=8, end=15, label="Code"),
        Field(start=16, end=31, label="Checksum"),
    ]


def test_bare_packet_keyword():
    d = parse('packet\n0-15: "A"')
    assert d.fields == [Field(start=0, end=15, label="A")]


def test_title_on_its_own_line():
    d = parse('packet-beta\n    title UDP Packet\n0-15: "A"')
    assert d.title == "UDP Packet"


def test_no_title_line_leaves_title_empty():
    d = parse('packet-beta\n0-15: "A"')
    assert d.title == ""


def test_comments_ignored():
    d = parse('packet-beta\n    %% comment\n0-15: "A"\n    %% another')
    assert len(d.fields) == 1


def test_inline_comment_truncates_line():
    d = parse('packet-beta\n0-15: "A" %% trailing note')
    assert d.fields == [Field(start=0, end=15, label="A")]


def test_blank_lines_ignored():
    d = parse('packet-beta\n\n0-15: "A"\n\n16-31: "B"\n')
    assert len(d.fields) == 2

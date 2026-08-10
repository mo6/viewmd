import re

import pytest

from viewmd.mermaid.pie.parser import ParseError, Slice, parse, sniff


@pytest.mark.parametrize(
    ("source", "message"),
    [
        ("", 'expected "pie" keyword'),
        ("pieFoo\n\"A\":1", 'expected "pie" keyword'),
        ('pie\n"bad"', "could not parse slice line: '\"bad\"'"),
        ('pie\n"A" : -5', "negative slice value not allowed"),
    ],
)
def test_parse_errors(source, message):
    with pytest.raises(ParseError, match=re.escape(message)):
        parse(source)


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ('pie\n"A" : 1', True),
        ('PIE\n"A" : 1', True),
        ('pie showData\n"A" : 1', True),
        ('pie title Some Title\n"A" : 1', True),
        ("pieFoo\nA-->B", False),
        ("sequenceDiagram\nA->>B: hi", False),
        ("", False),
        ("%% just a comment", False),
    ],
)
def test_sniff(source, expected):
    assert sniff(source) == expected


def test_empty_pie_has_no_slices():
    d = parse("pie")
    assert d.slices == []
    assert d.title == ""
    assert d.show_data is False


def test_basic_slices():
    d = parse('pie\n    "Dogs" : 386\n    "Cats" : 85\n    "Rats" : 15')
    assert d.slices == [
        Slice(label="Dogs", value=386.0),
        Slice(label="Cats", value=85.0),
        Slice(label="Rats", value=15.0),
    ]


def test_title_on_pie_line():
    d = parse('pie title Pets adopted by volunteers\n    "Dogs" : 386')
    assert d.title == "Pets adopted by volunteers"


def test_title_on_its_own_line():
    d = parse('pie\n    title Pets adopted by volunteers\n    "Dogs" : 386')
    assert d.title == "Pets adopted by volunteers"


def test_show_data_flag_present():
    d = parse('pie showData\n    "A" : 50\n    "B" : 50')
    assert d.show_data is True


def test_show_data_flag_absent():
    d = parse('pie\n    "A" : 50')
    assert d.show_data is False


def test_decimal_values():
    d = parse('pie\n    "Calcium" : 42.96\n    "Potassium" : 50.05')
    assert d.slices[0].value == 42.96
    assert d.slices[1].value == 50.05


def test_comments_ignored():
    d = parse('pie\n    %% this is a comment\n    "A" : 10\n    %% another comment')
    assert len(d.slices) == 1


def test_inline_comment_truncates_line():
    d = parse('pie\n    "A" : 10 %% trailing note')
    assert d.slices == [Slice(label="A", value=10.0)]


def test_blank_lines_ignored():
    d = parse('pie\n\n    "A" : 10\n\n    "B" : 20\n')
    assert len(d.slices) == 2

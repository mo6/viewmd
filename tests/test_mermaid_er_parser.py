import re

import pytest

from viewmd.mermaid.er.parser import Cardinality, ParseError, parse, sniff


@pytest.mark.parametrize(
    ("source", "message"),
    [
        ("", 'expected "erDiagram" keyword'),
        ("A ||--o{ B : places", 'expected "erDiagram" keyword'),
        ("erDiagram\ngarbage line !!", 'invalid syntax: "garbage line !!"'),
        ("erDiagram\nA {\n  string name\n", "unclosed attribute block (missing '}')"),
        ("erDiagram\nA {\n  string\n}", 'attribute needs a type and name: "string"'),
        ("erDiagram\nA {\n  string name BOGUS\n}", 'unexpected attribute tokens "BOGUS"'),
        ("erDiagram\nsubgraph foo", "er subgraphs are not supported"),
        ("erDiagram\nend", "er subgraphs are not supported"),
    ],
)
def test_parse_errors(source, message):
    with pytest.raises(ParseError, match=re.escape(message)):
        parse(source)


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("erDiagram\nA ||--o{ B : places", True),
        ("ERDIAGRAM\nA ||--o{ B : places", True),
        ("---\ntitle: T\n---\nerDiagram\nA ||--o{ B : places", True),
        ("erDiagramFoo\nA-->B", False),
        ("sequenceDiagram\nA->>B: hi", False),
        ("", False),
        ("%% just a comment", False),
    ],
)
def test_sniff(source, expected):
    assert sniff(source) == expected


def test_parse_tolerates_leading_front_matter():
    d = parse('---\ntitle: Ignored\n---\nerDiagram\nA ||--o{ B : places')
    assert [e.name for e in d.entities] == ["A", "B"]


def test_statement_less_diagram_is_valid():
    d = parse("erDiagram")
    assert d.entities == []
    assert d.relationships == []


def test_entity_with_attributes_and_alias():
    d = parse('erDiagram\nCUST["Customer"] {\n  string name\n  string id PK\n}')
    assert len(d.entities) == 1
    e = d.entities[0]
    assert e.name == "CUST"
    assert e.display == "Customer"
    assert [(a.type, a.name, a.keys) for a in e.attributes] == [
        ("string", "name", []),
        ("string", "id", ["PK"]),
    ]


def test_relationship_auto_creates_undeclared_entities():
    d = parse("erDiagram\nA ||--o{ B : places")
    assert [e.name for e in d.entities] == ["A", "B"]
    assert len(d.relationships) == 1
    rel = d.relationships[0]
    assert rel.left == "A"
    assert rel.right == "B"
    assert rel.left_card is Cardinality.ONLY_ONE
    assert rel.right_card is Cardinality.ZERO_OR_MORE
    assert rel.identifying is True
    assert rel.label == "places"


def test_dashed_relationship_is_not_identifying():
    d = parse("erDiagram\nA }o..o{ B : loose")
    assert d.relationships[0].identifying is False


def test_word_cardinality_and_optionally_to():
    d = parse("erDiagram\nA one or many optionally to zero or one B : maybe")
    rel = d.relationships[0]
    assert rel.left_card is Cardinality.ONE_OR_MORE
    assert rel.right_card is Cardinality.ZERO_OR_ONE
    assert rel.identifying is False


def test_lone_entity_declaration():
    d = parse("erDiagram\nLONE\nLONE2 alias2")
    assert [(e.name, e.display) for e in d.entities] == [("LONE", "LONE"), ("LONE2", "alias2")]


def test_empty_attribute_block_is_lone_entity():
    d = parse("erDiagram\nEMPTY {}")
    assert [e.name for e in d.entities] == ["EMPTY"]
    assert d.entities[0].attributes == []


def test_style_and_accessibility_lines_are_ignored():
    d = parse(
        "erDiagram\n"
        "direction LR\n"
        "accTitle: my diagram\n"
        "accDescr: some description\n"
        "classDef foo fill:#f00\n"
        "A ||--o{ B : places\n"
        "class A foo\n"
    )
    assert [e.name for e in d.entities] == ["A", "B"]


def test_comment_stripped_but_quoted_percent_kept():
    d = parse('erDiagram\n%% a comment\nA ||--o{ B : "100%% done"')
    assert d.relationships[0].label == "100%% done"

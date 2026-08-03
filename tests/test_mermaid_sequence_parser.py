import re

import pytest

from viewmd.mermaid.sequence.parser import ParseError, parse, sniff


@pytest.mark.parametrize(
    ("source", "message"),
    [
        ("", "empty input"),
        ("A->>B: Hello", 'expected "sequenceDiagram" keyword'),
        ("sequenceDiagram", "no participants found"),
        (
            "sequenceDiagram\nparticipant Alice\nparticipant Alice\nAlice->>Bob: Hi",
            'duplicate participant "Alice"',
        ),
        ("sequenceDiagram\nA->>B: hi\nend", '"end" without a matching fragment opener'),
        ("sequenceDiagram\nA->>B: hi\nelse", '"else" outside a matching alt block'),
        ("sequenceDiagram\nloop retry\nA->>B: hi", 'unclosed fragment: missing 1 "end"'),
        ("sequenceDiagram\ngarbage line !!", 'invalid syntax: "garbage line !!"'),
    ],
)
def test_parse_errors(source, message):
    with pytest.raises(ParseError, match=re.escape(message)):
        parse(source)


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("sequenceDiagram\nA->>B: Hello", True),
        ("SEQUENCEDIAGRAM\nA->>B: Hello", True),
        ("sequenceDiagramFoo-->B", False),
        ("graph LR\nA-->B", False),
        ("", False),
        ("%% Just a comment", False),
    ],
)
def test_sniff(source, expected):
    assert sniff(source) == expected

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
        ("---\ntitle: T\n---\nsequenceDiagram\nA->>B: Hello", True),
        ("sequenceDiagramFoo-->B", False),
        ("graph LR\nA-->B", False),
        ("", False),
        ("%% Just a comment", False),
    ],
)
def test_sniff(source, expected):
    assert sniff(source) == expected


@pytest.mark.parametrize(
    ("source", "expected_ids", "expected_labels"),
    [
        (
            "sequenceDiagram\nactor U\nU->>B: hi",
            ["U", "B"],
            ["U", "B"],
        ),
        (
            "sequenceDiagram\nactor U as User\nparticipant CU as Gateway\nU->>CU: hi",
            ["U", "CU"],
            ["User", "Gateway"],
        ),
        (
            # Quoted-name / as-label form — same capture groups as participant.
            'sequenceDiagram\nactor "Alice Smith" as A\n"Alice Smith"->>B: hi',
            ["Alice Smith", "B"],
            ["A", "B"],
        ),
    ],
)
def test_actor_synonym_for_participant(source, expected_ids, expected_labels):
    sd = parse(source)
    assert [p.id for p in sd.participants] == expected_ids
    assert [p.label for p in sd.participants] == expected_labels


def test_parse_tolerates_leading_front_matter():
    sd = parse("---\ntitle: Ignored\n---\nsequenceDiagram\nA->>B: Hello")
    assert [p.id for p in sd.participants] == ["A", "B"]


def test_actor_declaration_matches_participant_declaration():
    """actor and participant with the same args must yield identical participants."""
    via_actor = parse("sequenceDiagram\nactor U as User\nU->>CU: hi")
    via_participant = parse("sequenceDiagram\nparticipant U as User\nU->>CU: hi")
    assert [(p.id, p.label) for p in via_actor.participants] == [
        (p.id, p.label) for p in via_participant.participants
    ]


def test_actor_as_participant_name_still_parses_as_message():
    """A participant literally named `actor` must not be eaten by the keyword."""
    sd = parse("sequenceDiagram\nactor->>B: hi")
    assert [p.id for p in sd.participants] == ["actor", "B"]
    assert len(sd.messages) == 1
    assert sd.messages[0].from_.id == "actor"
    assert sd.messages[0].to.id == "B"


def test_participant_is_actor_flag():
    """VIEWMD-0020: the renderer needs to tell an `actor` declaration apart
    from a `participant` one to draw its stick-figure glyph."""
    sd = parse("sequenceDiagram\nactor U as User\nparticipant CU as Gateway\nU->>CU: hi")
    assert [p.is_actor for p in sd.participants] == [True, False]


def test_implicit_participant_is_not_an_actor():
    """A participant introduced only by a message (never declared) defaults to
    a plain box, not a stick figure."""
    sd = parse("sequenceDiagram\nA->>B: hi")
    assert [p.is_actor for p in sd.participants] == [False, False]

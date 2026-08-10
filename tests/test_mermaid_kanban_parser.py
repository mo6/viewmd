from pathlib import Path

import pytest

from viewmd.mermaid.kanban.parser import ParseError, parse, sniff

FIXTURES = Path(__file__).parent / "fixtures" / "mermaid_kanban"


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("kanban\n  Todo\n", True),
        ("KANBAN\n  Todo\n", True),
        ("kanbanFoo\n  Todo\n", True),  # sniff is a prefix match, like the other diagrams' sniff
        ("pie\n\"A\":1", False),
        ("sequenceDiagram\nA->>B: hi", False),
        ("", False),
    ],
)
def test_sniff(source, expected):
    assert sniff(source) == expected


def test_sniff_and_parse_tolerate_leading_front_matter():
    source = (FIXTURES / "front_matter.mmd").read_text()
    assert sniff(source) is True
    board = parse(source)
    assert [c.label for c in board.columns] == ["Todo"]


def test_bare_column_declaration():
    board = parse("kanban\n  Todo\n    [A card]\n")
    assert board.columns[0].id == "Todo"
    assert board.columns[0].label == "Todo"


def test_bracketed_column_declaration_with_no_id():
    board = parse("kanban\n  [In progress]\n    [A card]\n")
    assert board.columns[0].id == "In progress"
    assert board.columns[0].label == "In progress"


def test_bracketed_column_declaration_with_id():
    board = parse("kanban\n  id9[Ready for deploy]\n    [A card]\n")
    assert board.columns[0].id == "id9"
    assert board.columns[0].label == "Ready for deploy"


def test_bare_bracketed_card():
    board = parse("kanban\n  Todo\n    [Create Documentation]\n")
    card = board.columns[0].cards[0]
    assert card.label == "Create Documentation"


def test_id_prefixed_card():
    board = parse("kanban\n  Todo\n    docs[Create Blog]\n")
    card = board.columns[0].cards[0]
    assert card.id == "docs"
    assert card.label == "Create Blog"


def test_cards_collected_in_declaration_order_under_their_column():
    board = parse(
        "kanban\n"
        "  Todo\n"
        "    [First]\n"
        "    [Second]\n"
        "  Done\n"
        "    [Third]\n"
    )
    assert [c.label for c in board.columns[0].cards] == ["First", "Second"]
    assert [c.label for c in board.columns[1].cards] == ["Third"]


@pytest.mark.parametrize(
    ("meta", "expected"),
    [
        ("@{ ticket: MC-2038, assigned: 'K.Sveidqvist', priority: 'High' }",
         {"ticket": "MC-2038", "assigned": "K.Sveidqvist", "priority": "High"}),
        ("@{ assigned: 'knsv' }", {"assigned": "knsv"}),
        ("@{ assigned: knsv }", {"assigned": "knsv"}),  # unquoted value
        ("@{ priority: 'Very Low' }", {"priority": "Very Low"}),
    ],
)
def test_metadata_parsing(meta, expected):
    board = parse(f"kanban\n  Todo\n    id1[A card]{meta}\n")
    card = board.columns[0].cards[0]
    for key, value in expected.items():
        assert getattr(card, key) == value


def test_unrecognized_metadata_key_is_ignored_not_a_parse_failure():
    board = parse("kanban\n  Todo\n    id1[A card]@{ unknownKey: 'x', ticket: T-1 }\n")
    card = board.columns[0].cards[0]
    assert card.ticket == "T-1"


def test_duplicate_ids_across_columns_do_not_raise():
    board = parse(
        "kanban\n"
        "  Done\n"
        "    id3[Update DB function]\n"
        "  Can't reproduce\n"
        "    id3[Weird flickering in Firefox]\n"
    )
    assert board.columns[0].cards[0].id == "id3"
    assert board.columns[1].cards[0].id == "id3"
    assert board.columns[0].cards[0].label != board.columns[1].cards[0].label


def test_full_reference_example_parses():
    board = parse((FIXTURES / "reference.mmd").read_text())
    assert [c.label for c in board.columns] == [
        "Todo", "In progress", "Ready for deploy", "Ready for test", "Done", "Can't reproduce",
    ]
    assert sum(len(c.cards) for c in board.columns) == 10


def test_unterminated_metadata_block_raises():
    with pytest.raises(ParseError, match="unterminated metadata block"):
        parse("kanban\n  Todo\n    id1[A card]@{ ticket: T-1\n")


def test_malformed_card_line_raises():
    with pytest.raises(ParseError, match="could not parse card line"):
        parse("kanban\n  Todo\n    not a valid card line\n")


def test_no_columns_raises():
    with pytest.raises(ParseError, match="expected at least one column"):
        parse("kanban\n")


def test_not_a_kanban_diagram_raises():
    with pytest.raises(ParseError, match='expected "kanban" keyword'):
        parse("pie\n\"A\": 1\n")

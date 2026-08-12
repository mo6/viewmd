"""Parser unit tests for the gitGraph diagram type (VIEWMD-0042)."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from viewmd.mermaid.gitgraph.parser import ParseError, parse, sniff

FIXTURES = Path(__file__).parent / "fixtures" / "mermaid_gitgraph"


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ('gitGraph\n    commit id: "A"\n', True),
        ('GITGRAPH\n    commit id: "A"\n', True),
        ('gitGraph LR:\n    commit id: "A"\n', True),
        ('---\ntitle: T\n---\ngitGraph\n    commit id: "A"\n', True),
        ('gitGraphFoo\n    commit id: "A"\n', False),
        ("sequenceDiagram\nA->>B: hi", False),
        ("", False),
        ("%% just a comment", False),
    ],
)
def test_sniff(source, expected):
    assert sniff(source) == expected


def test_commit_id_appends_to_current_branch_at_next_column():
    graph = parse('gitGraph\n    commit id: "A"\n    commit id: "B"\n')
    assert len(graph.branches) == 1
    main = graph.branches[0]
    assert main.name == "main"
    assert [(c.id, c.label, c.column) for c in main.commits] == [
        ("A", "A", 0),
        ("B", "B", 1),
    ]


def test_branch_creates_new_lane_and_switches_current_branch():
    graph = parse(
        'gitGraph\n    commit id: "A"\n    branch develop\n    commit id: "B"\n'
    )
    assert [b.name for b in graph.branches] == ["main", "develop"]
    main, develop = graph.branches
    assert main.commits[0].id == "A"
    # The new commit landed on develop (the branch just switched to), not main.
    assert develop.commits[0].id == "B"
    assert len(main.commits) == 1


def test_branch_duplicate_name_is_a_parse_error():
    with pytest.raises(ParseError, match=re.escape('branch "develop" already exists')):
        parse('gitGraph\n    branch develop\n    branch develop\n    commit id: "A"\n')


def test_checkout_switches_without_adding_a_column():
    graph = parse(
        'gitGraph\n    commit id: "A"\n    branch develop\n    commit id: "B"\n'
        '    checkout main\n    commit id: "C"\n'
    )
    main, develop = graph.branches
    assert [c.id for c in main.commits] == ["A", "C"]
    assert [c.column for c in main.commits] == [0, 2]
    assert [c.id for c in develop.commits] == ["B"]


def test_checkout_of_undeclared_branch_is_a_parse_error():
    with pytest.raises(ParseError, match="undeclared branch"):
        parse('gitGraph\n    commit id: "A"\n    checkout develop\n')


def test_merge_with_explicit_id_adds_commit_and_connector():
    graph = parse(
        'gitGraph\n    commit id: "A"\n    branch develop\n    commit id: "B"\n'
        '    checkout main\n    merge develop id: "M"\n'
    )
    main, develop = graph.branches
    assert main.commits[-1].id == "M"
    assert main.commits[-1].label == "M"
    # One connector for the branch point, one for the merge.
    assert len(graph.connectors) == 2
    merge_conn = graph.connectors[-1]
    assert merge_conn.owner_row == main.row
    assert merge_conn.other_row == develop.row
    assert merge_conn.column == main.commits[-1].column


def test_merge_with_id_colliding_an_earlier_commit_id_is_a_parse_error():
    # A merge's id: shares the same commit_owner table as a plain commit's --
    # a collision must be rejected, not silently overwrite the id -> lane
    # mapping a later cherry-pick relies on to find the right source lane.
    with pytest.raises(ParseError, match=re.escape('duplicate commit id "A"')):
        parse(
            'gitGraph\n    branch develop\n    commit id: "A"\n'
            '    checkout main\n    merge develop id: "A"\n'
        )


def test_merge_without_explicit_id_still_adds_a_commit_and_connector():
    graph = parse(
        'gitGraph\n    commit id: "A"\n    branch develop\n    commit id: "B"\n'
        "    checkout main\n    merge develop\n"
    )
    main, develop = graph.branches
    assert main.commits[-1].id == ""
    assert len(graph.connectors) == 2


def test_merge_of_undeclared_branch_is_a_parse_error():
    with pytest.raises(ParseError, match="undeclared branch"):
        parse('gitGraph\n    commit id: "A"\n    merge develop\n')


def test_cherry_pick_labels_commit_as_id_cherry():
    graph = parse(
        'gitGraph\n    commit id: "A"\n    branch develop\n    commit id: "B"\n'
        '    checkout main\n    cherry-pick id: "B"\n'
    )
    main, develop = graph.branches
    picked = main.commits[-1]
    assert picked.label == "B-cherry"


def test_cherry_pick_references_a_commit_id_on_a_different_lane():
    """A cherry-pick's source commit id can live on any lane, not just the
    current one -- the connector must cross lanes back to wherever that
    commit id was originally declared."""
    graph = parse(
        'gitGraph\n    commit id: "A"\n    branch develop\n    commit id: "B"\n'
        '    checkout main\n    cherry-pick id: "B"\n'
    )
    main, develop = graph.branches
    connector = graph.connectors[-1]
    assert connector.owner_row == main.row
    assert connector.other_row == develop.row
    assert connector.column == main.commits[-1].column


def test_cherry_pick_of_undeclared_commit_id_is_a_parse_error():
    with pytest.raises(ParseError, match="undeclared commit"):
        parse('gitGraph\n    commit id: "A"\n    cherry-pick id: "nope"\n')


def test_cherry_pick_requires_an_id_attribute():
    with pytest.raises(ParseError, match="requires an id"):
        parse('gitGraph\n    commit id: "A"\n    cherry-pick\n')


def test_tag_is_captured_on_the_commit():
    graph = parse('gitGraph\n    commit id: "A" tag: "v1.0"\n')
    assert graph.branches[0].commits[0].tag == "v1.0"


def test_commit_without_tag_has_none():
    graph = parse('gitGraph\n    commit id: "A"\n')
    assert graph.branches[0].commits[0].tag is None


@pytest.mark.parametrize("orientation", ["TB", "BT", "RL"])
def test_non_lr_orientation_is_a_parse_error(orientation):
    with pytest.raises(ParseError, match="not supported"):
        parse(f'gitGraph {orientation}:\n    commit id: "A"\n')


def test_bare_commit_with_no_id_gets_a_random_4char_hex_id():
    graph = parse("gitGraph\n    commit\n    commit\n    commit\n")
    main = graph.branches[0]
    ids = [c.id for c in main.commits]
    assert len(ids) == 3
    assert len(set(ids)) == 3  # each commit gets its own random id
    for seq, id_ in enumerate(ids):
        assert re.fullmatch(rf"{seq}-[0-9a-f]{{4}}", id_)
        assert id_ == main.commits[ids.index(id_)].label


def test_sniff_and_parse_tolerate_leading_front_matter():
    source = (FIXTURES / "front_matter.mmd").read_text()
    assert sniff(source) is True
    graph = parse(source)
    assert [c.id for c in graph.branches[0].commits] == ["A", "B"]


def test_empty_input_is_a_parse_error():
    with pytest.raises(ParseError, match="empty input"):
        parse("")


def test_garbage_line_is_a_parse_error():
    with pytest.raises(ParseError, match="invalid syntax"):
        parse('gitGraph\n    commit id: "A"\n    garbage line !!\n')

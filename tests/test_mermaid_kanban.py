"""Tests for the kanban board renderer (VIEWMD-0034).

No upstream reference implementation to differentially test against (mermaid-
ascii has no kanban support) -- the reference fixture is the maintainer-
supplied example from the issue's mock-up, hand-verified against it
character-for-character, same posture as the pie/quadrant renderers' own
hand-authored fixtures.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from viewmd.mermaid.kanban.parser import parse
from viewmd.mermaid.kanban.renderer import render

FIXTURES = Path(__file__).parent / "fixtures" / "mermaid_kanban"

_ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")


def _strip_ansi(s: str) -> str:
    return _ANSI_RE.sub("", s)


# ---------------------------------------------------------------------------
# Plain layout: golden fixture (requirements 6, 7, maintainer sign-off a/c/d)
# ---------------------------------------------------------------------------


def test_reference_example_matches_fixture():
    board = parse((FIXTURES / "reference.mmd").read_text())
    out = _strip_ansi(render(board))
    assert out == (FIXTURES / "reference.out").read_text().rstrip("\n")


def test_columns_hug_their_own_content_height():
    # Maintainer sign-off (d): "Todo" (2 short cards) must not be padded down
    # to "Done"'s much taller box -- its own bottom border closes long before
    # the tallest column's does.
    board = parse((FIXTURES / "reference.mmd").read_text())
    lines = render(board).splitlines()
    todo_bottom_row = next(i for i, ln in enumerate(lines) if ln.startswith("└"))
    done_bottom_row = len(lines) - 1
    assert todo_bottom_row < done_bottom_row


def test_uniform_card_width_across_columns():
    # Maintainer sign-off (a): every card box is the same width, regardless
    # of which column it's in.
    board = parse((FIXTURES / "reference.mmd").read_text())
    plain = _strip_ansi(render(board))
    card_top_borders = {ln.strip() for ln in plain.splitlines() if ln.strip().startswith("┌")
                         and "┌" in ln.strip()[1:]}
    widths = {len(b) for b in card_top_borders}
    assert len(widths) == 1


def test_long_label_word_wraps_across_multiple_lines_not_truncated():
    board = parse(
        "kanban\n  Todo\n"
        "    id6[Create renderer so that it works in all cases. We also add some "
        "extra text here for testing purposes. And some more just for the extra flare.]\n"
    )
    out = _strip_ansi(render(board))
    assert "Create renderer so that it works in all cases." not in out  # would overflow a line
    assert "flare" in out
    for word in ("Create", "renderer", "flare"):
        assert word in out


def test_card_with_no_metadata_omits_the_metadata_line():
    # Maintainer sign-off (c): no blank metadata line reserved -- the card
    # box is exactly 3 rows tall (top border, one label line, bottom
    # border), not 4.
    board = parse("kanban\n  Todo\n    [Plain card]\n")
    out = _strip_ansi(render(board))
    lines = out.splitlines()
    card_top = next(i for i, ln in enumerate(lines) if ln.find("┌") > 0)
    card_label_line = lines[card_top + 1]
    card_bottom_line = lines[card_top + 2]
    assert "└" in card_bottom_line
    assert "Plain card" in card_label_line


# ---------------------------------------------------------------------------
# Metadata line layout (requirement 8)
# ---------------------------------------------------------------------------


def test_metadata_line_priority_left_ticket_left_assigned_right():
    board = parse(
        "kanban\n  Todo\n"
        "    id1[Card]@{ ticket: T-1, assigned: 'Alice', priority: 'High' }\n"
    )
    out = _strip_ansi(render(board))
    meta_line = next(ln for ln in out.splitlines() if "T-1" in ln)
    assert meta_line.index("[H]") < meta_line.index("T-1") < meta_line.index("Alice")
    # The card's own right border ("│  │") follows right after "Alice" --
    # right-aligned within the card's content area, not the terminal line.
    assert meta_line.rstrip().endswith("Alice │  │")


def test_metadata_line_assigned_only_is_right_aligned():
    board = parse("kanban\n  Todo\n    id1[Card]@{ assigned: 'Alice' }\n")
    out = _strip_ansi(render(board))
    meta_line = next(ln for ln in out.splitlines() if "Alice" in ln)
    assert meta_line.rstrip().endswith("Alice │  │")
    assert "[" not in meta_line


@pytest.mark.parametrize(
    ("priority", "token"),
    [
        ("Very Low", "[VL]"),
        ("Low", "[L]"),
        ("Medium", "[M]"),
        ("High", "[H]"),
        ("Very High", "[VH]"),
    ],
)
def test_priority_abbreviation_tokens(priority, token):
    board = parse(f"kanban\n  Todo\n    id1[Card]@{{ priority: '{priority}' }}\n")
    out = _strip_ansi(render(board))
    assert token in out


# ---------------------------------------------------------------------------
# Color (requirements 8a-8c)
# ---------------------------------------------------------------------------


def test_column_headers_use_categorical_palette_cycling_past_eight():
    board = parse(
        "kanban\n"
        + "".join(f"  Col{i}\n    [Card {i}]\n" for i in range(9))
    )
    out = render(board)
    bg_colors = re.findall(r"48;2;(\d+;\d+;\d+)", out)
    # 9 columns cycling an 8-hue palette: column 0 and column 8 share a hue.
    assert len(bg_colors) == 9
    assert bg_colors[0] == bg_colors[8]
    assert len(set(bg_colors)) == 8


@pytest.mark.parametrize(
    ("priority", "expected_hex"),
    [
        ("Very Low", "12;163;12"),
        ("Low", "12;163;12"),
        ("Medium", "250;178;25"),
        ("High", "236;131;90"),
        ("Very High", "208;59;59"),
    ],
)
def test_priority_status_color_mapping(priority, expected_hex):
    board = parse(f"kanban\n  Todo\n    id1[Card]@{{ priority: '{priority}' }}\n")
    out = render(board)
    assert f"38;2;{expected_hex}" in out


def test_ticket_is_colored_and_underlined():
    board = parse("kanban\n  Todo\n    id1[Card]@{ ticket: T-1 }\n")
    out = render(board)
    assert "4;38;2;57;135;229mT-1" in out or "38;2;57;135;229;4mT-1" in out


def test_assigned_uses_fixed_saturated_hue_for_every_assignee():
    # Maintainer sign-off (f): one fixed hue for all assignees, not per-name.
    board = parse(
        "kanban\n  Todo\n"
        "    id1[Card]@{ assigned: 'Alice' }\n"
        "    id2[Card2]@{ assigned: 'Bob' }\n"
    )
    out = render(board)
    assigned_colors = set(re.findall(r"38;2;(\d+;\d+;\d+)m(?:Alice|Bob)", out))
    assert len(assigned_colors) == 1


def test_color_is_strictly_additive_over_plain_layout():
    board = parse((FIXTURES / "reference.mmd").read_text())
    out = render(board)
    assert _strip_ansi(out) == (FIXTURES / "reference.out").read_text().rstrip("\n")


# ---------------------------------------------------------------------------
# Front matter tolerance (Non-goals)
# ---------------------------------------------------------------------------


def test_leading_front_matter_block_is_ignored_not_a_parse_failure():
    board = parse((FIXTURES / "front_matter.mmd").read_text())
    out = _strip_ansi(render(board))
    assert "Todo" in out
    assert "Create Documentation" in out


# ---------------------------------------------------------------------------
# ASCII mode
# ---------------------------------------------------------------------------


def test_ascii_mode_uses_plus_and_dash_border():
    board = parse("kanban\n  Todo\n    [Card]\n")
    out = _strip_ansi(render(board, use_ascii=True))
    assert "┌" not in out
    assert "+" in out and "-" in out

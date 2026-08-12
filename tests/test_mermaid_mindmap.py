"""Tests for the mindmap diagram renderer (VIEWMD-0045).

No upstream reference implementation to differentially test against
(mermaid-ascii has no mindmap support) -- fixtures in
tests/fixtures/mermaid_mindmap/ are hand-authored/visually verified, same
posture as the pie/kanban/packet ports. termaid's output is a cross-check,
not an oracle to match exactly.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

import viewmd.mermaid as mermaid
from viewmd.mermaid.mindmap.parser import parse
from viewmd.mermaid.mindmap.renderer import render
from viewmd.mermaid.preprocess import render_mermaid_blocks

FIXTURES = Path(__file__).parent / "fixtures" / "mermaid_mindmap"
_ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")


def _strip_ansi(s: str) -> str:
    return _ANSI_RE.sub("", s)


def _cases():
    for mmd in sorted(FIXTURES.glob("*.mmd")):
        for variant, use_ascii in (("unicode", False), ("ascii", True)):
            expected = mmd.with_name(f"{mmd.stem}.{variant}.out")
            if expected.exists():
                yield pytest.param(mmd, expected, use_ascii, id=f"{mmd.stem}-{variant}")


@pytest.mark.parametrize("mmd_path,expected_path,use_ascii", list(_cases()))
def test_matches_fixture(mmd_path, expected_path, use_ascii):
    d = parse(mmd_path.read_text())
    assert render(d, use_ascii=use_ascii) == expected_path.read_text().rstrip("\n")


def test_overflow_fixture_uses_a_second_side():
    """Requirement 6: enough children that a single-direction fan would be
    too tall must spill some to the left (exact split point is open)."""
    out = (FIXTURES / "overflow.unicode.out").read_text()
    assert "Center" in out
    # Left-branching uses ╮/╯/┤-style connectors (or ASCII +).
    assert "╮" in out or "╯" in out or "┤" in out
    for label in [f"C{i}" for i in range(9)]:
        assert label in out


def test_nested_left_overflow_keeps_fan_column_aligned():
    """Composition of req 5+6: a multi-line left subtree must keep the
    outer root-fan column vertically aligned (3-column suffixes on every
    row). Inner subtree fans sit further left and are ignored here."""
    out = render(parse((FIXTURES / "overflow_nested_left.mmd").read_text()))
    lines = out.splitlines()
    center_idx = next(line.index("Center") for line in lines if "Center" in line)
    outer_marks = []
    for line in lines:
        col = None
        for i, ch in enumerate(line):
            if i < center_idx and ch in "╮╯┤├":
                col = i  # rightmost left-of-Center junction on this line
        if col is not None:
            outer_marks.append(col)
    assert len(outer_marks) >= 3
    assert len(set(outer_marks)) == 1, f"outer left fan column misaligned: {outer_marks}"


def test_empty_mindmap_fence_left_untouched():
    text = "```mermaid\nmindmap\n```\n"
    assert render_mermaid_blocks(text) == text


def test_malformed_mindmap_raises_mermaid_error_without_crashing_preprocess():
    # Empty body after the keyword is the parse failure mode for mindmap
    # (indentation trees otherwise accept almost any remaining content).
    with pytest.raises(mermaid.MermaidError):
        mermaid.render("mindmap")
    text = "```mermaid\nmindmap\n```\n"
    assert render_mermaid_blocks(text) == text


def test_bold_italic_labels_emit_ansi_without_literal_markers():
    src = (
        "mindmap\n"
        "  Root\n"
        "    **bold**\n"
        "    *italic*\n"
        "    ***both***\n"
        "    plain **b** and *i*\n"
    )
    out = mermaid.render(src, color=False)
    assert "*" not in _strip_ansi(out)
    assert "\x1b[1mbold\x1b[0m" in out
    assert "\x1b[3mitalic\x1b[0m" in out
    assert "\x1b[1;3mboth\x1b[0m" in out
    assert "\x1b[1mb\x1b[0m" in out
    assert "\x1b[3mi\x1b[0m" in out
    # color=False: text styling still present, no truecolor escapes.
    assert "\x1b[38;2;" not in out
    assert "\x1b[48;2;" not in out


def test_ascii_mode_uses_no_unicode_box_drawing():
    d = parse("mindmap\n  Root\n    A\n    B\n")
    out = render(d, use_ascii=True)
    assert "╭" not in out and "│" not in out and "╰" not in out
    assert "+" in out and "-" in out

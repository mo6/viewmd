"""Tests for the block-beta renderer (VIEWMD-0040).

No upstream reference implementation to differentially test against
(mermaid-ascii has no block-beta support) -- fixtures in
tests/fixtures/mermaid_block/ are the maintainer-supplied reference examples
from the issue (hello/header/grid/edge) plus the wrap and per-column-widen
cases the acceptance list asks for, hand-verified character-for-character,
same posture as the pie/quadrant/kanban renderers' hand-authored fixtures.
"""

from __future__ import annotations

from pathlib import Path

import pytest

import viewmd.mermaid as mermaid
from viewmd.mermaid.block.parser import parse
from viewmd.mermaid.block.renderer import render
from viewmd.mermaid.preprocess import MERMAID_RENDERED_INFO, render_mermaid_blocks

FIXTURES = Path(__file__).parent / "fixtures" / "mermaid_block"


def _cases():
    for mmd in sorted(FIXTURES.glob("*.mmd")):
        expected = mmd.with_suffix(".out")
        if expected.exists():
            yield pytest.param(mmd, expected, False, id=mmd.stem)
        ascii_expected = mmd.with_name(f"{mmd.stem}.ascii.out")
        if ascii_expected.exists():
            yield pytest.param(mmd, ascii_expected, True, id=f"{mmd.stem}-ascii")


@pytest.mark.parametrize("mmd_path,expected_path,use_ascii", list(_cases()))
def test_matches_fixture(mmd_path, expected_path, use_ascii):
    d = parse(mmd_path.read_text())
    assert render(d, use_ascii=use_ascii) == expected_path.read_text().rstrip("\n")


def test_wrap_fixture_puts_the_overflow_block_on_a_second_row():
    out = (FIXTURES / "wrap.out").read_text()
    lines = [ln for ln in out.splitlines() if ln.strip()]
    # Two rows of boxes: first row has two top-borders, second row has one.
    top_borders = [ln for ln in lines if "┌" in ln]
    assert top_borders[0].count("┌") == 2
    assert top_borders[1].count("┌") == 1
    assert "Three" in out


def test_widen_fixture_equalizes_width_across_rows_of_the_same_column():
    # Requirement 9: D["Tiny"] shares column 1 with B["A much longer label"]
    # and must widen to match; A["Short"] / C["Also"] stay at the minimum.
    out = (FIXTURES / "widen.out").read_text()
    tops = [ln for ln in out.splitlines() if "┌" in ln]
    assert len(tops) == 2
    # Both rows share the same per-column border widths.
    assert tops[0] == tops[1]
    tiny_line = next(ln for ln in out.splitlines() if "Tiny" in ln)
    long_line = next(ln for ln in out.splitlines() if "A much longer label" in ln)
    assert tiny_line.index("│") == long_line.index("│")
    assert tiny_line.rstrip()[-1] == long_line.rstrip()[-1]


def test_ascii_mode_uses_plus_dash_pipe_and_ascii_arrowhead():
    out = render(parse((FIXTURES / "edge.mmd").read_text()), use_ascii=True)
    assert "┌" not in out and "►" not in out
    assert "+" in out and "-" in out and ">" in out
    assert "--->" in out or "-->" in out


def test_block_beta_fence_is_recognized_and_rendered_end_to_end():
    out = mermaid.render('block-beta\n    A["Hello World"]\n    B["Goodbye"]\n')
    assert "Hello World" in out
    assert "Goodbye" in out
    assert "┌" in out


def test_malformed_block_beta_fence_raises_mermaid_error():
    with pytest.raises(mermaid.MermaidError, match="undeclared id"):
        mermaid.render('block-beta\n    A["Source"]\n    A-->B\n')


def test_malformed_block_beta_fence_is_left_untouched_by_preprocess():
    text = "```mermaid\nblock-beta\n    A[\"Source\"]\n    A-->B\n```\n"
    assert render_mermaid_blocks(text) == text


def test_renders_a_block_beta_fence_as_tagged_code():
    text = "```mermaid\nblock-beta\n    A[\"Hello World\"]\n    B[\"Goodbye\"]\n```\n"
    got = render_mermaid_blocks(text)
    assert "```mermaid\n" not in got
    assert f"```{MERMAID_RENDERED_INFO}\n" in got
    assert "Hello World" in got
    assert "┌" in got

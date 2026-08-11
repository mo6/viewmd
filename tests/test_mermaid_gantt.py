"""Tests for the gantt chart renderer (VIEWMD-0032).

No upstream reference implementation to differentially test against
(mermaid-ascii has no gantt support, Non-goals) -- fixtures are hand-authored/
hand-verified, same posture as the pie/quadrant/packet/kanban renderers.

`d1_basic` reproduces mock-up D1 ("A Gantt Diagram", the mermaid.js "basic"
reference example) byte-for-byte against the issue's own worked date math.
`d2_full_syntax` reproduces mock-up D2 ("Adding GANTT diagram functionality
to mermaid") in full -- same tasks/sections/tags/`until`/`excludes weekends`
input as the issue's mock-up -- but its exact bar/tick geometry is this
renderer's own (self-consistent) recomputation rather than a byte-for-byte
copy of the issue's illustrative D2 rendering: that rendering predates this
issue's `crit` bracket decision (needing 2 extra columns per bracketed task,
noted in the issue text as still to be "recomputed"), and separately used
calendar-day math that does not actually honor the `excludes weekends` line
its own source carries (also flagged in the issue text as an admitted gap in
that specific illustrative rendering) -- whereas requirement 8 in this port
actually skips weekends when `excludes weekends` is present, which shifts
D2's task dates (and, per requirement 7b, its total span) versus that
illustrative version. See tests/test_mermaid_gantt_parser.py for the
excludes-weekends day-math coverage in isolation.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from viewmd.mermaid.gantt.parser import ParseError, parse
from viewmd.mermaid.gantt.renderer import render

FIXTURES = Path(__file__).parent / "fixtures" / "mermaid_gantt"

_ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")


def _strip_ansi(s: str) -> str:
    return _ANSI_RE.sub("", s)


@pytest.mark.parametrize("name", ["d1_basic", "d2_full_syntax"])
def test_mockup_fixtures_match_byte_for_byte(name):
    diagram = parse((FIXTURES / f"{name}.mmd").read_text())
    out = _strip_ansi(render(diagram))
    assert out == (FIXTURES / f"{name}.out").read_text().rstrip("\n")


def test_d1_uses_week_ticks_and_d2_uses_day_ticks():
    # Requirement 7b: automatic tick-granularity switching -- the two
    # mock-ups exercise opposite branches of the same rule.
    d1 = parse((FIXTURES / "d1_basic.mmd").read_text())
    d2 = parse((FIXTURES / "d2_full_syntax.mmd").read_text())
    assert "W1" in render(d1)
    assert "W1" not in render(d2)
    assert re.search(r"\d\d-\d\d", render(d2))


def test_week_mode_anchors_dates_under_the_chart_every_4_weeks():
    # Maintainer review feedback (2026-08-11): "W<n>" labels alone don't say
    # what date the timeline starts from, unlike day mode's already-absolute
    # "MM-DD" labels -- an anchor line under the chart fixes that.
    diagram = parse((FIXTURES / "d1_basic.mmd").read_text())
    out = render(diagram)
    assert out.rstrip("\n").endswith("W1: 2014-01-01, W5: 2014-01-29")


def test_day_mode_has_no_anchor_line():
    diagram = parse((FIXTURES / "d2_full_syntax.mmd").read_text())
    out = render(diagram)
    assert ": 20" not in out.splitlines()[-1]  # no "Wn: YYYY-MM-DD" trailer


def test_section_headers_render_as_their_own_row_with_no_gridlines():
    diagram = parse((FIXTURES / "d1_basic.mmd").read_text())
    lines = render(diagram).splitlines()
    section_lines = [ln for ln in lines if ln.strip() in ("Section", "Another")]
    assert len(section_lines) == 2
    for ln in section_lines:
        assert "│" not in ln and "┬" not in ln


def test_gridlines_run_through_every_task_row_requirement_7a():
    diagram = parse((FIXTURES / "d1_basic.mmd").read_text())
    lines = render(diagram).splitlines()
    task_lines = [
        ln for ln in lines
        if ln.strip().startswith(("A task", "Another task", "Task in Another", "another task"))
    ]
    assert len(task_lines) == 4
    for ln in task_lines:
        assert "│" in ln  # at least one gridline column not covered by this task's own bar


def test_bar_glyph_takes_precedence_over_gridline():
    # "A task" spans day 0-30, which includes at least one tick column (W1
    # at day 0 itself) -- that column must show the fill glyph, not "│".
    diagram = parse((FIXTURES / "d1_basic.mmd").read_text())
    line = next(ln for ln in render(diagram).splitlines() if "A task" in ln)
    bar_start = line.index("░")
    assert line[bar_start] == "░"


def test_milestone_renders_as_a_point_glyph_not_a_bar():
    diagram = parse((FIXTURES / "d2_full_syntax.mmd").read_text())
    line = next(ln for ln in render(diagram).splitlines() if "Functionality added" in ln)
    assert line.count("◆") == 1
    assert "█" not in line and "▓" not in line and "░" not in line


def test_crit_tasks_get_bracket_markers():
    diagram = parse((FIXTURES / "d2_full_syntax.mmd").read_text())
    out = render(diagram)
    for label in (
        "Completed task in the critical line",
        "Implement parser and jison",
        "Create tests for parser",
        "Future task in critical line",
    ):
        line = next(ln for ln in out.splitlines() if label in ln)
        assert "[" in line and "]" in line


def test_use_ascii_fallback_fixture_matches():
    diagram = parse((FIXTURES / "use_ascii.mmd").read_text())
    out = render(diagram, use_ascii=True)
    assert out == (FIXTURES / "use_ascii.out").read_text().rstrip("\n")


def test_use_ascii_mode_has_no_unicode_glyphs():
    diagram = parse((FIXTURES / "use_ascii.mmd").read_text())
    out = render(diagram, use_ascii=True)
    for glyph in "█▓░◆│┬┴─":
        assert glyph not in out


def test_no_ansi_when_color_disabled():
    diagram = parse((FIXTURES / "d2_full_syntax.mmd").read_text())
    assert "\x1b[" not in render(diagram, color=False)


def test_color_disabled_by_default():
    diagram = parse((FIXTURES / "d2_full_syntax.mmd").read_text())
    assert render(diagram) == render(diagram, color=False)


def test_color_output_strips_to_the_same_plain_text():
    # Coloring must be a pure overlay -- stripping ANSI from the colored
    # render reproduces the uncolored render exactly, same invariant as the
    # pie/quadrant renderers' own color tests.
    diagram = parse((FIXTURES / "d2_full_syntax.mmd").read_text())
    assert _strip_ansi(render(diagram, color=True)) == render(diagram, color=False)


def test_color_uses_one_hue_per_status_plus_a_crit_marker_hue():
    diagram = parse((FIXTURES / "d2_full_syntax.mmd").read_text())
    out = render(diagram, color=True)
    colors = set(re.findall(r"38;2;(\d+;\d+;\d+)", out))
    # done, active, untagged, milestone, crit -- all five statuses are
    # exercised by mock-up D2 (see its Requirements coverage in the issue).
    assert len(colors) == 5


def test_crit_task_color_layers_marker_hue_onto_status_hue():
    # "Completed task in the critical line" is crit+done: its brackets carry
    # the crit hue, its fill glyphs carry the done hue, both present on the
    # same line, distinct from each other.
    diagram = parse((FIXTURES / "d2_full_syntax.mmd").read_text())
    line = next(
        ln for ln in render(diagram, color=True).splitlines()
        if "Completed task in the critical line" in ln
    )
    colors_on_line = re.findall(r"38;2;(\d+;\d+;\d+)", line)
    assert len(set(colors_on_line)) == 2


def test_color_and_use_ascii_are_independent():
    # --ascii picks the glyph set; --color tints it -- the two flags don't
    # interact, matching viewmd/mermaid/quadrant/renderer.py's convention.
    diagram = parse((FIXTURES / "d2_full_syntax.mmd").read_text())
    out = render(diagram, use_ascii=True, color=True)
    assert "\x1b[38;2;" in out
    for glyph in "█▓░◆│┬┴─":
        assert glyph not in out


def test_malformed_fence_raises_parse_error_not_a_crash():
    # A task line missing its ':' separator -- per requirement 9, this must
    # surface as a ParseError so the caller (viewmd.mermaid.render) can fall
    # back to showing the raw fence, not crash viewmd.
    with pytest.raises(ParseError):
        parse((FIXTURES / "malformed_missing_colon.mmd").read_text())

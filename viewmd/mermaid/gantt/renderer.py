"""Gantt chart renderer (VIEWMD-0032).

No upstream reference implementation to port from (mermaid-ascii has no gantt
support) -- hand-written and hand-verified against the issue's own mock-ups,
same posture as the pie/quadrant/packet/kanban renderers. Layout (label
column sizing, tick spacing/granularity, trailing axis stub) is this issue's
own design decision (requirement 6/7), pinned by the mock-up D1 fixture,
which this renderer reproduces byte-for-byte -- see
tests/test_mermaid_gantt.py.

Timeline scale: 1 character per day when the tick axis is in week mode, 2
characters per day in day mode -- not an arbitrary choice, but the minimum
needed so adjacent tick labels never collide: a "W<n>" label is at most 3
characters wide against a 7-day/7-column tick spacing, while a "MM-DD" label
is a fixed 5 characters against a 3-day tick spacing, which needs 2
characters/day (6-column spacing) to leave a label its own column of
breathing room.

Week mode's "W<n>" tick labels don't say what calendar date the timeline
starts from (day mode's "MM-DD" labels already do), so an anchor line under
the chart maps every 4th week tick to its absolute date, e.g. "W1: 2014-01-01,
W5: 2014-01-29" (maintainer review feedback, 2026-08-11).

`color=True` (maintainer review feedback, 2026-08-11) tints each task's fill
glyphs by status, approximating Mermaid's own default gantt palette the same
way `viewmd/mermaid/pie/renderer.py`'s `_SLICE_COLORS`/
`viewmd/mermaid/quadrant/renderer.py`'s `_QUADRANT_COLORS` approximate theirs
-- not a byte-for-byte match to Mermaid's SVG theme, since gantt has no
upstream reference to port from at all (see the module docstring above). The
`crit` bracket markers (requirement 5a) get their own red tint layered on top
of whichever status color the task's fill already has, mirroring how the
brackets are already a layered marker rather than a replacement glyph. Grid
lines, section headers, and the axis stay uncolored so the colored bars read
clearly against them.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import timedelta

from viewmd.mermaid.gantt.parser import GanttDiagram, Task, round_half_up
from viewmd.mermaid.grid.canvas import wrap_text_in_color
from viewmd.mermaid.textutil import width as string_width

__all__ = ["render"]

# Requirement 7b: span >= this many days uses week-granularity ticks, below
# it switches to day-granularity ticks at a 3-day interval -- "a span around
# 3-4 weeks is a reasonable boundary" per the issue's own judgment call; the
# 4-week (not 3-week) end of that range keeps mock-up D2's ~19-22 day span
# (its exact width depends on `excludes weekends` actually being honored,
# requirement 8, rather than the issue's own illustrative math -- see
# tests/test_mermaid_gantt.py) on the day-tick side of the boundary, so both
# fixtures still exercise a different branch of requirement 7b's switch.
_WEEK_MODE_THRESHOLD_DAYS = 28
_WEEK_UNIT_DAYS = 7
_DAY_UNIT_DAYS = 3

# In week mode, "W<n>" labels alone don't say which calendar date the timeline
# starts from -- unlike day mode, whose tick labels are already absolute dates.
# Every 4th week tick gets an absolute-date anchor on its own line under the
# chart (maintainer review feedback on this issue, 2026-08-11).
_WEEK_ANCHOR_INTERVAL = 4

_SECTION_INDENT = 2
_TASK_INDENT = 4
# Gutter between the longest label (indent included) and the first tick
# column -- pinned by mock-up D1: its longest row ("    Task in Another",
# 19 display columns) sits 5 columns short of the label column's own width
# (24), and that same gutter is reused for every diagram this renders.
_LABEL_GUTTER = 5

# Approximating Mermaid's own default gantt status palette (`color=True`,
# maintainer review feedback, 2026-08-11) -- one hue per status, matching the
# convention of viewmd/mermaid/pie/renderer.py's _SLICE_COLORS/
# viewmd/mermaid/quadrant/renderer.py's _QUADRANT_COLORS. `_CRIT_COLOR` tints
# only the bracket markers (requirement 5a), layered on top of whichever of
# these a task's fill already uses, not a replacement for it.
_DONE_COLOR = "58d68d"
_ACTIVE_COLOR = "5dade2"
_UNTAGGED_COLOR = "8a90dd"
_MILESTONE_COLOR = "f4d03f"
_CRIT_COLOR = "e74c3c"


@dataclass(frozen=True)
class _Glyphs:
    grid_v: str
    h: str
    tee_down: str
    tee_up: str
    done: str
    active: str
    untagged: str
    milestone: str


_UNICODE = _Glyphs(
    grid_v="│", h="─", tee_down="┬", tee_up="┴",
    done="█", active="▓", untagged="░", milestone="◆",
)
_ASCII = _Glyphs(
    grid_v="|", h="-", tee_down="+", tee_up="+",
    done="#", active="=", untagged=".", milestone="*",
)


@dataclass
class _TickAxis:
    unit_days: int
    chars_per_day: int
    tick_cols: list[int]  # column offsets (from the label column's right edge)
    labels: list[str]
    stub: int  # trailing dash run after the last tick, axis lines only

    @property
    def last_tick_col(self) -> int:
        return self.tick_cols[-1]

    @property
    def body_width(self) -> int:
        return self.last_tick_col + 1


def render(diagram: GanttDiagram, *, use_ascii: bool = False, color: bool = False) -> str:
    if not diagram.tasks:
        return diagram.title

    g = _ASCII if use_ascii else _UNICODE

    day0 = min(t.start for t in diagram.tasks)
    total_days = max(1, max(_day_offset(t.end, day0) for t in diagram.tasks))
    axis = _build_axis(day0, total_days)

    groups = _group_by_section(diagram.tasks)
    label_col_width = _label_column_width(groups)

    geometry = {id(t): _task_geometry(t, day0, axis) for t in diagram.tasks}
    body_width = max(
        axis.body_width,
        *(geom.right_edge for geom in geometry.values()),
    )

    lines: list[str] = []
    if diagram.title:
        lines.append(diagram.title)
        lines.append("")

    lines.append(_axis_label_line(axis, label_col_width, body_width))
    lines.append(_axis_tick_line(axis, g, g.tee_down, label_col_width, body_width))

    for section, tasks in groups:
        if section is not None:
            lines.append(" " * _SECTION_INDENT + section)
        for task in tasks:
            lines.append(_task_row(task, geometry[id(task)], axis, g, label_col_width, body_width,
                                    color=color))

    lines.append(_axis_tick_line(axis, g, g.tee_up, label_col_width, body_width))
    lines.append(_axis_label_line(axis, label_col_width, body_width))

    anchor_line = _week_anchor_line(axis, day0, label_col_width)
    if anchor_line is not None:
        lines.append("")
        lines.append(anchor_line)

    return "\n".join(lines)


def _day_offset(dt, day0) -> int:
    days = (dt - day0).total_seconds() / 86400
    return round_half_up(days)


def _build_axis(day0, total_days: int) -> _TickAxis:
    if total_days >= _WEEK_MODE_THRESHOLD_DAYS:
        unit_days = _WEEK_UNIT_DAYS
        chars_per_day = 1
        label_fn = lambda i: f"W{i + 1}"  # noqa: E731
    else:
        unit_days = _DAY_UNIT_DAYS
        chars_per_day = 2
        label_fn = lambda i: (day0 + timedelta(days=i * unit_days)).strftime("%m-%d")  # noqa: E731

    spacing = unit_days * chars_per_day
    num_ticks = max(1, math.ceil(total_days / unit_days))
    tick_cols = [i * spacing for i in range(num_ticks)]
    labels = [label_fn(i) for i in range(num_ticks)]
    stub = math.ceil((spacing - 1) / 2)
    return _TickAxis(unit_days=unit_days, chars_per_day=chars_per_day, tick_cols=tick_cols,
                      labels=labels, stub=stub)


def _week_anchor_line(axis: _TickAxis, day0, label_col_width: int) -> str | None:
    if axis.unit_days != _WEEK_UNIT_DAYS:
        return None
    anchors = [
        f"{axis.labels[i]}: {(day0 + timedelta(days=i * axis.unit_days)).strftime('%Y-%m-%d')}"
        for i in range(0, len(axis.tick_cols), _WEEK_ANCHOR_INTERVAL)
    ]
    return " " * label_col_width + ", ".join(anchors)


def _group_by_section(tasks: list[Task]) -> list[tuple[str | None, list[Task]]]:
    groups: list[tuple[str | None, list[Task]]] = []
    for task in tasks:
        if not groups or groups[-1][0] != task.section:
            groups.append((task.section, []))
        groups[-1][1].append(task)
    return groups


def _label_column_width(groups: list[tuple[str | None, list[Task]]]) -> int:
    longest = 0
    for section, tasks in groups:
        if section is not None:
            longest = max(longest, _SECTION_INDENT + string_width(section))
        for task in tasks:
            longest = max(longest, _TASK_INDENT + string_width(task.label))
    return longest + _LABEL_GUTTER


@dataclass(frozen=True)
class _TaskGeometry:
    col_start: int
    col_end: int  # exclusive
    right_edge: int  # right-most column this task's glyphs occupy (+1)


def _task_geometry(task: Task, day0, axis: _TickAxis) -> _TaskGeometry:
    start_off = _day_offset(task.start, day0)
    end_off = _day_offset(task.end, day0)
    col_start = start_off * axis.chars_per_day
    if task.milestone:
        return _TaskGeometry(col_start=col_start, col_end=col_start, right_edge=col_start + 1)
    col_end = max(col_start, end_off * axis.chars_per_day)
    if col_end == col_start:
        col_end = col_start + 1  # a zero-width non-milestone task still shows one cell
    right_edge = col_end + (1 if task.crit else 0)  # requirement 5a: closing bracket column
    return _TaskGeometry(col_start=col_start, col_end=col_end, right_edge=right_edge)


def _axis_label_line(axis: _TickAxis, label_col_width: int, body_width: int) -> str:
    width = label_col_width + body_width + axis.stub
    chars = [" "] * width
    for col, label in zip(axis.tick_cols, axis.labels, strict=True):
        _place(chars, label_col_width + col, label)
    return "".join(chars).rstrip()


def _axis_tick_line(axis: _TickAxis, g: _Glyphs, tee: str, label_col_width: int,
                     body_width: int) -> str:
    width = label_col_width + body_width + axis.stub
    chars = [" "] * width
    for i in range(label_col_width, width):
        chars[i] = g.h
    for col in axis.tick_cols:
        chars[label_col_width + col] = tee
    return "".join(chars).rstrip()


def _status_color(task: Task) -> str:
    if task.milestone:
        return _MILESTONE_COLOR
    if task.done:
        return _DONE_COLOR
    if task.active:
        return _ACTIVE_COLOR
    return _UNTAGGED_COLOR


def _task_row(task: Task, geom: _TaskGeometry, axis: _TickAxis, g: _Glyphs,
              label_col_width: int, body_width: int, *, color: bool = False) -> str:
    prefix = " " * _TASK_INDENT + task.label
    pad = max(label_col_width - string_width(prefix), 1)
    row: list[str] = list(prefix) + [" "] * pad

    body: list[str] = [" "] * body_width
    for col in axis.tick_cols:
        if col < body_width:
            body[col] = g.grid_v

    if task.milestone:
        fill_char = g.milestone
    elif task.done:
        fill_char = g.done
    elif task.active:
        fill_char = g.active
    else:
        fill_char = g.untagged

    # (col_start, col_end_exclusive, color_hex) spans within `body`, applied
    # after all glyph placement below so coloring never disturbs the
    # single-char-per-column placement logic those columns were computed for.
    color_spans: list[tuple[int, int, str]] = []
    status_color = _status_color(task)

    if task.milestone:
        if geom.col_start < body_width:
            body[geom.col_start] = fill_char
            color_spans.append((geom.col_start, geom.col_start + 1, status_color))
    else:
        fill_end = min(geom.col_end, body_width)
        for col in range(geom.col_start, fill_end):
            body[col] = fill_char
        if fill_end > geom.col_start:
            color_spans.append((geom.col_start, fill_end, status_color))
        if task.crit:
            if geom.col_start - 1 >= 0:
                body[geom.col_start - 1] = "["
                color_spans.append((geom.col_start - 1, geom.col_start, _CRIT_COLOR))
            elif row:
                # The task starts at the very first body column, leaving no
                # room before it for the opening bracket -- borrow the last
                # column of the label gutter instead of dropping it, so a
                # crit task pinned to the chart's own start date still gets
                # both brackets (requirement 5a).
                row[-1] = wrap_text_in_color("[", _CRIT_COLOR) if color else "["
            if geom.col_end < body_width:
                body[geom.col_end] = "]"
                color_spans.append((geom.col_end, geom.col_end + 1, _CRIT_COLOR))

    body_str = _colorize_spans(body, color_spans) if color else "".join(body)
    return "".join(row) + body_str.rstrip()


def _colorize_spans(chars: list[str], spans: list[tuple[int, int, str]]) -> str:
    if not spans:
        return "".join(chars)
    out: list[str] = []
    pos = 0
    for start, end, hex_ in sorted(spans):
        if start > pos:
            out.append("".join(chars[pos:start]))
        out.append(wrap_text_in_color("".join(chars[start:end]), hex_))
        pos = end
    out.append("".join(chars[pos:]))
    return "".join(out)


def _place(chars: list[str], start: int, text: str) -> None:
    for i, ch in enumerate(text):
        pos = start + i
        if 0 <= pos < len(chars):
            chars[pos] = ch

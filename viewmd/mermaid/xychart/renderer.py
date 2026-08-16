"""XY-chart renderer (VIEWMD-0048).

No upstream reference implementation to port from (mermaid-ascii has no
XY-chart support; termaid's own rendering is a cross-check during design,
not an oracle -- see the issue's Design notes). Layout math follows
requirement 7 (row-centered eighth-block bars, orthogonal step/staircase
lines with the same round-corner set `canvas.py:_box_glyphs("round")`
already returns) and requirement 8 (plot width between 50% and 100% of the
caller's resolved render `width`, aspect ~1:1 at the floor and never
flatter than 2:1). `poc/xychart/xychart_poc.py` is the implementation
example this module follows for the step-line and bar-fill rules; the
glyph tables and overlay order here are ported from it, not re-derived.
Color (VIEWMD-0063) is a post-layout ANSI wrap around those already-placed
glyphs. VIEWMD-0064 then splits the bar dataset's wrap per category (a small
categorical palette, cycling) and leaves a one-column gap between adjacent
bars; `_plot_geometry` and `_build_line_grid` stay on VIEWMD-0063's math.
"""

from __future__ import annotations

import math
import shutil
from dataclasses import dataclass
from functools import lru_cache

from viewmd.mermaid.grid.canvas import apply_color_spans
from viewmd.mermaid.textutil import width as string_width
from viewmd.mermaid.xychart.parser import XYChart

__all__ = ["render"]

# Unicode Block Elements U+2581-U+2588; index 0 is a space (no fill).
_EIGHTHS = " ▁▂▃▄▅▆▇█"


@dataclass(frozen=True)
class _Glyphs:
    h: str        # ─  axis / line horizontal
    v: str        # │  axis / line vertical
    bl: str       # └  axis bottom-left
    tee_d: str    # ┬  axis category tick
    line_tl: str  # ╭
    line_tr: str  # ╮
    line_bl: str  # ╰
    line_br: str  # ╯
    bar_full: str  # █ / #


# Round-corner set matches canvas.py:_box_glyphs("round"); axis box stays
# square (`└`/`┬`). ASCII collapses every eighth-block to bar_full.
_UNICODE = _Glyphs(
    h="─", v="│", bl="└", tee_d="┬",
    line_tl="╭", line_tr="╮", line_bl="╰", line_br="╯",
    bar_full="█",
)
_ASCII = _Glyphs(
    h="-", v="|", bl="+", tee_d="+",
    line_tl="+", line_tr="+", line_bl="+", line_br="+",
    bar_full="#",
)

# One trailing empty column between adjacent bars (VIEWMD-0064). `_MIN_COL`
# is fill + gap so a bar never shrinks to zero width when the gap is taken
# out of `col_width` (requirement 5).
_BAR_GAP = 1
_MIN_COL = 1 + _BAR_GAP

# Per-bar categorical palette (VIEWMD-0064), cycling by category index. Same
# "dark" dataviz hues as kanban's `_CATEGORICAL` / gitgraph's `_BRANCH_COLORS`,
# minus `_LINE_COLOR` so every bar stays distinct from the line dataset
# (requirement 2). Length > 1 and every entry unique, so `palette[i]` and
# `palette[(i+1) % n]` are never equal when the palette wraps (requirement 3).
# Slot 0 keeps VIEWMD-0063's former whole-dataset bar hue.
_BAR_COLORS = [
    "3987e5",  # blue
    "199e70",  # aqua
    "c98500",  # yellow
    "d55181",  # magenta
    "008300",  # green
    "9085e9",  # violet
    "e66767",  # red
]
_LINE_COLOR = "d95926"  # orange -- unchanged from VIEWMD-0063

# A monospace terminal cell is roughly twice as tall as it is wide, so a plot
# that's N columns wide needs roughly N/2 rows to *look* square -- raw
# column/row count parity (no correction) renders about twice as tall as
# wide instead. Requirement 8 leaves this correction as an implementation
# choice; _plot_geometry applies it so "~1:1 at the floor" and "2:1 at the
# ceiling" hold visually, not just in character counts.
_CELL_ASPECT = 2


def _terminal_width(fallback: int = 100) -> int:
    return shutil.get_terminal_size(fallback=(fallback, 24)).columns


def _plot_geometry(n_cats: int, min_col: int, target_width: int) -> tuple[int, int, int]:
    """Requirement 8: plot width in `[50% of width, 100% of width]`, overflowing
    past the ceiling when category labels cannot shrink further; height is ~1:1
    at the 50% floor and never flatter than 2:1 -- both visually, correcting
    for the terminal cell's own non-square aspect (see `_CELL_ASPECT`), not
    literal column/row count parity.

    Returns `(col_width, plot_width, n_rows)`.
    """
    target_width = max(1, target_width)
    n_cats = max(1, n_cats)
    min_col = max(_MIN_COL, min_col)
    content_w = n_cats * min_col
    floor_w = max(1, target_width // 2)
    ceil_w = max(floor_w, target_width)

    if content_w > ceil_w:
        plot_w = content_w  # overflow rather than compress below the label floor
    else:
        plot_w = max(content_w, floor_w)

    col_width = max(min_col, plot_w // n_cats)
    # Floor-division leftover can drop the snapped width back below the 50%
    # floor (e.g. 13 categories into a 100-col floor: 100//13=7 → 91). One
    # extra column per category closes that gap; with n_cats small enough
    # to not already be overflowing, it still fits under ceil_w.
    if col_width * n_cats < floor_w:
        col_width += 1
    plot_w = col_width * n_cats

    # Height stays at the visually-square (1:1) figure for the floor width
    # while width grows toward the ceiling, then lifts just enough to keep
    # the visual 2:1 floor if the plot overflows past `width`. Both figures
    # are divided by _CELL_ASPECT to correct for the terminal cell's own
    # (non-square) aspect -- see its definition above.
    n_rows_floor = max(1, floor_w // _CELL_ASPECT)
    n_rows_for_2to1 = -(-plot_w // (2 * _CELL_ASPECT))  # ceil division
    n_rows = max(n_rows_floor, n_rows_for_2to1)
    return col_width, plot_w, n_rows


def _bar_glyph(h: float, v: float, step: float, *, use_ascii: bool) -> str:
    """Eighth-block (or `#`) for a bar of height `h` at tick row `v`.

    Requirement 7: row `v`'s band is `[v - step/2, v + step/2)`; a bar
    landing exactly on the tick shows a half-block (`▄`), not a full block.
    """
    if step <= 0:
        return " "
    lo, hi = v - step / 2, v + step / 2
    full = "#" if use_ascii else "█"
    if hi <= h:
        return full
    if lo > h:
        return " "
    level = round((h - lo) / step * 8)
    if use_ascii:
        return full if level > 0 else " "
    if level <= 0:
        return " "
    if level >= 8:
        return "█"
    return _EIGHTHS[level]


def _tick_decimals(step: float) -> int:
    """How many decimal places the y-axis labels need so every row's
    value prints at a consistent precision, derived from `step` rather
    than per-tick (so `230` and `228.4` don't sit in the same column
    as different widths / precisions)."""
    if step <= 0 or abs(step - round(step)) < 1e-6:
        return 0
    for d in range(1, 4):
        scaled = step * 10**d
        if abs(scaled - round(scaled)) < 1e-6:
            return d
    return 2


def _format_tick(v: float, decimals: int = 0) -> str:
    if not math.isfinite(v):
        return "nan"
    if decimals <= 0:
        return str(int(round(v)))
    return f"{v:.{decimals}f}"


def _nice_step(raw_step: float) -> float:
    """Round `raw_step` to the nearest "nice" tick spacing -- 1, 2, or 5 times a power of ten --
    so y-axis labels land on round numbers instead of an arbitrary fraction of the axis range
    divided by the row count `_plot_geometry` happens to produce. Classic graph-labelling
    algorithm (Sparks' "nice numbers"); rounds rather than always rounding up, since a tick count
    close to the caller's target row count matters more here than guaranteeing a specific bound."""
    if raw_step <= 0 or not math.isfinite(raw_step):
        return 1.0
    exponent = math.floor(math.log10(raw_step))
    magnitude = 10.0**exponent
    residual = raw_step / magnitude
    if residual < 1.5:
        nice = 1
    elif residual < 3:
        nice = 2
    elif residual < 7:
        nice = 5
    else:
        nice = 10
    return nice * magnitude


def _auto_range(values: list[float]) -> tuple[float, float]:
    lo, hi = min(values), max(values)
    if lo == hi:
        pad = abs(lo) * 0.1 or 1.0
        return lo - pad, hi + pad
    return lo, hi


def _snap_to_row(h: float, step: float, levels: list[float]) -> float | None:
    """The data-row value whose band contains `h`, clamped to the highest row when `h` is above
    the top row's band; `levels` is expected to include the axis baseline itself (`y_min`) as its
    last entry when called for a line dataset (see `render`), so a point resting on the baseline
    snaps to `y_min` via the same band check as every other row rather than being dropped."""
    for v in levels:
        if v - step / 2 <= h < v + step / 2:
            return v
    if levels and h >= levels[0] + step / 2:
        return levels[0]
    return None


def _build_bar_grid(
    values: list[float], levels: list[float], step: float, col_width: int,
    *, use_ascii: bool,
) -> dict[float, list[str]]:
    """The gap (requirement 4) sits before every bar except the first, not
    after -- `_build_line_grid`'s own corner/vertical-stem glyph for
    category `i` (`i > 0`) only ever lands at that category's *leading*
    column (`i * col_width`), never elsewhere in its span, so reserving that
    exact column as the gap keeps a combo chart's bar fill out of the one
    column a line dataset can overwrite (finding 1 against this issue --
    with the gap trailing instead, at `_MIN_COL` a bar's lone fillable
    column *was* that vulnerable one, so a line peak/trough could erase the
    bar entirely). Consecutive categories still read as "one column between
    adjacent bars" since each shares its own leading gap with its left
    neighbor's fill; the first category has nothing to its left, so it gets
    no gap and fills its whole span, and the last bar ends up flush against
    the plot's right edge -- both match this issue's own mockup above.
    """
    n = len(values)
    total_w = n * col_width
    grid = {lv: [" "] * total_w for lv in levels}
    for i, h in enumerate(values):
        fill_w = col_width if i == 0 else max(1, col_width - _BAR_GAP)
        col0 = i * col_width + (col_width - fill_w)
        col1 = col0 + fill_w
        for lv in levels:
            ch = _bar_glyph(h, lv, step, use_ascii=use_ascii)
            if ch == " ":
                continue
            for c in range(col0, col1):
                grid[lv][c] = ch
    return grid


def _build_line_grid(
    values: list[float], levels: list[float], step: float, col_width: int,
    g: _Glyphs,
) -> dict[float, list[str]]:
    n = len(values)
    total_w = n * col_width
    grid = {lv: [" "] * total_w for lv in levels}
    snapped = [_snap_to_row(h, step, levels) for h in values]
    # Runs of consecutive equal (snapped) values merge into one flat span.
    runs: list[tuple[int, int, float]] = []
    i = 0
    while i < n:
        v = snapped[i]
        j = i
        while j + 1 < n and snapped[j + 1] == v:
            j += 1
        if v is not None:
            runs.append((i, j + 1, v))
        i = j + 1

    for ridx, (a, b, v) in enumerate(runs):
        left_start = a * col_width if a == 0 else a * col_width + 1
        right_end = b * col_width if b == n else b * col_width
        for c in range(left_start, right_end):
            grid[v][c] = g.h
        if a > 0 and ridx > 0 and runs[ridx - 1][1] == a:
            prev_v = runs[ridx - 1][2]
            col = a * col_width
            grid[v][col] = g.line_tl if v > prev_v else g.line_bl
            lo, hi = min(v, prev_v), max(v, prev_v)
            for lv in levels:
                if lo < lv < hi:
                    grid[lv][col] = g.v
        if b < n:
            # Only if the next run exists (a gap of None-snapped values
            # would mean this run is not adjacent to runs[ridx+1]).
            if ridx + 1 < len(runs) and runs[ridx + 1][0] == b:
                next_v = runs[ridx + 1][2]
                col = b * col_width
                grid[v][col] = g.line_br if next_v > v else g.line_tr
    return grid


def _merge(
    bar_grid: dict[float, list[str]] | None,
    line_grid: dict[float, list[str]] | None,
    levels: list[float],
    total_w: int,
) -> dict[float, list[str]]:
    """Line dataset wins wherever both draw a cell (requirement 7 combo)."""
    merged = {lv: [" "] * total_w for lv in levels}
    if bar_grid is not None:
        for lv in levels:
            merged[lv] = list(bar_grid[lv])
    if line_grid is not None:
        for lv in levels:
            row = merged[lv]
            for c, ch in enumerate(line_grid[lv]):
                if ch != " ":
                    row[c] = ch
    return merged


def _bar_color(category_index: int) -> str:
    """Category `i`'s bar hue, cycling the palette (VIEWMD-0064)."""
    return _BAR_COLORS[category_index % len(_BAR_COLORS)]


@lru_cache(maxsize=2)  # g is always one of the two module-level _ASCII/_UNICODE singletons
def _bar_chars(g: _Glyphs) -> frozenset[str]:
    if g.bar_full == "#":
        return frozenset("#")
    return frozenset(_EIGHTHS[1:])  # skip the leading space


@lru_cache(maxsize=2)
def _line_chars(g: _Glyphs) -> frozenset[str]:
    return frozenset({g.h, g.v, g.line_tl, g.line_tr, g.line_bl, g.line_br})


def _color_runs(chars: list[str], classify) -> list[tuple[int, int, str]]:
    """Consecutive runs of chars mapping to the same non-None `classify(i, ch)`
    label, as `(start, end, label)` triples. Shared scan shape for both
    `_plot_color_spans` (per-bar / line glyphs in a plot row) and
    `_colorize_axis` (line glyphs stitched onto the axis row), so a future
    change to run-detection can't drift between the two."""
    runs: list[tuple[int, int, str]] = []
    i = 0
    n = len(chars)
    while i < n:
        label = classify(i, chars[i])
        if label is None:
            i += 1
            continue
        j = i + 1
        while j < n and classify(j, chars[j]) == label:
            j += 1
        runs.append((i, j, label))
        i = j
    return runs


def _plot_color_spans(chars: list[str], g: _Glyphs, col_width: int) -> list[tuple[int, int, str]]:
    """Consecutive same-color glyph runs in a plot row, as color spans.

    Bar glyphs take category `i`'s palette entry (`col_width` columns each,
    VIEWMD-0064); line glyphs stay VIEWMD-0063's one fixed hue.
    """
    bar, line = _bar_chars(g), _line_chars(g)
    col_width = max(1, col_width)

    def classify(i: int, ch: str) -> str | None:
        if ch in bar:
            return _bar_color(i // col_width)
        if ch in line:
            return _LINE_COLOR
        return None

    return _color_runs(chars, classify)


def _colorize_row(chars: list[str], g: _Glyphs, col_width: int, *, color: bool) -> str:
    if not color:
        return "".join(chars)
    return apply_color_spans(chars, _plot_color_spans(chars, g, col_width))


def _colorize_axis(
    axis_chars: list[str],
    line_baseline: list[str] | None,
    *,
    color: bool,
) -> str:
    """Wrap line-dataset glyphs stitched onto the axis; leave └/┬/─ plain."""
    if not color or line_baseline is None:
        return "".join(axis_chars)
    hex_ = _LINE_COLOR
    runs = _color_runs(line_baseline, lambda _i, ch: "line" if ch != " " else None)
    # +1 on both ends: axis_chars[0] is the bl corner, one column left of the plot columns
    # line_baseline (and every plot row) is indexed from.
    spans = [(s + 1, e + 1, hex_) for s, e, _kind in runs]
    return apply_color_spans(axis_chars, spans)


def render(chart: XYChart, *, use_ascii: bool = False, color: bool = False,
           width: int | None = None) -> str:
    g = _ASCII if use_ascii else _UNICODE
    if not chart.categories:
        return chart.title

    values: list[float] = []
    if chart.bar:
        values.extend(chart.bar)
    if chart.line:
        values.extend(chart.line)
    if chart.y_min is not None and chart.y_max is not None:
        y_min, y_max = chart.y_min, chart.y_max
        if y_min == y_max:
            y_min, y_max = _auto_range([y_min])
    elif values:
        y_min, y_max = _auto_range(values)
    else:
        y_min, y_max = 0.0, 1.0

    min_col = max(_MIN_COL, max((string_width(c) for c in chart.categories), default=1) + 1)
    target_width = width if width is not None else _terminal_width()
    col_width, plot_w, target_rows = _plot_geometry(len(chart.categories), min_col, target_width)
    # _plot_geometry's row count is chosen purely from width/aspect (requirement 8); snapping the
    # step it implies to a "nice" round number (1/2/5 x 10^k) instead of using it verbatim keeps
    # y-axis labels off arbitrary fractions like "4.8"/"9.6" at the cost of the actual row count
    # (and so the plot's exact aspect ratio) drifting a bit from that target -- deliberately, nice
    # labels matter more here than hitting the aspect figure exactly. The resulting `n_rows` can
    # exceed `target_rows` when the range doesn't divide evenly by the nice step, so the top tick
    # sits at or above `y_max` rather than clipping it.
    span = y_max - y_min
    step = _nice_step(span / target_rows) if target_rows > 0 and span > 0 else max(span, 1.0)
    n_rows = max(1, math.ceil(span / step - 1e-9)) if step > 0 else target_rows
    levels = [y_min + step * i for i in range(n_rows, 0, -1)]

    n = len(chart.categories)
    bar_grid = (
        _build_bar_grid(chart.bar, levels, step, col_width, use_ascii=use_ascii)
        if chart.bar is not None else None
    )
    # `y_min` itself is appended so a line point resting on the axis baseline snaps into its own
    # band (_snap_to_row) instead of falling through to None and being dropped; `_merge` below is
    # given the un-extended `levels` so this extra row never reaches the printed grid rows -- it's
    # pulled out separately and stitched into the axis line instead (below).
    line_grid = (
        _build_line_grid(chart.line, [*levels, y_min], step, col_width, g)
        if chart.line is not None else None
    )
    grid = _merge(bar_grid, line_grid, levels, plot_w)

    decimals = _tick_decimals(step)
    tick_labels = [_format_tick(lv, decimals) for lv in levels]
    ymin_s = _format_tick(y_min, decimals)
    label_w = max(string_width(t) for t in (*tick_labels, ymin_s))

    lines: list[str] = []
    if chart.title:
        total_w = label_w + 2 + plot_w
        title_pad = max(0, (total_w - string_width(chart.title)) // 2)
        lines.append(" " * title_pad + chart.title)
        lines.append("")

    for lv, tick in zip(levels, tick_labels, strict=True):
        pad = " " * (label_w - string_width(tick))
        plot = _colorize_row(grid[lv], g, col_width, color=color)
        lines.append(f"{pad}{tick} {g.v}{plot}")

    axis_chars = list(g.bl + (g.tee_d + g.h * (col_width - 1)) * n)
    line_baseline = (
        line_grid[y_min] if line_grid is not None and y_min in line_grid else None
    )
    if line_baseline is not None:
        for c, ch in enumerate(line_baseline):
            if ch != " ":
                axis_chars[c + 1] = ch  # +1: axis_chars[0] is g.bl, left of the plot columns
    axis = _colorize_axis(axis_chars, line_baseline, color=color)
    ymin_pad = " " * (label_w - string_width(ymin_s))
    lines.append(f"{ymin_pad}{ymin_s} {axis}")

    label_line = " " * (label_w + 1)
    for cat in chart.categories:
        # Truncate a label that somehow still exceeds its column rather than
        # letting it shove neighbors over -- overflow is supposed to have
        # already grown the column past this.
        w = string_width(cat)
        if w > col_width:
            cat = cat[:col_width]
        label_line += cat + " " * (col_width - string_width(cat))
    lines.append(label_line.rstrip())
    return "\n".join(lines)

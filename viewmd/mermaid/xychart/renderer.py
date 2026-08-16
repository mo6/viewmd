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
"""

from __future__ import annotations

import math
import shutil
from dataclasses import dataclass

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

_MIN_COL = 2


def _terminal_width(fallback: int = 100) -> int:
    return shutil.get_terminal_size(fallback=(fallback, 24)).columns


def _plot_geometry(n_cats: int, min_col: int, target_width: int) -> tuple[int, int, int]:
    """Requirement 8: plot width in `[50% of width, 100% of width]`, overflowing
    past the ceiling when category labels cannot shrink further; height is ~1:1
    at the 50% floor and never flatter than 2:1.

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

    # Height stays at the 1:1-at-floor figure while width grows toward the
    # ceiling, then lifts just enough to keep the 2:1 floor if the plot
    # overflows past `width`.
    n_rows = max(floor_w, (plot_w + 1) // 2)
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


def _auto_range(values: list[float]) -> tuple[float, float]:
    lo, hi = min(values), max(values)
    if lo == hi:
        pad = abs(lo) * 0.1 or 1.0
        return lo - pad, hi + pad
    return lo, hi


def _snap_to_row(h: float, step: float, levels: list[float]) -> float | None:
    """The data-row value whose band contains `h`, or None if `h` sits on
    or below the axis baseline."""
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
    n = len(values)
    total_w = n * col_width
    grid = {lv: [" "] * total_w for lv in levels}
    for i, h in enumerate(values):
        col0, col1 = i * col_width, (i + 1) * col_width
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
        if a > 0:
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


def render(chart: XYChart, *, use_ascii: bool = False, width: int | None = None) -> str:
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
    col_width, plot_w, n_rows = _plot_geometry(len(chart.categories), min_col, target_width)
    step = (y_max - y_min) / n_rows
    levels = [y_min + step * i for i in range(n_rows, 0, -1)]

    n = len(chart.categories)
    bar_grid = (
        _build_bar_grid(chart.bar, levels, step, col_width, use_ascii=use_ascii)
        if chart.bar is not None else None
    )
    line_grid = (
        _build_line_grid(chart.line, levels, step, col_width, g)
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
        lines.append(f"{pad}{tick} {g.v}{''.join(grid[lv])}")

    axis = g.bl + (g.tee_d + g.h * (col_width - 1)) * n
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

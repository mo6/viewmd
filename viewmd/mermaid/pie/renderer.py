"""Pie chart renderer (VIEWMD-0043).

Two renderings, chosen by the caller: a horizontal bar chart (no color, or
`--ascii`) and a circular pie (color enabled, not `--ascii`). See VIEWMD-0043's
Design notes for why a circular pie is the primary rendering here rather than
dismissed outright the way termaid's does -- and why a *monochrome* circular
pie, and two earlier outer-silhouette anti-aliasing designs (a flat ring
character, then per-cell directional tick marks), were all prototyped and
visually rejected before the quadrant-block approach below.
`poc/pie/pie_poc.py` is the implementation example this module follows; the
layout math, thresholds, and glyph tables here are ported from it, not
re-derived.
"""

from __future__ import annotations

import math
import os
import shutil

from viewmd.mermaid.grid.canvas import wrap_text_bold, wrap_text_in_color
from viewmd.mermaid.pie.parser import PieChart
from viewmd.mermaid.textutil import width as string_width

__all__ = ["render"]

# Approximating Mermaid's own default pie palette; cycles for a 7th+ slice.
_SLICE_COLORS = ["c9c9f5", "f7f4b8", "c3e876", "f5c6c6", "a8d8ea", "e0b3f0"]

# Shared between the circle grid's own layout and _default_radius's width
# prediction below, so the two can't silently drift apart.
_CIRCLE_MARGIN = 4

# Empirically-corrected default for one real terminal (macOS Terminal.app) --
# not a universal constant, since no terminal reliably reports its own
# character-cell pixel aspect ratio. VIEWMD_PIE_ASPECT overrides it.
_DEFAULT_ASPECT = 0.42

_BAR_WIDTH = 32


def render(chart: PieChart, *, use_ascii: bool = False, color: bool = False,
           width: int | None = None) -> str:
    if color and not use_ascii:
        return _render_circle(chart, width)
    return _render_bar(chart, use_ascii=use_ascii, color=color)


# ---------------------------------------------------------------------------
# Bar chart (no color, or --ascii)
# ---------------------------------------------------------------------------


def _render_bar(chart: PieChart, *, use_ascii: bool, color: bool) -> str:
    if not chart.slices:
        return wrap_text_bold(chart.title) if (chart.title and color) else chart.title

    total = sum(s.value for s in chart.slices)
    label_w = max(string_width(s.label) for s in chart.slices)
    max_v = max(s.value for s in chart.slices) or 1

    lines: list[str] = []
    if chart.title:
        lines.append(wrap_text_bold(chart.title) if color else chart.title)
        lines.append("")

    full = "#" if use_ascii else "█"
    eighths = [] if use_ascii else list(" ▏▎▍▌▋▊▉")

    for s in chart.slices:
        pct = s.value / total * 100
        filled = s.value / max_v * _BAR_WIDTH
        whole = int(filled)
        frac = filled - whole
        bar = full * whole
        if not use_ascii:
            eighth_idx = round(frac * 8)
            if eighth_idx > 0:
                bar += eighths[eighth_idx]
        suffix = f"  {pct:5.1f}%"
        if chart.show_data:
            suffix += f"  ({s.value:g})"
        pad = " " * (label_w - string_width(s.label))
        lines.append(f"{pad}{s.label}┃{bar}{suffix}")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Circular rendering (color only)
# ---------------------------------------------------------------------------


def _terminal_width(fallback: int = 100) -> int:
    return shutil.get_terminal_size(fallback=(fallback, 24)).columns


def _aspect() -> float:
    """VIEWMD-0043 requirement 5a: a one-setting escape hatch for the
    unavoidably-guessed terminal character-cell aspect ratio."""
    raw = os.environ.get("VIEWMD_PIE_ASPECT")
    if raw:
        try:
            return float(raw)
        except ValueError:
            pass
    return _DEFAULT_ASPECT


def _explicit_radius() -> int | None:
    raw = os.environ.get("VIEWMD_PIE_RADIUS")
    if raw:
        try:
            return int(raw)
        except ValueError:
            pass
    return None


def _default_radius(chart: PieChart, target_width: int) -> int:
    """60% of the largest radius whose full render (circle + legend) still
    fits `target_width` (VIEWMD-0043 requirement 5b) -- a pie at the true
    maximum reads as oversized relative to a document. `target_width` is the
    caller's resolved render width (`--width`/its default, threaded down
    from `viewmd/__main__.py`), not necessarily the raw terminal size -- a
    pie MUST size itself the same way the rest of the document does, not
    independently of it."""
    if not chart.slices:
        return 16
    legend_extra = 3 + 2 + 1 + max(string_width(s.label) for s in chart.slices)
    max_fit = (target_width - (2 * _CIRCLE_MARGIN + 1) - legend_extra) // 2
    return max(6, round(max_fit * 0.6))


# Directional quadrant-block anti-aliasing (requirement 4a): every character
# cell samples 4 sub-points against the ellipse independently and renders the
# glyph matching exactly which are inside, so every boundary cell gets a
# partial-fill glyph -- not only cells matching a specific neighbor pattern,
# which is what made the two earlier (rejected) designs read as gapped or
# spiky rather than a curve. See Design notes in VIEWMD-0043.
_QUADRANT_GLYPH = {
    (False, False, False, False): " ",
    (True, False, False, False): "▘",
    (False, True, False, False): "▝",
    (False, False, True, False): "▖",
    (False, False, False, True): "▗",
    (True, True, False, False): "▀",
    (False, False, True, True): "▄",
    (True, False, True, False): "▌",
    (False, True, False, True): "▐",
    (True, False, False, True): "▚",
    (False, True, True, False): "▞",
    (True, True, True, False): "▛",
    (True, True, False, True): "▜",
    (True, False, True, True): "▙",
    (False, True, True, True): "▟",
    (True, True, True, True): "█",
}
_QUAD_OFFSETS = [(-0.25, -0.25), (-0.25, 0.25), (0.25, -0.25), (0.25, 0.25)]  # UL, UR, LL, LR
_FILL_GLYPHS = set("▘▝▖▗▀▄▌▐▚▞▛▜▙▟█")


def _render_circle(chart: PieChart, width: int | None) -> str:
    if not chart.slices:
        return wrap_text_bold(chart.title) if chart.title else ""

    aspect = _aspect()
    target_width = width if width is not None else _terminal_width()
    radius = _explicit_radius() or _default_radius(chart, target_width)

    total = sum(s.value for s in chart.slices)
    bounds: list[tuple[float, float]] = []
    acc = 0.0
    for s in chart.slices:
        start = acc / total * 360.0
        acc += s.value
        end = acc / total * 360.0
        bounds.append((start, end))

    rx, ry = radius, max(1, round(radius * aspect))
    margin = _CIRCLE_MARGIN
    w, h = rx * 2 + 1 + margin * 2, ry * 2 + 1 + margin
    cx, cy = rx + margin, ry + margin // 2

    def angle_of(dx: float, dy: float) -> float:
        a = math.degrees(math.atan2(dx, -dy))
        return a + 360 if a < 0 else a

    def wedge_of(row_f: float, col_f: float) -> int | None:
        dx, dy = col_f - cx, row_f - cy
        nx, ny = dx / rx, dy / ry
        if nx * nx + ny * ny > 1.0:
            return None
        # Angle must use the aspect-corrected (nx, ny), not raw (dx, dy):
        # rows are compressed by `aspect` to make the circle look round on
        # screen, so an angle from unscaled dx/dy would be skewed by that
        # same compression -- wedge boundaries would land at the wrong
        # on-screen angle relative to what's drawn.
        ang = angle_of(nx, ny)
        for i, (start, end) in enumerate(bounds):
            if start <= ang < end or (i == len(bounds) - 1 and ang >= start):
                return i
        return None

    def inside(row_f: float, col_f: float) -> bool:
        dx, dy = col_f - cx, row_f - cy
        nx, ny = dx / rx, dy / ry
        return nx * nx + ny * ny <= 1.0

    grid: list[list[int | None]] = [[None] * w for _ in range(h)]
    quad_glyph: list[list[str | None]] = [[None] * w for _ in range(h)]
    for row in range(h):
        for col in range(w):
            v = wedge_of(row, col)
            grid[row][col] = v
            corners = tuple(inside(row + dr, col + dc) for dr, dc in _QUAD_OFFSETS)
            if any(corners) and not all(corners):
                # Mixed cell: center's own wedge might be None (center just
                # outside) even though part of the cell is inside -- an
                # ellipse is convex, so falling back to whichever sub-point
                # is actually inside always finds a valid wedge for color.
                color_v = v
                if color_v is None:
                    for (dr, dc), is_in in zip(_QUAD_OFFSETS, corners, strict=True):
                        if is_in:
                            color_v = wedge_of(row + dr, col + dc)
                            if color_v is not None:
                                break
                if color_v is not None:
                    grid[row][col] = color_v
                    quad_glyph[row][col] = _QUADRANT_GLYPH[corners]

    label_map: dict[tuple[int, int], str] = {}
    for s, (start, end) in zip(chart.slices, bounds, strict=True):
        pct = s.value / total * 100
        text = f"{pct:.0f}%"
        mid = math.radians((start + end) / 2)
        span = end - start
        # A wedge narrower than this can't hold its own label without
        # overlapping its neighbors -- push the label outside instead,
        # along the same mid-angle leader (requirement 6).
        out_r = 0.55 if span > 25 else 1.28
        px = cx + out_r * rx * math.sin(mid)
        py = cy - out_r * ry * math.cos(mid)
        # An outside label's reach (out_r > 1) grows with the circle's own
        # radius, but the margin around the grid does not -- at a large
        # enough radius the computed position lands outside the grid
        # entirely and silently vanishes (found by actually rendering the
        # circle at the default radius derived from a 100-column terminal,
        # not by inspection). Clamp to the nearest valid cell instead of
        # dropping the label: a slightly-crowded label beats a missing one.
        row = max(0, min(h - 1, round(py)))
        col0 = max(0, min(w - len(text), round(px) - len(text) // 2))
        for k, ch in enumerate(text):
            label_map[(row, col0 + k)] = ch

    glyph = "█"
    rows: list[str] = []
    for row in range(h):
        buf = []
        for col in range(w):
            if (row, col) in label_map:
                buf.append(wrap_text_bold(label_map[(row, col)]))
                continue
            v = grid[row][col]
            if v is None:
                buf.append(" ")
            else:
                g = quad_glyph[row][col] or glyph
                buf.append(wrap_text_in_color(g, _SLICE_COLORS[v % len(_SLICE_COLORS)]))
        rows.append("".join(buf))

    legend = [
        f"{wrap_text_in_color(glyph + glyph, _SLICE_COLORS[i % len(_SLICE_COLORS)])} {s.label}"
        for i, s in enumerate(chart.slices)
    ]
    legend_start = h // 2 - len(legend) // 2
    for i, txt in enumerate(legend):
        r = legend_start + i
        if 0 <= r < h:
            rows[r] = rows[r] + "   " + txt

    # Trim blank rows above the circle's first actual fill row (requirement
    # 6a): the top margin plus a thin outside slice's label can otherwise
    # leave a blank row, the label row, then *another* blank row before the
    # circle itself starts -- drop every blank row ahead of the first row
    # with a fill glyph, keeping any label text intact.
    first_fill = next(
        (i for i, r in enumerate(rows) if any(ch in _FILL_GLYPHS for ch in r)), len(rows)
    )
    rows = [r for r in rows[:first_fill] if r.strip()] + rows[first_fill:]

    out = []
    if chart.title:
        pad = (w - string_width(chart.title)) // 2
        out.append(" " * max(pad, 0) + wrap_text_bold(chart.title))
        out.append("")
    out.extend(rows)
    return "\n".join(out)

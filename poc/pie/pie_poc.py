#!/usr/bin/env python3
"""Proof of concept for VIEWMD-0043 (Mermaid pie charts).

Not part of the shipped `viewmd` package -- a throwaway script to validate a
*colored, circular* pie rendering against real input before committing to the
design, alongside the horizontal-bar-chart fallback for when color/unicode
isn't available (no-color terminal, `NO_COLOR` set, or `--ascii` requested).

    python3 poc/pie/pie_poc.py poc/pie/example.mmd
    python3 poc/pie/pie_poc.py poc/pie/example.mmd --color always
    python3 poc/pie/pie_poc.py poc/pie/example.mmd --color never
    python3 poc/pie/pie_poc.py poc/pie/example.mmd --color never --ascii

Circular rendering only appears when color is enabled (`--color always`, or
`--color auto` on a real tty with no `NO_COLOR`); `--color never`, a
non-tty, `NO_COLOR`, or `--ascii` all fall back to the bar chart -- see
VIEWMD-0043's "Circular pie vs. bar-chart fallback" mock-up for why: a
monochrome circular pie was tested and found not to hold up (jagged
character-grid edges, fragile terminal-font aspect-ratio assumption, only
2-3 patterns distinguishable without color).

The circle's outer silhouette is anti-aliased using quadrant block characters
(`▘▝▖▗▀▄▌▐▚▞▛▜▙▟█`, Unicode Block Elements): each cell samples 4 sub-points
against the ellipse independently and picks the matching glyph, rather than
rounding the whole cell to one color. Two earlier approaches were tried and
rejected first -- a separate border-ring character (both a flat `o` and,
worse, per-cell directional tick marks) read as a spiky, disconnected fringe
rather than a curve once actually rendered; see VIEWMD-0043's Design notes.

`--aspect` compensates for the terminal's actual character height:width
ratio, which this script cannot detect and must be given -- 0.42 is a
maintainer-verified default for one real terminal (macOS Terminal.app), not
a universal constant; a circle that looks oval means a different terminal
font, and the flag exists precisely so that's a one-flag fix, not a
report-a-bug situation.
"""

from __future__ import annotations

import argparse
import math
import os
import re
import shutil
import sys
from dataclasses import dataclass

# Margin (columns) around the circle grid on each side -- shared between
# render_circle's own layout and _default_radius's width prediction below, so
# the two can't silently drift apart.
CIRCLE_MARGIN = 4

# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------


@dataclass
class Slice:
    label: str
    value: float


@dataclass
class PieChart:
    title: str
    show_data: bool
    slices: list[Slice]


class ParseError(Exception):
    pass


_SLICE_RE = re.compile(r'^"(?P<label>[^"]*)"\s*:\s*(?P<value>-?\d+(?:\.\d+)?)\s*$')


def sniff(text: str) -> bool:
    return text.lstrip().startswith("pie")


def parse(text: str) -> PieChart:
    lines = text.splitlines()
    if not lines or not lines[0].strip().startswith("pie"):
        raise ParseError("expected a line starting with 'pie'")

    first = lines[0].strip()
    show_data = "showData" in first.split()
    title = ""
    m = re.search(r"\btitle\s+(.+)$", first)
    if m:
        title = m.group(1).strip()

    slices: list[Slice] = []
    for raw in lines[1:]:
        line = raw.split("%%", 1)[0].strip()
        if not line:
            continue
        if line.startswith("title "):
            title = line[len("title "):].strip()
            continue
        sm = _SLICE_RE.match(line)
        if not sm:
            raise ParseError(f"could not parse slice line: {raw!r}")
        value = float(sm.group("value"))
        if value < 0:
            raise ParseError(f"negative slice value not allowed: {raw!r}")
        slices.append(Slice(label=sm.group("label"), value=value))

    return PieChart(title=title, show_data=show_data, slices=slices)


# ---------------------------------------------------------------------------
# Color
# ---------------------------------------------------------------------------

# Approximating Mermaid's own default pie palette for the reference example.
SLICE_COLORS = ["c9c9f5", "f7f4b8", "c3e876", "f5c6c6", "a8d8ea", "e0b3f0"]


def _hex_to_rgb(h: str) -> tuple[int, int, int]:
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


class Colorizer:
    """Wraps text in 24-bit ANSI escapes, or passes it through unchanged.

    A single `enabled` flag gates every attribute (fg color *and* bold),
    matching poc/kanban/kanban_poc.py's Colorizer precedent: bold is not
    itself a color, but a genuinely no-color/no-ANSI terminal (piped output,
    `NO_COLOR`, `--color never`) should see plain text with zero embedded
    escapes, not a half-styled result.
    """

    def __init__(self, enabled: bool) -> None:
        self.enabled = enabled

    def fg(self, text: str, hex_: str) -> str:
        if not self.enabled or not text:
            return text
        r, g, b = _hex_to_rgb(hex_)
        return f"\x1b[38;2;{r};{g};{b}m{text}\x1b[0m"

    def bold(self, text: str) -> str:
        if not self.enabled or not text:
            return text
        return f"\x1b[1m{text}\x1b[0m"


# ---------------------------------------------------------------------------
# Bar-chart rendering (fallback: no color, or --ascii)
# ---------------------------------------------------------------------------


def render_bar(chart: PieChart, c: Colorizer, use_ascii: bool) -> str:
    if not chart.slices:
        return c.bold(chart.title) if chart.title else ""

    total = sum(s.value for s in chart.slices)
    label_w = max(len(s.label) for s in chart.slices)
    bar_w = 32
    max_v = max(s.value for s in chart.slices) or 1

    lines: list[str] = []
    if chart.title:
        lines.append(c.bold(chart.title))
        lines.append("")

    full = "#" if use_ascii else "█"
    eighths = [] if use_ascii else list(" ▏▎▍▌▋▊▉")

    for s in chart.slices:
        pct = s.value / total * 100
        filled = s.value / max_v * bar_w
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
        lines.append(f"{s.label.rjust(label_w)}┃{bar}{suffix}")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Circular rendering (color only)
# ---------------------------------------------------------------------------


def render_circle(chart: PieChart, c: Colorizer, radius: int = 16, aspect: float = 0.42) -> str:
    if not chart.slices:
        return c.bold(chart.title) if chart.title else ""

    total = sum(s.value for s in chart.slices)
    bounds: list[tuple[float, float]] = []
    acc = 0.0
    for s in chart.slices:
        start = acc / total * 360.0
        acc += s.value
        end = acc / total * 360.0
        bounds.append((start, end))

    rx, ry = radius, max(1, round(radius * aspect))
    margin = CIRCLE_MARGIN
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
        # Angle must be computed from the aspect-corrected (nx, ny), not the
        # raw grid (dx, dy): rows are compressed by `aspect` to make the
        # circle look round on screen, so an angle computed from unscaled
        # dx/dy would be skewed by that same compression -- wedge boundaries
        # would land at the wrong on-screen angle relative to what's drawn.
        ang = angle_of(nx, ny)
        for i, (start, end) in enumerate(bounds):
            if start <= ang < end or (i == len(bounds) - 1 and ang >= start):
                return i
        return None

    # Quadrant-block silhouette anti-aliasing: sample each cell at 4 sub-cell
    # points (roughly its quarter-centers, not full corners) against the
    # ellipse boundary, independently. Unlike the earlier corner-triangle
    # attempt -- which only fired on a narrow specific corner pattern and left
    # most boundary cells untouched, reading as scattered flecks -- every
    # boundary cell gets *some* glyph here: a direct 16-way lookup from which
    # of the 4 sub-points are inside vs outside, not a pattern match. Slice
    # color is still decided once per cell (from its center), so this only
    # smooths the *outer* silhouette, not wedge-to-wedge internal boundaries
    # -- that was the specific ask, and keeps this prototype's scope matched
    # to what it's testing.
    QUADRANT_GLYPH = {
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
    QUAD_OFFSETS = [(-0.25, -0.25), (-0.25, 0.25), (0.25, -0.25), (0.25, 0.25)]  # UL, UR, LL, LR

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
            corners = tuple(inside(row + dr, col + dc) for dr, dc in QUAD_OFFSETS)
            if any(corners) and not all(corners):
                # Mixed cell: center's own wedge might be None (center just
                # outside) even though part of the cell is inside -- an
                # ellipse is convex, so falling back to whichever sub-point is
                # actually inside always finds a valid wedge for the color.
                color_v = v
                if color_v is None:
                    for (dr, dc), is_in in zip(QUAD_OFFSETS, corners):
                        if is_in:
                            color_v = wedge_of(row + dr, col + dc)
                            if color_v is not None:
                                break
                if color_v is not None:
                    grid[row][col] = color_v
                    quad_glyph[row][col] = QUADRANT_GLYPH[corners]

    label_map: dict[tuple[int, int], str] = {}
    for s, (start, end) in zip(chart.slices, bounds):
        pct = s.value / total * 100
        text = f"{pct:.0f}%"
        mid = math.radians((start + end) / 2)
        span = end - start
        out_r = 0.55 if span > 25 else 1.28
        px = cx + out_r * rx * math.sin(mid)
        py = cy - out_r * ry * math.cos(mid)
        col0 = round(px) - len(text) // 2
        for k, ch in enumerate(text):
            label_map[(round(py), col0 + k)] = ch

    glyph = "█"
    rows: list[str] = []
    for row in range(h):
        buf = []
        for col in range(w):
            if (row, col) in label_map:
                buf.append(c.bold(label_map[(row, col)]))
                continue
            v = grid[row][col]
            if v is None:
                buf.append(" ")
            else:
                g = quad_glyph[row][col] or glyph
                buf.append(c.fg(g, SLICE_COLORS[v % len(SLICE_COLORS)]))
        rows.append("".join(buf))

    legend = [f"{c.fg(glyph + glyph, SLICE_COLORS[i % len(SLICE_COLORS)])} {s.label}"
              for i, s in enumerate(chart.slices)]
    legend_start = h // 2 - len(legend) // 2
    for i, txt in enumerate(legend):
        r = legend_start + i
        if 0 <= r < h:
            rows[r] = rows[r] + "   " + txt

    # Trim blank rows above the circle's first actual fill row: the top
    # margin plus a thin outside slice's label (e.g. Rats' "3%" above the
    # circle, per the thin-wedge placement above) can otherwise leave a blank
    # row, then the label row, then *another* blank row before the circle
    # itself starts -- a plain leading-blank strip only catches the first of
    # those, since the label row in between isn't blank. Drop every blank row
    # ahead of the first row containing a fill glyph instead, keeping any
    # label text intact; one deliberate blank separator (below) is enough.
    FILL_GLYPHS = set("▘▝▖▗▀▄▌▐▚▞▛▜▙▟█")
    first_fill = next((i for i, r in enumerate(rows) if any(ch in FILL_GLYPHS for ch in r)), len(rows))
    rows = [r for r in rows[:first_fill] if r.strip()] + rows[first_fill:]

    out = []
    if chart.title:
        pad = (w - len(chart.title)) // 2
        out.append(" " * max(pad, 0) + c.bold(chart.title))
        out.append("")
    out.extend(rows)
    return "\n".join(out)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _resolve_color(choice: str) -> bool:
    if choice == "always":
        return True
    if choice == "never":
        return False
    if os.environ.get("NO_COLOR"):
        return False
    return sys.stdout.isatty()


def _terminal_width(fallback: int = 100) -> int:
    return shutil.get_terminal_size(fallback=(fallback, 24)).columns


def _default_radius(chart: PieChart, terminal_width: int) -> int:
    """60% of the largest radius whose full render (circle + legend) still
    fits `terminal_width` -- a pie at the true maximum reads as oversized
    relative to a document; 60% keeps it comfortably inside the width
    without needing the caller to hand-tune --radius per chart."""
    if not chart.slices:
        return 16
    # Mirrors render_circle's own width math (w = 2*radius + 1 + 2*margin)
    # plus the legend's fixed per-row suffix ("   " + 2-char swatch + " " +
    # label), so this prediction can't quietly drift from what actually gets
    # rendered.
    legend_extra = 3 + 2 + 1 + max(len(s.label) for s in chart.slices)
    max_fit = (terminal_width - (2 * CIRCLE_MARGIN + 1) - legend_extra) // 2
    return max(6, round(max_fit * 0.6))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument(
        "path", nargs="?", default=os.path.join(os.path.dirname(__file__), "example.mmd")
    )
    parser.add_argument("--color", choices=["auto", "always", "never"], default="auto")
    parser.add_argument("--ascii", action="store_true", help="force ASCII-safe glyphs (implies bar-chart fallback)")
    parser.add_argument(
        "--radius", type=int, default=None,
        help="circle radius in columns (circular rendering only). Defaults to 60%% of the "
             "largest radius that fits the terminal width (or 100 columns if not a tty).",
    )
    parser.add_argument(
        "--aspect", type=float, default=0.42,
        help="row compression factor -- lower if the circle looks tall/oval in your terminal, "
             "raise if it looks short/oval. Compensates for your terminal font's actual "
             "character height:width ratio, which this script cannot detect reliably. "
             "0.42 is a maintainer-verified default (macOS Terminal.app); other terminals may need "
             "a different value.",
    )
    args = parser.parse_args()

    with open(args.path, encoding="utf-8") as f:
        text = f.read()

    if not sniff(text):
        print("not a pie fence", file=sys.stderr)
        raise SystemExit(1)

    chart = parse(text)
    color_enabled = _resolve_color(args.color)
    colorizer = Colorizer(enabled=color_enabled)

    if color_enabled and not args.ascii:
        radius = args.radius if args.radius is not None else _default_radius(chart, _terminal_width())
        print(render_circle(chart, colorizer, radius, args.aspect))
    else:
        print(render_bar(chart, colorizer, use_ascii=args.ascii))


if __name__ == "__main__":
    main()

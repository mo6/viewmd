#!/usr/bin/env python3
"""Proof of concept for VIEWMD-0047 (Mermaid quadrant charts).

Not part of the shipped `viewmd` package -- a throwaway script to research
whether/how color should be used in the quadrant chart before committing to a
design, alongside the plain box-drawing layout the issue's own mockups
already settled on. viewmd's existing Mermaid renderers (flowchart, sequence,
ER, pie's bar-chart fallback) don't use ANSI color today, so this is
specifically for reviewing whether quadrant charts should be the first to.

    python3 poc/quadrant/quadrant_poc.py poc/quadrant/example.mmd
    python3 poc/quadrant/quadrant_poc.py poc/quadrant/example.mmd --color always
    python3 poc/quadrant/quadrant_poc.py poc/quadrant/example.mmd --color never
    python3 poc/quadrant/quadrant_poc.py poc/quadrant/example.mmd --fill none --points mono
    python3 poc/quadrant/quadrant_poc.py poc/quadrant/example.mmd --fill quadrant --points quadrant
    python3 poc/quadrant/quadrant_poc.py poc/quadrant/example.mmd --fill quadrant --points palette
    python3 poc/quadrant/quadrant_poc.py poc/quadrant/example-styled.mmd --fill none --points styled
    python3 poc/quadrant/quadrant_poc.py poc/quadrant/example.mmd \\
        --bg quadrant --fill none --points mono
    python3 poc/quadrant/quadrant_poc.py poc/quadrant/example.mmd \\
        --bg quadrant --fill quadrant --points styled

`--fill` controls whether/how the box itself is tinted per quadrant (`none`:
today's plain box; `border`: only the box-drawing border/cross segments and
quadrant-label text pick up that quadrant's tint; `quadrant`: `border` plus
every point marker in that quadrant also picks it up, unless overridden by
`--points`). `--points` controls marker/label color independently of `--fill`
(`mono`: no color; `quadrant`: match the point's own quadrant, same as
`--fill quadrant`; `palette`: rotate a fixed palette by point index, for
datasets where "which quadrant" isn't the interesting grouping; `styled`:
honor the point's own Mermaid `color:` styling or its `:::class`'s `classDef`
color -- the one mode that actually reads the real Mermaid point-styling
syntax VIEWMD-0047 currently parses-and-discards as a Non-goal -- falling
back to `quadrant`/plain when neither is set). `--bg` is a third, independent
knob: `none` (today's blank interior) or `quadrant` (every cell of a
quadrant's interior -- not just its border/text -- gets a solid background
fill, darkened from that quadrant's own tint so foreground text/markers stay
legible on top, closer to how mermaid.js.org actually fills each quadrant as
a colored rectangle rather than leaving it blank).

The four quadrant tints and the palette-mode point colors below are a
starting draft to react to, not a claim that they match Mermaid's own
default theme pixel-for-pixel -- same posture as `poc/pie/pie_poc.py`'s
`SLICE_COLORS` comment ("approximating Mermaid's own default pie palette").
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from dataclasses import dataclass, field

# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------


@dataclass
class Point:
    label: str
    x: float
    y: float
    cls: str | None = None
    style: dict[str, str] = field(default_factory=dict)


@dataclass
class QuadrantChart:
    title: str = ""
    x_low: str = ""
    x_high: str = ""
    y_low: str = ""
    y_high: str = ""
    quadrants: dict[int, str] = field(default_factory=dict)  # 1..4
    points: list[Point] = field(default_factory=list)
    class_defs: dict[str, dict[str, str]] = field(default_factory=dict)


class ParseError(Exception):
    pass


_TITLE_RE = re.compile(r"^title\s+(?P<text>.+)$")
_XAXIS_RE = re.compile(r"^x-axis\s+(?P<low>.+?)(?:\s*-->\s*(?P<high>.+))?$")
_YAXIS_RE = re.compile(r"^y-axis\s+(?P<low>.+?)(?:\s*-->\s*(?P<high>.+))?$")
_QUADRANT_RE = re.compile(r"^quadrant-(?P<n>[1-4])\s+(?P<text>.+)$")
_POINT_RE = re.compile(
    r"^(?P<label>[^:\[]+?)(?::::(?P<cls>[\w-]+))?\s*:\s*"
    r"\[\s*(?P<x>-?\d+(?:\.\d+)?)\s*,\s*(?P<y>-?\d+(?:\.\d+)?)\s*\]\s*(?P<rest>.*)$"
)
_CLASSDEF_RE = re.compile(r"^classDef\s+(?P<name>[\w-]+)\s+(?P<rest>.*)$")
_STYLE_TOKEN_RE = re.compile(r"([\w-]+)\s*:\s*([^,]+)")


def sniff(text: str) -> bool:
    return text.lstrip().startswith("quadrantChart")


def _parse_style(rest: str) -> dict[str, str]:
    return {k.strip(): v.strip() for k, v in _STYLE_TOKEN_RE.findall(rest)}


def parse(text: str) -> QuadrantChart:
    lines = text.splitlines()
    if not lines or not lines[0].strip().startswith("quadrantChart"):
        raise ParseError("expected a line starting with 'quadrantChart'")

    chart = QuadrantChart()
    for raw in lines[1:]:
        line = raw.split("%%", 1)[0].strip()
        if not line:
            continue
        if m := _TITLE_RE.match(line):
            chart.title = m.group("text").strip()
        elif m := _XAXIS_RE.match(line):
            chart.x_low = m.group("low").strip()
            chart.x_high = (m.group("high") or "").strip()
        elif m := _YAXIS_RE.match(line):
            chart.y_low = m.group("low").strip()
            chart.y_high = (m.group("high") or "").strip()
        elif m := _QUADRANT_RE.match(line):
            chart.quadrants[int(m.group("n"))] = m.group("text").strip()
        elif m := _CLASSDEF_RE.match(line):
            chart.class_defs[m.group("name")] = _parse_style(m.group("rest"))
        elif m := _POINT_RE.match(line):
            chart.points.append(Point(
                label=m.group("label").strip(),
                x=float(m.group("x")),
                y=float(m.group("y")),
                cls=m.group("cls"),
                style=_parse_style(m.group("rest")),
            ))
        else:
            raise ParseError(f"could not parse line: {raw!r}")

    return chart


# ---------------------------------------------------------------------------
# Color
# ---------------------------------------------------------------------------

# Draft-only starting tints, one per quadrant (1=top-right .. 4=bottom-right,
# Mermaid's own numbering) -- reviewable/replaceable, see module docstring.
QUADRANT_COLORS = {
    1: "6f9fd8",  # top-right: blue
    2: "d88a3f",  # top-left: orange
    3: "3fa66a",  # bottom-left: green
    4: "b06fd8",  # bottom-right: violet
}

# Rotated by point index in --points palette mode, independent of quadrant.
POINT_PALETTE = ["c9c9f5", "f7f4b8", "c3e876", "f5c6c6", "a8d8ea", "e0b3f0"]


def _hex_to_rgb(h: str) -> tuple[int, int, int]:
    h = h.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def _darken(hex_: str, factor: float) -> str:
    """Scales a quadrant's foreground tint down to a background-fill shade
    (`factor` of original brightness) rather than a second hand-picked
    palette -- keeps the fg/bg tints from silently drifting apart per
    quadrant as QUADRANT_COLORS above gets tweaked during review."""
    r, g, b = _hex_to_rgb(hex_)
    return f"{int(r * factor):02x}{int(g * factor):02x}{int(b * factor):02x}"


class Colorizer:
    """Wraps text in 24-bit ANSI escapes, or passes it through unchanged.

    Same single-`enabled`-flag precedent as poc/pie/pie_poc.py and
    poc/kanban/kanban_poc.py's Colorizer.
    """

    def __init__(self, enabled: bool) -> None:
        self.enabled = enabled

    def fg(self, text: str, hex_: str) -> str:
        return self.style(text, fg=hex_)

    def bold(self, text: str) -> str:
        return self.style(text, bold=True)

    def style(self, text: str, *, fg: str | None = None, bg: str | None = None,
              bold: bool = False) -> str:
        if not self.enabled or not text:
            return text
        codes = []
        if bold:
            codes.append("1")
        if fg:
            r, g, b = _hex_to_rgb(fg)
            codes.append(f"38;2;{r};{g};{b}")
        if bg:
            r, g, b = _hex_to_rgb(bg)
            codes.append(f"48;2;{r};{g};{b}")
        if not codes:
            return text
        return f"\x1b[{';'.join(codes)}m{text}\x1b[0m"


def _point_color(chart: QuadrantChart, p: Point, quadrant: int, mode: str) -> str | None:
    if mode == "mono":
        return None
    if mode == "styled":
        if "color" in p.style:
            return p.style["color"]
        if p.cls and p.cls in chart.class_defs and "color" in chart.class_defs[p.cls]:
            return chart.class_defs[p.cls]["color"]
        return QUADRANT_COLORS[quadrant]
    if mode == "palette":
        idx = chart.points.index(p)
        return POINT_PALETTE[idx % len(POINT_PALETTE)]
    return QUADRANT_COLORS[quadrant]  # "quadrant"


# ---------------------------------------------------------------------------
# Rendering (bordered-box layout, per VIEWMD-0047's mockups)
# ---------------------------------------------------------------------------


def _quadrant_of(x: float, y: float) -> tuple[int, float, float]:
    """Returns (quadrant number, x/y remapped to 0..1 *within that quadrant*)."""
    if x < 0.5 and y >= 0.5:
        return 2, x / 0.5, 1 - (y - 0.5) / 0.5
    if x >= 0.5 and y >= 0.5:
        return 1, (x - 0.5) / 0.5, 1 - (y - 0.5) / 0.5
    if x < 0.5 and y < 0.5:
        return 3, x / 0.5, 1 - y / 0.5
    return 4, (x - 0.5) / 0.5, 1 - y / 0.5


def render_box(chart: QuadrantChart, c: Colorizer, *, fill: str, points_mode: str, bg: str,
                qw: int = 24, qh: int = 7) -> str:
    width = qw * 2 + 3
    total_rows = qh * 2 + 3
    # Each cell holds (char, color_hex_or_None).
    grid: list[list[tuple[str, str | None]]] = [[(" ", None)] * width for _ in range(total_rows)]

    def put(r: int, ci: int, ch: str, color: str | None = None) -> None:
        grid[r][ci] = (ch, color)

    def border_color(qrow: int, qcol: int) -> str | None:
        if fill == "none":
            return None
        n = {(0, 1): 1, (0, 0): 2, (1, 0): 3, (1, 1): 4}[(qrow, qcol)]
        return QUADRANT_COLORS[n]

    # Border: split each edge segment by which quadrant(s) it touches, so
    # --fill border/quadrant can tint the left half of the top edge
    # differently from the right half, etc.
    for ci in range(width):
        left_half = ci <= qw + 1
        qcol = 0 if left_half else 1
        top_color = border_color(0, qcol)
        bot_color = border_color(1, qcol)
        if ci == 0:
            put(0, ci, "┌", top_color)
            put(qh + 1, ci, "├", None)
            put(total_rows - 1, ci, "└", bot_color)
        elif ci == qw + 1:
            put(0, ci, "┬", top_color)
            put(qh + 1, ci, "┼", None)
            put(total_rows - 1, ci, "┴", bot_color)
        elif ci == width - 1:
            put(0, ci, "┐", top_color)
            put(qh + 1, ci, "┤", None)
            put(total_rows - 1, ci, "┘", bot_color)
        else:
            put(0, ci, "─", top_color)
            put(qh + 1, ci, "─", None)
            put(total_rows - 1, ci, "─", bot_color)
    for r in range(1, total_rows - 1):
        if r == qh + 1:
            continue
        qrow = 0 if r < qh + 1 else 1
        put(r, 0, "│", border_color(qrow, 0))
        put(r, qw + 1, "│", None)
        put(r, width - 1, "│", border_color(qrow, 1))
    for r in range(total_rows):
        if grid[r][qw + 1][0] not in "┬┼┴":
            put(r, qw + 1, "│", None)

    def cell_origin(qrow: int, qcol: int) -> tuple[int, int]:
        r0 = 1 if qrow == 0 else qh + 2
        c0 = 1 if qcol == 0 else qw + 2
        return r0, c0

    quadrant_pos = {1: (0, 1), 2: (0, 0), 3: (1, 0), 4: (1, 1)}
    for n, text in chart.quadrants.items():
        qrow, qcol = quadrant_pos[n]
        r0, c0 = cell_origin(qrow, qcol)
        color = QUADRANT_COLORS[n] if fill in ("border", "quadrant") else None
        for i, ch in enumerate(text):
            if c0 + i < c0 + qw:
                put(r0, c0 + i, ch, color)

    used_rows: dict[tuple[int, int], set[int]] = {}
    for p in chart.points:
        n, xc, yc = _quadrant_of(p.x, p.y)
        qrow, qcol = quadrant_pos[n]
        r0, c0 = cell_origin(qrow, qcol)
        col = max(c0, min(c0 + round(xc * (qw - 1)), c0 + qw - 1))
        row = max(r0 + 1, min(r0 + round(yc * (qh - 1)), r0 + qh - 2))
        taken = used_rows.setdefault((qrow, qcol), set())
        while row in taken and row + 1 < r0 + qh:
            row += 1
        taken.add(row)
        lrow = row + 1 if row + 1 < r0 + qh and (row + 1) not in taken else row - 1
        taken.add(lrow)

        color = _point_color(chart, p, n, points_mode)
        put(row, col, "●", color)
        start = max(c0, min(col - len(p.label) // 2, c0 + qw - len(p.label)))
        for i, ch in enumerate(p.label):
            ci = start + i
            if c0 <= ci < c0 + qw and grid[lrow][ci][0] == " ":
                put(lrow, ci, ch, color)

    # Background fill (independent of --fill, which only tints border/text
    # foreground): a solid tint across every cell of a quadrant's interior,
    # darkened from that quadrant's own QUADRANT_COLORS entry so foreground
    # text/markers (colored or not) stay legible on top of it -- closer to
    # how the real mermaid.js.org render fills each quadrant as a colored
    # rectangle rather than leaving it blank.
    bg_grid: list[list[str | None]] = [[None] * width for _ in range(total_rows)]
    if bg == "quadrant":
        for n, (qrow, qcol) in quadrant_pos.items():
            r0, c0 = cell_origin(qrow, qcol)
            shade = _darken(QUADRANT_COLORS[n], 0.28)
            for r in range(r0, r0 + qh):
                for ci in range(c0, c0 + qw):
                    bg_grid[r][ci] = shade

    def render_cell(ch: str, fg_color: str | None, bg_color: str | None) -> str:
        if not fg_color and not bg_color:
            return ch
        return c.style(ch, fg=fg_color, bg=bg_color)

    lines = [
        "".join(render_cell(ch, fg_color, bg_grid[ri][ci]) for ci, (ch, fg_color) in enumerate(row))
        for ri, row in enumerate(grid)
    ]

    left_pad = max(len(chart.y_low), len(chart.y_high)) + 1
    out: list[str] = []
    if chart.title:
        out.append(" " * left_pad + c.bold(chart.title.center(width)))
        out.append("")
    yhigh_row = 1 + qh // 2
    ylow_row = qh + 2 + qh // 2
    for i, line in enumerate(lines):
        prefix = " " * left_pad
        if i == yhigh_row and chart.y_high:
            prefix = chart.y_high.rjust(left_pad - 1) + " "
        elif i == ylow_row and chart.y_low:
            prefix = chart.y_low.rjust(left_pad - 1) + " "
        out.append(prefix + line)
    xaxis_row = " " * left_pad + chart.x_low.center(qw + 2) + chart.x_high.center(qw + 2)
    out.append(xaxis_row)
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


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "path", nargs="?", default=os.path.join(os.path.dirname(__file__), "example.mmd")
    )
    parser.add_argument("--color", choices=["auto", "always", "never"], default="auto")
    parser.add_argument("--fill", choices=["none", "border", "quadrant"], default="quadrant")
    parser.add_argument(
        "--points", choices=["mono", "quadrant", "palette", "styled"], default="styled"
    )
    parser.add_argument("--bg", choices=["none", "quadrant"], default="none")
    parser.add_argument("--quadrant-width", type=int, default=24)
    parser.add_argument("--quadrant-height", type=int, default=7)
    args = parser.parse_args()

    with open(args.path, encoding="utf-8") as f:
        text = f.read()
    if not sniff(text):
        print("not a quadrantChart fence", file=sys.stderr)
        sys.exit(1)

    chart = parse(text)
    c = Colorizer(_resolve_color(args.color))
    print(render_box(
        chart, c, fill=args.fill, points_mode=args.points, bg=args.bg,
        qw=args.quadrant_width, qh=args.quadrant_height,
    ))


if __name__ == "__main__":
    main()

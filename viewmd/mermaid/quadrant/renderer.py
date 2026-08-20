"""Quadrant chart renderer (VIEWMD-0047).

No upstream reference implementation to port from (mermaid-ascii has no
quadrant-chart support; termaid's own free-floating axis-cross rendering was
a cross-check during design, not an oracle to match -- see the issue's
Design notes for why this ships a bordered box instead, closer to
mermaid.js.org's own real SVG render), so this is hand-written directly
against Mermaid's own syntax (https://mermaid.js.org/syntax/quadrantChart.html).
`poc/quadrant/quadrant_poc.py` is the implementation example this module
follows for both the box layout and the color scheme (`QUADRANT_COLORS`,
`_darken`, the `--fill quadrant --bg quadrant --points styled` combination);
the constants and layout math here are ported from it, not re-derived.
"""

from __future__ import annotations

import shutil
from dataclasses import dataclass

from viewmd.mermaid.grid.canvas import wrap_text_bold, wrap_text_styled
from viewmd.mermaid.quadrant.parser import QuadrantChart
from viewmd.mermaid.textutil import width as string_width

__all__ = ["render"]


@dataclass(frozen=True)
class _Glyphs:
    h: str
    v: str
    tl: str
    tr: str
    bl: str
    br: str
    tee_d: str  # ┬
    tee_u: str  # ┴
    tee_l: str  # ├
    tee_r: str  # ┤
    cross: str  # ┼
    marker: str  # ●


_UNICODE = _Glyphs(h="─", v="│", tl="┌", tr="┐", bl="└", br="┘",
                    tee_d="┬", tee_u="┴", tee_l="├", tee_r="┤", cross="┼", marker="●")
_ASCII = _Glyphs(h="-", v="|", tl="+", tr="+", bl="+", br="+",
                  tee_d="+", tee_u="+", tee_l="+", tee_r="+", cross="+", marker="*")

# Approximating Mermaid's own default quadrant palette (requirement 8); one
# hue per quadrant, Mermaid's own 1..4 numbering (top-right, top-left,
# bottom-left, bottom-right). Ported from poc/quadrant/quadrant_poc.py's
# QUADRANT_COLORS, the palette that mockup 1a in the issue was reviewed
# against, not a new palette invented here.
_QUADRANT_COLORS = {
    1: "6f9fd8",
    2: "d88a3f",
    3: "3fa66a",
    4: "b06fd8",
}
# Background-fill brightness (requirement 8b), relative to the same tint --
# ported from poc/quadrant/quadrant_poc.py:_darken's factor.
_BG_DARKEN_FACTOR = 0.28
# VIEWMD-0091 (amended requirement 4): the light-theme counterpart to
# _BG_DARKEN_FACTOR -- blends each quadrant's foreground tint toward white by
# this fraction instead of toward black, so the fill reads as a light pastel
# on a light terminal background rather than the dark-theme's near-black
# shade. 0.82 was chosen (over e.g. 0.5, too saturated/mid-tone to read as
# "light", or 0.95+, too washed out to keep the four quadrants visually
# distinct from each other or from a white background) by rendering
# docs/mermaid-quadrant.md with each candidate and eyeballing it against a
# white terminal background: at 0.82 all four quadrant fills are unmistakably
# pale/pastel (each channel at least 82% of the way to 255) while still
# visibly tinted and distinguishable from one another and from plain white.
_BG_LIGHTEN_FACTOR = 0.82

_QUADRANT_POS = {1: (0, 1), 2: (0, 0), 3: (1, 0), 4: (1, 1)}  # n -> (qrow, qcol)
_POS_TO_QUADRANT = {pos: n for n, pos in _QUADRANT_POS.items()}

_QUADRANT_HEIGHT = 7
_MIN_QUADRANT_WIDTH = 10


def _darken(hex_: str, factor: float) -> str:
    """Scales a quadrant's foreground tint down to a background-fill shade
    rather than a second hand-picked palette -- keeps the fg/bg tints from
    silently drifting apart per quadrant if `_QUADRANT_COLORS` is ever
    retuned (ported from poc/quadrant/quadrant_poc.py:_darken)."""
    hex_ = hex_.lstrip("#")
    r, g, b = int(hex_[0:2], 16), int(hex_[2:4], 16), int(hex_[4:6], 16)
    return f"{int(r * factor):02x}{int(g * factor):02x}{int(b * factor):02x}"


def _lighten(hex_: str, factor: float) -> str:
    """Scales a quadrant's foreground tint up toward white by `factor`,
    mirroring `_darken`'s shape (VIEWMD-0091 amended requirement 4) -- blends
    each channel toward 255 rather than scaling toward 0, so the light theme's
    background fill stays derived from the same per-quadrant tint instead of
    a second hand-picked palette, exactly as `_darken` already does for dark."""
    hex_ = hex_.lstrip("#")
    r, g, b = int(hex_[0:2], 16), int(hex_[2:4], 16), int(hex_[4:6], 16)
    r2 = int(r + (255 - r) * factor)
    g2 = int(g + (255 - g) * factor)
    b2 = int(b + (255 - b) * factor)
    return f"{r2:02x}{g2:02x}{b2:02x}"


def _terminal_width(fallback: int = 100) -> int:
    return shutil.get_terminal_size(fallback=(fallback, 24)).columns


def _default_box_width(chart: QuadrantChart, target_width: int) -> int:
    """Requirement 7: the box's default column width scales with the
    caller's resolved render width (mirroring
    `viewmd/mermaid/pie/renderer.py:_default_radius`, VIEWMD-0043
    requirement 5b) rather than a fixed constant. `target_width` MUST be the
    caller's already-resolved value, not re-queried from the terminal here --
    VIEWMD-0043's own peer review caught exactly that mistake in the pie
    chart's first implementation."""
    left_pad = max(string_width(chart.y_low), string_width(chart.y_high)) + 1
    # Mirrors render()'s own width math (2 quadrant cells + 3 border columns,
    # plus the left margin), so this prediction can't silently drift from
    # what actually gets rendered.
    available = target_width - left_pad - 3
    qw = max(_MIN_QUADRANT_WIDTH, available // 2)
    if chart.title:
        # Requirement 7 also names the title explicitly ("the full box --
        # plus its left-margin y-axis label and title -- still fits the
        # target width"): grow qw (never shrink it) so the box itself is at
        # least as wide as its own centered title, the same way render()
        # centers it (`chart.title.center(box_width)`) -- otherwise a title
        # longer than a narrow-target box would silently overflow past
        # target_width while the sizing math claimed to account for it. An
        # unavoidably long title can still end up wider than target_width in
        # the end (same posture as every other Mermaid diagram here,
        # VIEWMD-0018 -- rows are allowed to scroll, not truncated/wrapped),
        # but that's now a deliberate trade-off this function actually
        # considered, not a blind spot.
        title_w = string_width(chart.title)
        title_min_qw = -(-(title_w - 3) // 2)  # ceil((title_w - 3) / 2)
        qw = max(qw, title_min_qw)
    return qw


def _quadrant_of(x: float, y: float) -> tuple[int, float, float]:
    """Maps a point's `[0,1]` (x, y) onto (quadrant number, x/y remapped to
    0..1 *within that quadrant*), Mermaid's own 1..4 numbering."""
    if x < 0.5 and y >= 0.5:
        return 2, x / 0.5, 1 - (y - 0.5) / 0.5
    if x >= 0.5 and y >= 0.5:
        return 1, (x - 0.5) / 0.5, 1 - (y - 0.5) / 0.5
    if x < 0.5 and y < 0.5:
        return 3, x / 0.5, 1 - y / 0.5
    return 4, (x - 0.5) / 0.5, 1 - y / 0.5


def render(chart: QuadrantChart, *, use_ascii: bool = False, color: bool = False,
           width: int | None = None, theme: str = "dark") -> str:
    g = _ASCII if use_ascii else _UNICODE
    target_width = width if width is not None else _terminal_width()
    qw = _default_box_width(chart, target_width)
    return _render_box(chart, g, color=color, qw=qw, qh=_QUADRANT_HEIGHT, theme=theme)


def _render_box(
    chart: QuadrantChart, g: _Glyphs, *, color: bool, qw: int, qh: int, theme: str = "dark"
) -> str:
    box_width = qw * 2 + 3
    total_rows = qh * 2 + 3
    # Each cell holds (char, fg_color_hex_or_None).
    grid: list[list[tuple[str, str | None]]] = (
        [[(" ", None)] * box_width for _ in range(total_rows)]
    )

    def put(r: int, ci: int, ch: str, fg: str | None = None) -> None:
        grid[r][ci] = (ch, fg)

    def border_color(qrow: int, qcol: int) -> str | None:
        if not color:
            return None
        return _QUADRANT_COLORS[_POS_TO_QUADRANT[(qrow, qcol)]]

    # Border: split each edge segment by which quadrant(s) it touches, so
    # each half of the top/bottom edge and each side's border picks up its
    # own quadrant's tint (requirement 8a) rather than one color for the
    # whole box.
    for ci in range(box_width):
        qcol = 0 if ci <= qw + 1 else 1
        top_color = border_color(0, qcol)
        bot_color = border_color(1, qcol)
        if ci == 0:
            put(0, ci, g.tl, top_color)
            put(qh + 1, ci, g.tee_l)
            put(total_rows - 1, ci, g.bl, bot_color)
        elif ci == qw + 1:
            put(0, ci, g.tee_d, top_color)
            put(qh + 1, ci, g.cross)
            put(total_rows - 1, ci, g.tee_u, bot_color)
        elif ci == box_width - 1:
            put(0, ci, g.tr, top_color)
            put(qh + 1, ci, g.tee_r)
            put(total_rows - 1, ci, g.br, bot_color)
        else:
            put(0, ci, g.h, top_color)
            put(qh + 1, ci, g.h)
            put(total_rows - 1, ci, g.h, bot_color)
    for r in range(1, total_rows - 1):
        if r == qh + 1:
            continue
        qrow = 0 if r < qh + 1 else 1
        put(r, 0, g.v, border_color(qrow, 0))
        put(r, qw + 1, g.v)
        put(r, box_width - 1, g.v, border_color(qrow, 1))

    def cell_origin(qrow: int, qcol: int) -> tuple[int, int]:
        r0 = 1 if qrow == 0 else qh + 2
        c0 = 1 if qcol == 0 else qw + 2
        return r0, c0

    for n, text in chart.quadrants.items():
        qrow, qcol = _QUADRANT_POS[n]
        r0, c0 = cell_origin(qrow, qcol)
        fg = _QUADRANT_COLORS[n] if color else None
        for i, ch in enumerate(text):
            if c0 + i < c0 + qw:
                put(r0, c0 + i, ch, fg)

    used_rows: dict[tuple[int, int], set[int]] = {}
    for p in chart.points:
        n, xc, yc = _quadrant_of(p.x, p.y)
        qrow, qcol = _QUADRANT_POS[n]
        r0, c0 = cell_origin(qrow, qcol)
        col = max(c0, min(c0 + round(xc * (qw - 1)), c0 + qw - 1))
        row = max(r0 + 1, min(r0 + round(yc * (qh - 1)), r0 + qh - 2))
        taken = used_rows.setdefault((qrow, qcol), set())
        while row in taken and row + 1 < r0 + qh:
            row += 1
        taken.add(row)
        lrow = row + 1 if row + 1 < r0 + qh and (row + 1) not in taken else row - 1
        taken.add(lrow)

        # Requirement 8c: a point's own explicit color overrides its
        # quadrant's fallback tint; with color disabled, no fg at all.
        fg = (p.color or _QUADRANT_COLORS[n]) if color else None
        put(row, col, g.marker, fg)
        label_w = string_width(p.label)
        start = max(c0, min(col - label_w // 2, c0 + qw - label_w))
        for i, ch in enumerate(p.label):
            ci = start + i
            if c0 <= ci < c0 + qw and grid[lrow][ci][0] == " ":
                put(lrow, ci, ch, fg)

    # Background fill (requirement 8b): every cell of a quadrant's interior
    # gets a solid, darkened tint so foreground text/markers stay legible on
    # top of it.
    bg_grid: list[list[str | None]] = [[None] * box_width for _ in range(total_rows)]
    if color:
        for n, (qrow, qcol) in _QUADRANT_POS.items():
            r0, c0 = cell_origin(qrow, qcol)
            # VIEWMD-0091 (amended requirement 4): light theme lightens each
            # quadrant's foreground tint toward white instead of darkening it
            # toward black -- the foreground tints (_QUADRANT_COLORS, used for
            # borders/points/text) are unchanged in both themes; only this
            # background fill flips direction.
            shade = (
                _lighten(_QUADRANT_COLORS[n], _BG_LIGHTEN_FACTOR)
                if theme == "light"
                else _darken(_QUADRANT_COLORS[n], _BG_DARKEN_FACTOR)
            )
            for r in range(r0, r0 + qh):
                for ci in range(c0, c0 + qw):
                    bg_grid[r][ci] = shade

    def render_cell(ch: str, fg: str | None, bg: str | None) -> str:
        if not fg and not bg:
            return ch
        return wrap_text_styled(ch, fg=fg, bg=bg)

    lines = [
        "".join(render_cell(ch, fg, bg_grid[ri][ci]) for ci, (ch, fg) in enumerate(row))
        for ri, row in enumerate(grid)
    ]

    # Title and axis labels stay plain/uncolored outside the box (requirement
    # 8d) -- only the title picks up bold, matching the other Mermaid
    # renderers' title treatment.
    left_pad = max(string_width(chart.y_low), string_width(chart.y_high)) + 1
    out: list[str] = []
    if chart.title:
        title_line = chart.title.center(box_width)
        out.append(" " * left_pad + (wrap_text_bold(title_line) if color else title_line))
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

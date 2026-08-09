"""Packet diagram renderer (VIEWMD-0049).

No upstream reference implementation to port from (mermaid-ascii has no
packet-diagram support, and real Mermaid renders to SVG, not a terminal
grid), so the row-wrapping/splitting algorithm below is hand-written directly
against Mermaid's own `populate()`/`getNextFittingBlock()` behavior
(packages/mermaid/src/diagrams/packet/renderer.ts, packet/parser.ts), while
the box-drawing/label layout is hand-authored and visually verified (see the
issue's Design notes for why there's no character-grid oracle to match).
"""

from __future__ import annotations

from dataclasses import dataclass

from viewmd.mermaid.packet.parser import Field, PacketDiagram
from viewmd.mermaid.textutil import width as string_width

__all__ = ["render"]

BITS_PER_ROW = 32

# Chars per bit of proportional cell width, minus one (every field's cell
# loses a single column versus a flat 3-per-bit budget) -- reverse-engineered
# from the one hand-verified reference example (two 16-bit fields, each
# rendered 47 dashes wide: 16*3 - 1). Floored so a 1-bit field still has room
# for a short label before truncation kicks in.
_CHARS_PER_BIT = 3
_MIN_CELL_WIDTH = 3


@dataclass(frozen=True)
class _Glyphs:
    h: str
    v: str
    tl: str
    tr: str
    bl: str
    br: str
    tee_d: str
    tee_u: str


_UNICODE = _Glyphs(h="─", v="│", tl="╭", tr="╮", bl="╰", br="╯", tee_d="┬", tee_u="┴")
_ASCII = _Glyphs(h="-", v="|", tl="+", tr="+", bl="+", br="+", tee_d="+", tee_u="+")


def _split_into_rows(fields: list[Field], bits_per_row: int) -> list[list[Field]]:
    """Wrap `fields` onto rows of `bits_per_row` bits, splitting a field that
    crosses a row boundary into same-labeled halves (requirement 5), mirroring
    upstream's `getNextFittingBlock` -- including flushing a row the instant a
    field's `end` lands exactly on the boundary, not only when the next field
    overflows it."""
    rows: list[list[Field]] = []
    current: list[Field] = []
    row = 0
    for f in fields:
        start = f.start
        while True:
            row_end = (row + 1) * bits_per_row - 1
            if f.end <= row_end:
                current.append(Field(start=start, end=f.end, label=f.label))
                if f.end == row_end:
                    rows.append(current)
                    current = []
                    row += 1
                break
            current.append(Field(start=start, end=row_end, label=f.label))
            rows.append(current)
            current = []
            row += 1
            start = row_end + 1
    if current:
        rows.append(current)
    return rows


def _truncate(label: str, width: int, ellipsis: str) -> str:
    """Truncate `label` to display-width `width`, wide-character-safe (never
    splits a double-width glyph), appending `ellipsis` when it fits."""
    if string_width(label) <= width:
        return label
    if width <= 0:
        return ""

    ell_w = string_width(ellipsis)
    target = width - ell_w if width > ell_w else width
    out: list[str] = []
    w = 0
    for ch in label:
        cw = string_width(ch)
        if w + cw > target:
            break
        out.append(ch)
        w += cw
    return "".join(out) + (ellipsis if width > ell_w else "")


def _center(label: str, width: int, ellipsis: str) -> str:
    label = _truncate(label, width, ellipsis)
    pad = width - string_width(label)
    left = pad // 2
    right = pad - left
    return " " * left + label + " " * right


def _header_slot(lo: int, hi: int, width: int) -> str:
    if lo == hi:
        pad = width - len(str(lo))
        left = pad // 2
        return " " * left + str(lo) + " " * (pad - left)
    left_s, right_s = str(lo), str(hi)
    pad = max(width - len(left_s) - len(right_s), 1)
    return left_s + " " * pad + right_s


def _render_row(row_fields: list[Field], g: _Glyphs, ellipsis: str) -> list[str]:
    widths = [
        max((f.end - f.start + 1) * _CHARS_PER_BIT - 1, _MIN_CELL_WIDTH) for f in row_fields
    ]
    # The header's numbers align under the box: the first field's slot
    # includes the left corner's column (width + 1), every other field's
    # slot lines up with its dash run only (no allowance for a trailing
    # corner column after the last field) -- reverse-engineered from the
    # reference example's exact column positions (see renderer module docstring).
    header_widths = [w + 1 if i == 0 else w for i, w in enumerate(widths)]
    header = " " + " ".join(
        _header_slot(f.start, f.end, w)
        for f, w in zip(row_fields, header_widths, strict=True)
    )
    top = " " + g.tl + g.tee_d.join(g.h * w for w in widths) + g.tr
    mid = (
        " " + g.v
        + g.v.join(_center(f.label, w, ellipsis) for f, w in zip(row_fields, widths, strict=True))
        + g.v
    )
    bot = " " + g.bl + g.tee_u.join(g.h * w for w in widths) + g.br
    return [header, top, mid, bot]


def render(d: PacketDiagram, *, use_ascii: bool = False) -> str:
    g = _ASCII if use_ascii else _UNICODE
    ellipsis = "..." if use_ascii else "…"

    if not d.fields:
        return d.title

    rows = _split_into_rows(d.fields, BITS_PER_ROW)
    lines: list[str] = []
    for row_fields in rows:
        lines.extend(_render_row(row_fields, g, ellipsis))

    if d.title:
        total_width = max(string_width(line) for line in lines)
        pad = total_width - string_width(d.title)
        left = pad // 2
        lines.insert(0, " " * max(left, 0) + d.title)

    return "\n".join(lines)

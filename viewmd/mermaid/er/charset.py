"""Box-drawing glyph sets, ported from pkg/er/renderer.go's `glyphs` struct."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Glyphs:
    h: str
    v: str
    tl: str
    tr: str
    bl: str
    br: str
    tee_d: str
    tee_u: str
    tee_l: str
    tee_r: str
    cross: str
    hd: str  # dashed horizontal line, for non-identifying relationships
    vd: str  # dashed vertical line, for non-identifying relationships


UNICODE = Glyphs(
    h="─", v="│", tl="┌", tr="┐", bl="└", br="┘",
    tee_d="┬", tee_u="┴", tee_l="┤", tee_r="├", cross="┼",
    # '·' (U+00B7 MIDDLE DOT) and ':' (U+003A COLON) rather than '┈'
    # (U+2508) and '┊' (U+250A): those box-drawing dash glyphs sit outside
    # the basic box-drawing block most monospace terminal fonts actually
    # cover and render blank, making dashed relationship lines
    # indistinguishable from empty space. Both replacements have
    # near-universal monospace coverage and read as a consistent dotted
    # style, matching VIEWMD-0021's fix for sequence-diagram dotted lines.
    hd="·", vd=":",
)

ASCII = Glyphs(
    h="-", v="|", tl="+", tr="+", bl="+", br="+",
    tee_d="+", tee_u="+", tee_l="+", tee_r="+", cross="+",
    hd=".", vd=":",
)

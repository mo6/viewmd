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
    hd="┈", vd="┊",
)

ASCII = Glyphs(
    h="-", v="|", tl="+", tr="+", bl="+", br="+",
    tee_d="+", tee_u="+", tee_l="+", tee_r="+", cross="+",
    hd=".", vd=":",
)

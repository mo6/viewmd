"""Box-drawing glyph sets, ported from pkg/sequence/charset.go."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class BoxChars:
    top_left: str
    top_right: str
    bottom_left: str
    bottom_right: str
    horizontal: str
    vertical: str
    tee_down: str
    tee_right: str
    tee_left: str
    cross: str
    arrow_right: str
    arrow_left: str
    cross_head: str  # head of -x / --x (lost/failed message)
    point_right: str  # head of -) / --) (async message)
    point_left: str
    circle: str  # central-connection marker ("()") on a lifeline
    solid_line: str
    dotted_line: str
    self_top_right: str
    self_bottom: str


ASCII = BoxChars(
    top_left="+", top_right="+", bottom_left="+", bottom_right="+",
    horizontal="-", vertical="|",
    tee_down="+", tee_right="+", tee_left="+", cross="+",
    arrow_right=">", arrow_left="<",
    cross_head="x", point_right=")", point_left="(",
    circle="o", solid_line="-", dotted_line=".",
    self_top_right="+", self_bottom="+",
)

UNICODE = BoxChars(
    top_left="┌", top_right="┐", bottom_left="└", bottom_right="┘",
    horizontal="─", vertical="│",
    tee_down="┬", tee_right="├", tee_left="┤", cross="┼",
    arrow_right="►", arrow_left="◄",
    cross_head="×", point_right=")", point_left="(",
    # 'o' rather than '○': the latter is East-Asian-ambiguous width and would
    # break column alignment in CJK-capable terminals.
    circle="o", solid_line="─", dotted_line="┈",
    self_top_right="┐", self_bottom="┘",
)

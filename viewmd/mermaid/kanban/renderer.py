"""Kanban board renderer (VIEWMD-0034).

No upstream reference implementation to port from (mermaid-ascii has no
kanban support), so this is hand-written directly against Mermaid's own
kanban rendering (the maintainer-supplied screenshot referenced in the
issue's mock-up), same posture as the pie/quadrant renderers.

Coloring (requirements 8a-8c) is always on, same posture as the flowchart
renderer's `classDef` coloring (`viewmd/mermaid/__init__.py:render` doesn't
thread a color flag through to either) -- see the issue's Non-goals.
"""

from __future__ import annotations

from dataclasses import dataclass

from viewmd.mermaid.grid.canvas import wrap_text_in_color, wrap_text_styled
from viewmd.mermaid.kanban.parser import Card, Column, KanbanDiagram
from viewmd.mermaid.textutil import width as string_width
from viewmd.mermaid.textutil import wrap_words

__all__ = ["render"]


@dataclass(frozen=True)
class _Glyphs:
    h: str
    v: str
    tl: str
    tr: str
    bl: str
    br: str
    tee_l: str  # ├
    tee_r: str  # ┤


_UNICODE = _Glyphs(h="─", v="│", tl="┌", tr="┐", bl="└", br="┘", tee_l="├", tee_r="┤")
_ASCII = _Glyphs(h="-", v="|", tl="+", tr="+", bl="+", br="+", tee_l="+", tee_r="+")

# Requirement 8a: 8-hue categorical palette, cycling past 8 columns. Values
# are the "dark" half of the dataviz skill's light/dark pairs (references/
# palette.md) -- viewmd has no terminal light/dark background detection to
# pick between the two, so one fixed variant per hue is used throughout.
_CATEGORICAL = [
    "3987e5",  # blue
    "d95926",  # orange
    "199e70",  # aqua
    "c98500",  # yellow
    "d55181",  # magenta
    "008300",  # green
    "9085e9",  # violet
    "e66767",  # red
]

# Requirement 8b: fixed 4-step status palette, same hex both modes.
_STATUS = {
    "good": "0ca30c",
    "warning": "fab219",
    "serious": "ec835a",
    "critical": "d03b3b",
}

# Requirement 8b: Very Low/Low collapse onto "good" -- maintainer sign-off
# (e) in the issue.
_PRIORITY_STATUS = {
    "very low": "good",
    "low": "good",
    "medium": "warning",
    "high": "serious",
    "very high": "critical",
}
_PRIORITY_TOKEN = {
    "very low": "VL",
    "low": "L",
    "medium": "M",
    "high": "H",
    "very high": "VH",
}

# Requirement 8c: ticket reuses categorical slot 1 ("link" hue); assigned
# gets its own fixed, saturated hue (maintainer sign-off (f)) -- categorical
# slot 7 (violet), distinct from every column header hue a 6-8 column board
# would use and from the ticket hue.
_TICKET_COLOR = _CATEGORICAL[0]
_ASSIGNED_COLOR = _CATEGORICAL[6]

_DEFAULT_CONTENT_WIDTH = 26


def _priority_key(priority: str | None) -> str | None:
    if not priority:
        return None
    key = priority.strip().lower()
    return key if key in _PRIORITY_TOKEN else None


def _metadata_parts(card: Card) -> tuple[str, str]:
    """Plain-text (uncolored) left ("[H] TICKET-1") and right ("assignee")
    halves of a card's metadata line, per requirement 8. Either half may be
    empty; both empty means the card has no metadata to render at all
    (maintainer sign-off (c): omit the line entirely, not a blank line)."""
    key = _priority_key(card.priority)
    left_parts = []
    if key:
        left_parts.append(f"[{_PRIORITY_TOKEN[key]}]")
    if card.ticket:
        left_parts.append(card.ticket)
    return " ".join(left_parts), card.assigned or ""


def _metadata_natural_width(card: Card) -> int:
    left, right = _metadata_parts(card)
    if not left and not right:
        return 0
    sep = 1 if left and right else 0
    return string_width(left) + sep + string_width(right)


def _content_width(diagram: KanbanDiagram) -> int:
    """Requirement 6/8: one uniform card content width across the whole
    board (maintainer sign-off (a)), wide enough to fit every card's
    metadata line without truncation -- a label alone never needs to grow
    it, since long labels word-wrap (requirement 7) instead."""
    needed = _DEFAULT_CONTENT_WIDTH
    for column in diagram.columns:
        for card in column.cards:
            needed = max(needed, _metadata_natural_width(card))
    return needed


def _metadata_line(card: Card, content_width: int, *, color: bool) -> str | None:
    plain_left, plain_right = _metadata_parts(card)
    if not plain_left and not plain_right:
        return None

    colored_left = plain_left
    key = _priority_key(card.priority)
    if key and color:
        token = f"[{_PRIORITY_TOKEN[key]}]"
        status_hex = _STATUS[_PRIORITY_STATUS[key]]
        colored_token = wrap_text_in_color(token, status_hex)
        colored_left = colored_token if not card.ticket else (
            f"{colored_token} {wrap_text_styled(card.ticket, fg=_TICKET_COLOR, underline=True)}"
        )
    elif card.ticket and color:
        colored_left = wrap_text_styled(card.ticket, fg=_TICKET_COLOR, underline=True)

    colored_right = plain_right
    if plain_right and color:
        colored_right = wrap_text_in_color(plain_right, _ASSIGNED_COLOR)

    sep = 1 if plain_left and plain_right else 0
    pad = max(content_width - string_width(plain_left) - string_width(plain_right), sep)
    return colored_left + " " * pad + colored_right


def _contrast_ink(hex_: str) -> str:
    r, g, b = int(hex_[0:2], 16), int(hex_[2:4], 16), int(hex_[4:6], 16)
    luminance = 0.299 * r + 0.587 * g + 0.114 * b
    return "000000" if luminance > 150 else "ffffff"


def _render_card(card: Card, g: _Glyphs, content_width: int, *, color: bool) -> list[str]:
    label_lines = wrap_words(card.label, content_width)
    meta_line = _metadata_line(card, content_width, color=color)

    lines = [g.tl + g.h * (content_width + 2) + g.tr]
    for line in label_lines:
        pad = max(content_width - string_width(line), 0)
        lines.append(f"{g.v} {line}{' ' * pad} {g.v}")
    if meta_line is not None:
        lines.append(f"{g.v} {meta_line} {g.v}")
    lines.append(g.bl + g.h * (content_width + 2) + g.br)
    return lines


def _render_column(
    column: Column, g: _Glyphs, content_width: int, column_inner_width: int, *,
    header_color: str, color: bool,
) -> list[str]:
    lines = [g.tl + g.h * column_inner_width + g.tr]

    header_text = column.label.center(column_inner_width)
    if color:
        header_text = wrap_text_styled(header_text, fg=_contrast_ink(header_color),
                                        bg=header_color)
    lines.append(f"{g.v}{header_text}{g.v}")
    lines.append(g.tee_l + g.h * column_inner_width + g.tee_r)

    for card in column.cards:
        for card_line in _render_card(card, g, content_width, color=color):
            lines.append(f"{g.v}  {card_line}  {g.v}")

    lines.append(g.bl + g.h * column_inner_width + g.br)
    return lines


def render(diagram: KanbanDiagram, *, use_ascii: bool = False) -> str:
    g = _ASCII if use_ascii else _UNICODE
    content_width = _content_width(diagram)
    card_box_width = content_width + 4  # 2 border cols + 2 padding cols
    column_inner_width = card_box_width + 4  # 2-space margin either side

    blocks = [
        _render_column(
            column, g, content_width, column_inner_width,
            header_color=_CATEGORICAL[i % len(_CATEGORICAL)], color=True,
        )
        for i, column in enumerate(diagram.columns)
    ]

    column_box_width = column_inner_width + 2
    height = max(len(block) for block in blocks)
    rows = []
    for r in range(height):
        row = " ".join(
            block[r] if r < len(block) else " " * column_box_width for block in blocks
        )
        rows.append(row)
    return "\n".join(rows)

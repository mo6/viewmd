#!/usr/bin/env python3
"""Proof of concept for VIEWMD-0034 (Mermaid kanban diagrams).

Not part of the shipped `viewmd` package -- a throwaway script to validate the
issue's box-drawing layout and column/priority/ticket/assignee coloring against
real input before committing to the design. Run against the bundled example:

    python3 poc/kanban/kanban_poc.py poc/kanban/example.mmd
    python3 poc/kanban/kanban_poc.py poc/kanban/example.mmd --color always
    python3 poc/kanban/kanban_poc.py poc/kanban/example.mmd --color never
"""

from __future__ import annotations

import argparse
import os
import re
import sys
import textwrap
from dataclasses import dataclass, field

# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------

_LABEL_RE = re.compile(
    r"^(?:(?P<id>[A-Za-z0-9_-]+)\[(?P<idlabel>.*)\]|\[(?P<barelabel>.*)\]|(?P<bare>[^@]+))"
    r"(?:@\{(?P<meta>.*)\})?\s*$"
)


@dataclass
class Card:
    label: str
    ticket: str | None = None
    assigned: str | None = None
    priority: str | None = None


@dataclass
class Column:
    name: str
    cards: list[Card] = field(default_factory=list)


class ParseError(Exception):
    pass


def _strip_front_matter(text: str) -> str:
    lines = text.splitlines()
    if lines and lines[0].strip() == "---":
        for i in range(1, len(lines)):
            if lines[i].strip() == "---":
                return "\n".join(lines[i + 1 :])
        raise ParseError("unterminated front-matter block")
    return text


def _parse_metadata(raw: str) -> dict[str, str]:
    meta: dict[str, str] = {}
    for part in raw.split(","):
        part = part.strip()
        if not part or ":" not in part:
            continue
        key, _, value = part.partition(":")
        key = key.strip()
        value = value.strip().strip("'").strip('"')
        meta[key] = value
    return meta


def _parse_label_line(line: str) -> tuple[str, dict[str, str]]:
    m = _LABEL_RE.match(line.strip())
    if not m:
        raise ParseError(f"could not parse line: {line!r}")
    label = m.group("idlabel") or m.group("barelabel") or m.group("bare")
    if label is None:
        raise ParseError(f"could not extract a label from: {line!r}")
    label = label.strip()
    meta = _parse_metadata(m.group("meta")) if m.group("meta") else {}
    return label, meta


def parse(text: str) -> list[Column]:
    body = _strip_front_matter(text)
    lines = [ln for ln in body.splitlines() if ln.strip() and not ln.strip().startswith("%%")]
    if not lines or lines[0].strip() != "kanban":
        raise ParseError("expected a line reading 'kanban'")
    lines = lines[1:]
    if not lines:
        raise ParseError("empty kanban diagram")

    col_indent = min(len(ln) - len(ln.lstrip(" ")) for ln in lines)

    columns: list[Column] = []
    for line in lines:
        indent = len(line) - len(line.lstrip(" "))
        label, meta = _parse_label_line(line)
        if indent <= col_indent:
            columns.append(Column(name=label))
        else:
            if not columns:
                raise ParseError(f"card line before any column declared: {line!r}")
            columns[-1].cards.append(
                Card(
                    label=label,
                    ticket=meta.get("ticket"),
                    assigned=meta.get("assigned"),
                    priority=meta.get("priority"),
                )
            )
    return columns


def sniff(text: str) -> bool:
    return _strip_front_matter(text).lstrip().startswith("kanban")


# ---------------------------------------------------------------------------
# Color (VIEWMD-0034 requirements 8a-8c) -- values from Anthropic's `dataviz`
# skill's validated default palette (references/palette.md), dark-surface column.
# ---------------------------------------------------------------------------

CATEGORICAL = [
    ("blue", "3987e5"),
    ("orange", "d95926"),
    ("aqua", "199e70"),
    ("yellow", "c98500"),
    ("magenta", "d55181"),
    ("green", "008300"),
    ("violet", "9085e9"),
    ("red", "e66767"),
]

STATUS = {
    "very low": ("good", "0ca30c"),
    "low": ("good", "0ca30c"),
    "medium": ("warning", "fab219"),
    "high": ("serious", "ec835a"),
    "very high": ("critical", "d03b3b"),
}

LINK_HEX = "3987e5"        # ticket: categorical slot 1, reused
SECONDARY_HEX = "c3c2b7"   # assigned: secondary ink (dark surface)
HEADER_TEXT_HEX = "ffffff"

PRIORITY_TOKEN = {
    "very low": "[VL]",
    "low": "[L]",
    "medium": "[M]",
    "high": "[H]",
    "very high": "[VH]",
}


def _hex_to_rgb(h: str) -> tuple[int, int, int]:
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


class Colorizer:
    """Wraps text in 24-bit ANSI escapes, or passes it through unchanged."""

    def __init__(self, enabled: bool) -> None:
        self.enabled = enabled

    def fg(self, text: str, hex_: str) -> str:
        if not self.enabled or not text:
            return text
        r, g, b = _hex_to_rgb(hex_)
        return f"\x1b[38;2;{r};{g};{b}m{text}\x1b[0m"

    def bg(self, text: str, hex_: str) -> str:
        if not self.enabled or not text:
            return text
        r, g, b = _hex_to_rgb(hex_)
        return f"\x1b[48;2;{r};{g};{b}m{text}\x1b[0m"

    def underline(self, text: str) -> str:
        if not self.enabled or not text:
            return text
        return f"\x1b[4m{text}\x1b[24m"


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------

TEXT_W = 26
CARD_TOTAL = TEXT_W + 4       # "┌" + "─"*(TEXT_W+2) + "┐"
COL_INNER = CARD_TOTAL + 2    # 1-space pad each side of the card box


def _wrap(text: str, width: int) -> list[str]:
    return textwrap.wrap(text, width) or [""]


def _pad_visible(s: str, width: int) -> str:
    """Right-pad `s` to `width` *visible* columns, ignoring ANSI escapes."""
    visible_len = len(re.sub(r"\x1b\[[0-9;]*m", "", s))
    return s + " " * max(0, width - visible_len)


def _center_visible(s: str, width: int) -> str:
    visible_len = len(re.sub(r"\x1b\[[0-9;]*m", "", s))
    pad = max(0, width - visible_len)
    left = pad // 2
    right = pad - left
    return " " * left + s + " " * right


def render_card(card: Card, c: Colorizer) -> list[str]:
    lines = [f"┌{'─' * (TEXT_W + 2)}┐"]
    for ln in _wrap(card.label, TEXT_W):
        lines.append(f"│ {ln.ljust(TEXT_W)} │")

    if card.ticket or card.assigned or card.priority:
        prio_key = (card.priority or "").lower()
        token = PRIORITY_TOKEN.get(prio_key, "")
        if token:
            _, hex_ = STATUS.get(prio_key, ("", "ffffff"))
            token = c.fg(token, hex_)
        ticket = c.underline(c.fg(card.ticket, LINK_HEX)) if card.ticket else ""
        assigned = c.fg(card.assigned, SECONDARY_HEX) if card.assigned else ""

        left = " ".join(p for p in (token, ticket) if p)
        left_visible = len(re.sub(r"\x1b\[[0-9;]*m", "", left))
        assigned_visible = len(re.sub(r"\x1b\[[0-9;]*m", "", assigned))
        space = max(1, TEXT_W - left_visible - assigned_visible)
        meta = left + " " * space + assigned
        meta = _pad_visible(meta, TEXT_W)
        lines.append(f"│ {meta} │")

    lines.append(f"└{'─' * (TEXT_W + 2)}┘")
    return lines


def render_column(col: Column, color_hex: str, c: Colorizer) -> list[str]:
    lines = [f"┌{'─' * (COL_INNER + 2)}┐"]
    header_text = c.fg(col.name.center(COL_INNER), HEADER_TEXT_HEX)
    header_bg = c.bg(header_text, color_hex)
    lines.append(f"│ {header_bg} │")
    lines.append(f"├{'─' * (COL_INNER + 2)}┤")

    first = True
    for card in col.cards:
        if not first:
            lines.append(f"│{' ' * (COL_INNER + 2)}│")
        first = False
        for cl in render_card(card, c):
            lines.append(f"│ {_center_visible(cl, COL_INNER)} │")

    lines.append(f"│{' ' * (COL_INNER + 2)}│")
    lines.append(f"└{'─' * (COL_INNER + 2)}┘")
    return lines


def render(columns: list[Column], c: Colorizer) -> str:
    rendered = [
        render_column(col, CATEGORICAL[i % len(CATEGORICAL)][1], c)
        for i, col in enumerate(columns)
    ]
    maxh = max(len(r) for r in rendered)
    for r in rendered:
        width = len(re.sub(r"\x1b\[[0-9;]*m", "", r[0]))
        while len(r) < maxh:
            r.append(" " * width)
    return "\n".join(" ".join(r[row] for r in rendered) for row in range(maxh))


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
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "path", nargs="?", default=os.path.join(os.path.dirname(__file__), "example.mmd")
    )
    parser.add_argument("--color", choices=["auto", "always", "never"], default="auto")
    args = parser.parse_args()

    with open(args.path, encoding="utf-8") as f:
        text = f.read()

    if not sniff(text):
        print("not a kanban fence", file=sys.stderr)
        raise SystemExit(1)

    columns = parse(text)
    colorizer = Colorizer(enabled=_resolve_color(args.color))
    print(render(columns, colorizer))


if __name__ == "__main__":
    main()

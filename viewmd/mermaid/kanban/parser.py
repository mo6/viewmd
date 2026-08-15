"""Kanban board parser (VIEWMD-0034).

No upstream reference implementation to port from (mermaid-ascii has no
kanban support), so this is hand-written directly against Mermaid's own
syntax (https://mermaid.ai/open-source/syntax/kanban.html), same posture as
the pie/quadrant/packet parsers.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from viewmd.mermaid.textutil import strip_front_matter

KANBAN_DIAGRAM_KEYWORD = "kanban"

# A column or card node: an optional id followed by a `[label]`, e.g.
# `id9[Ready for deploy]` or bare `[In progress]` (no id).
_ID_BRACKET_RE = re.compile(r"^(?P<id>[\w-]+)?\[(?P<label>.*)\]\s*$")
# A card's optional `@{ ... }` metadata block, anchored at the start of the
# remainder of the line after its node syntax.
_META_BLOCK_RE = re.compile(r"^@\{(?P<body>.*)\}\s*$")
_META_PAIR_RE = re.compile(r"([\w-]+)\s*:\s*('[^']*'|[^,}]+)")


class ParseError(Exception):
    pass


@dataclass
class Card:
    id: str
    label: str
    ticket: str | None = None
    assigned: str | None = None
    priority: str | None = None


@dataclass
class Column:
    id: str
    label: str
    cards: list[Card] = field(default_factory=list)


@dataclass
class KanbanDiagram:
    columns: list[Column] = field(default_factory=list)


def sniff(text: str) -> bool:
    """Whether `text`'s first meaningful line (after an optional YAML
    front-matter block) declares a kanban board."""
    for line in strip_front_matter(text).split("\n"):
        t = line.strip()
        if t == "":
            continue
        return t.lower().startswith(KANBAN_DIAGRAM_KEYWORD.lower())
    return False


def _parse_node(content: str) -> tuple[str | None, str]:
    m = _ID_BRACKET_RE.match(content)
    if m:
        return m.group("id"), m.group("label")
    return None, content


def _split_metadata(content: str) -> tuple[str, str | None]:
    idx = content.find("@{")
    if idx == -1:
        return content.strip(), None
    node_part = content[:idx].strip()
    m = _META_BLOCK_RE.match(content[idx:])
    if not m:
        raise ParseError(f"unterminated metadata block: {content!r}")
    return node_part, m.group("body")


def _apply_metadata(card: Card, body: str) -> None:
    for key, raw_value in _META_PAIR_RE.findall(body):
        value = raw_value.strip()
        if len(value) >= 2 and value[0] == "'" and value[-1] == "'":
            value = value[1:-1]
        if key == "ticket":
            card.ticket = value
        elif key == "assigned":
            card.assigned = value
        elif key == "priority":
            card.priority = value
        # Requirement 4: an unrecognized key is ignored, not a parse failure.


def parse(text: str) -> KanbanDiagram:
    if not sniff(text):
        raise ParseError(f'expected "{KANBAN_DIAGRAM_KEYWORD}" keyword')

    lines = strip_front_matter(text).split("\n")
    header_idx = next(i for i, ln in enumerate(lines) if ln.strip())

    diagram = KanbanDiagram()
    column_indent: int | None = None
    current_column: Column | None = None
    auto_id = 0

    for raw in lines[header_idx + 1:]:
        if not raw.strip():
            continue
        indent = len(raw) - len(raw.lstrip(" "))
        content = raw.strip()

        if column_indent is None or indent <= column_indent:
            column_indent = indent
            node_id, label = _parse_node(content)
            current_column = Column(id=node_id or label, label=label)
            diagram.columns.append(current_column)
            continue

        if current_column is None:
            raise ParseError(f"card line before any column: {raw!r}")

        node_part, meta_body = _split_metadata(content)
        m = _ID_BRACKET_RE.match(node_part)
        if not m:
            raise ParseError(f"could not parse card line: {raw!r}")
        node_id = m.group("id")
        if not node_id:
            auto_id += 1
            node_id = f"_card{auto_id}"
        card = Card(id=node_id, label=m.group("label"))
        if meta_body is not None:
            _apply_metadata(card, meta_body)
        current_column.cards.append(card)

    if not diagram.columns:
        raise ParseError("expected at least one column")

    return diagram

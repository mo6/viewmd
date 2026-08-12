"""Mindmap diagram parser (VIEWMD-0045).

No upstream reference implementation to port from (mermaid-ascii has no
mindmap support), so this is hand-written directly against Mermaid's own
syntax (https://mermaid.js.org/syntax/mindmap.html), same posture as the
pie/quadrant/packet/kanban parsers. termaid's indentation-tree approach is a
useful cross-check, not an oracle to match exactly.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from viewmd.mermaid.textutil import strip_front_matter

MINDMAP_DIAGRAM_KEYWORD = "mindmap"

# Shape markers, longest-first so `((Circle))` wins over `(Round)`. An optional
# Mermaid node-id prefix (`root((mindmap))`) is stripped with the markers --
# only the inner label text remains (requirement 3).
_SHAPE_RES = (
    re.compile(r"^(?:[\w-]+)?\(\((.+)\)\)$"),  # ((Circle)) / id((Circle))
    re.compile(r"^(?:[\w-]+)?\{\{(.+)\}\}$"),  # {{Hexagon}}
    re.compile(r"^(?:[\w-]+)?\((.+)\)$"),  # (Round)
    re.compile(r"^(?:[\w-]+)?\[(.+)\]$"),  # [Square]
    re.compile(r"^(?:[\w-]+)?\)(.+)\($"),  # )Cloud(
)


class ParseError(Exception):
    pass


@dataclass
class MindmapNode:
    """One mindmap node: plain label text for layout, plus style spans for ANSI."""

    plain: str
    # (text, bold, italic) segments covering `plain` without the markdown markers.
    segments: list[tuple[str, bool, bool]] = field(default_factory=list)
    children: list[MindmapNode] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.segments:
            self.segments = [(self.plain, False, False)]


@dataclass
class MindmapDiagram:
    root: MindmapNode | None = None


def sniff(text: str) -> bool:
    """Whether `text`'s first meaningful line (after an optional YAML
    front-matter block) declares a mindmap."""
    for line in strip_front_matter(text).split("\n"):
        t = line.strip()
        if t == "" or t.startswith("%%"):
            continue
        return t.lower().startswith(MINDMAP_DIAGRAM_KEYWORD.lower())
    return False


def _strip_shape_markers(label: str) -> str:
    for pat in _SHAPE_RES:
        m = pat.match(label)
        if m:
            return m.group(1)
    return label


def _parse_markdown_spans(text: str) -> list[tuple[str, bool, bool]]:
    """Split a label into `(text, bold, italic)` spans for `**bold**`,
    `*italic*`, and `***both***` (requirement 8). Unclosed markers stay
    literal. Applied after shape-marker stripping."""
    spans: list[tuple[str, bool, bool]] = []
    i = 0
    n = len(text)
    plain_buf: list[str] = []

    def flush_plain() -> None:
        if plain_buf:
            spans.append(("".join(plain_buf), False, False))
            plain_buf.clear()

    while i < n:
        if text.startswith("***", i):
            end = text.find("***", i + 3)
            if end != -1:
                flush_plain()
                spans.append((text[i + 3:end], True, True))
                i = end + 3
                continue
        if text.startswith("**", i):
            end = text.find("**", i + 2)
            if end != -1:
                flush_plain()
                spans.append((text[i + 2:end], True, False))
                i = end + 2
                continue
        if text[i] == "*":
            end = text.find("*", i + 1)
            if end != -1:
                flush_plain()
                spans.append((text[i + 1:end], False, True))
                i = end + 1
                continue
        plain_buf.append(text[i])
        i += 1
    flush_plain()
    return spans or [("", False, False)]


def _make_node(raw_label: str) -> MindmapNode:
    stripped = _strip_shape_markers(raw_label)
    segments = _parse_markdown_spans(stripped)
    plain = "".join(seg for seg, _, _ in segments)
    return MindmapNode(plain=plain, segments=segments)


def parse(text: str) -> MindmapDiagram:
    if not sniff(text):
        raise ParseError(f'expected "{MINDMAP_DIAGRAM_KEYWORD}" keyword')

    lines = strip_front_matter(text).split("\n")
    header_idx = next(
        i for i, ln in enumerate(lines) if ln.strip() and not ln.strip().startswith("%%")
    )

    body: list[tuple[int, str]] = []
    for raw in lines[header_idx + 1:]:
        # Requirement 4: strip inline `%%` comments; ignore blank lines.
        if "%%" in raw:
            raw = raw[: raw.find("%%")]
        if not raw.strip():
            continue
        indent = len(raw) - len(raw.lstrip(" \t"))
        body.append((indent, raw.strip()))

    if not body:
        raise ParseError("expected at least one mindmap node")

    diagram = MindmapDiagram()
    stack: list[tuple[int, MindmapNode]] = []

    for indent, label in body:
        node = _make_node(label)
        while stack and stack[-1][0] >= indent:
            stack.pop()
        if stack:
            stack[-1][1].children.append(node)
        elif diagram.root is None:
            diagram.root = node
        else:
            # A second least-indented node: treat as another child of root
            # rather than a parse failure (matches Mermaid/termaid tolerance).
            diagram.root.children.append(node)
        stack.append((indent, node))

    return diagram

"""block-beta diagram parser (VIEWMD-0040).

No upstream reference implementation to port from (mermaid-ascii has no
block-beta support), so this is hand-written directly against Mermaid's own
syntax (https://mermaid.js.org/syntax/block.html) and the maintainer-supplied
reference examples in the issue -- same posture as the pie/quadrant/packet/
kanban parsers. Only the quoted-label rectangle (`id["label"]`), `columns N`,
`:N` spans, and unlabeled `A-->B` edges are accepted; every other block-beta
construct is a parse failure (the follow-ups VIEWMD-0053..0057).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from viewmd.mermaid.textutil import strip_front_matter

BLOCK_DIAGRAM_KEYWORD = "block-beta"

# `id["label"]` with an optional `:N` column-span suffix. Ids match the other
# Mermaid parsers' `[\w.-]+` vocabulary; the quoted label is the only shape
# this issue accepts (see Non-goals).
_BLOCK_RE = re.compile(r'([\w.-]+)\["([^"]*)"\](?::(\d+))?')
_EDGE_RE = re.compile(r"([\w.-]+)\s*-->\s*([\w.-]+)")
_COLUMNS_RE = re.compile(r"columns\s+(\d+)", re.IGNORECASE)


class ParseError(Exception):
    pass


@dataclass
class Block:
    id: str
    label: str
    span: int = 1
    # Column-count that was active when this block was declared (`None` means
    # no `columns` directive yet -- every block goes in a single row).
    columns: int | None = None


@dataclass
class Edge:
    src: str
    dst: str


@dataclass
class BlockDiagram:
    blocks: list[Block] = field(default_factory=list)
    edges: list[Edge] = field(default_factory=list)


def sniff(text: str) -> bool:
    """Whether `text`'s first meaningful line (after an optional YAML
    front-matter block) declares a `block-beta` diagram (case-insensitive,
    whole token -- matching gantt/er/pie's own sniff convention)."""
    for line in strip_front_matter(text).split("\n"):
        t = line.strip()
        if t == "" or t.startswith("%%"):
            continue
        low = t.lower()
        kw = BLOCK_DIAGRAM_KEYWORD
        return low == kw or low.startswith(kw + " ")
    return False


def parse(text: str) -> BlockDiagram:
    if not sniff(text):
        raise ParseError(f'expected "{BLOCK_DIAGRAM_KEYWORD}" keyword')

    lines = strip_front_matter(text).split("\n")
    header_idx = next(
        i for i, ln in enumerate(lines) if ln.strip() and not ln.strip().startswith("%%")
    )

    diagram = BlockDiagram()
    declared: set[str] = set()
    current_columns: int | None = None

    header_rest = re.sub(
        rf"(?i)^{re.escape(BLOCK_DIAGRAM_KEYWORD)}\b", "", lines[header_idx]
    ).strip()
    pending = [header_rest] if header_rest else []
    pending.extend(lines[header_idx + 1 :])

    for raw in pending:
        line = raw.split("%%", 1)[0].strip()
        if not line:
            continue
        for item in _parse_line(line):
            if isinstance(item, int):
                current_columns = item
                continue
            if isinstance(item, Edge):
                if item.src not in declared or item.dst not in declared:
                    raise ParseError(
                        f"edge {item.src}-->{item.dst} references an undeclared id"
                    )
                diagram.edges.append(item)
                continue
            if item.id in declared:
                raise ParseError(f"duplicate block id {item.id!r}")
            if current_columns is not None and item.span > current_columns:
                raise ParseError(
                    f"block {item.id!r} span {item.span} exceeds columns {current_columns}"
                )
            item.columns = current_columns
            declared.add(item.id)
            diagram.blocks.append(item)

    return diagram


def _parse_line(line: str) -> list[Block | Edge | int]:
    """Tokenize one statement line into blocks, edges, and/or a `columns N`
    count (returned as a bare int). Multiple declarations on one line
    (`B["Left"] C["Center"] D["Right"]`) are the second reference example's
    shape and must parse in left-to-right order."""
    items: list[Block | Edge | int] = []
    pos = 0
    n = len(line)
    while pos < n:
        while pos < n and line[pos].isspace():
            pos += 1
        if pos >= n:
            break
        m = _COLUMNS_RE.match(line, pos)
        if m:
            count = int(m.group(1))
            if count < 1:
                raise ParseError(f"columns count must be >= 1, got {count}")
            items.append(count)
            pos = m.end()
            continue
        m = _BLOCK_RE.match(line, pos)
        if m:
            span = int(m.group(3)) if m.group(3) is not None else 1
            if span < 1:
                raise ParseError(f"block {m.group(1)!r} span must be >= 1, got {span}")
            items.append(Block(id=m.group(1), label=m.group(2), span=span))
            pos = m.end()
            continue
        m = _EDGE_RE.match(line, pos)
        if m:
            items.append(Edge(src=m.group(1), dst=m.group(2)))
            pos = m.end()
            continue
        raise ParseError(f"could not parse: {line[pos:]!r}")
    return items

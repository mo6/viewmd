"""Multi-line node/edge/subgraph label text model, ported from cmd/label.go."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from viewmd.mermaid.textutil import width as _width

_HTML_BREAK_RE = re.compile(r"<br\s*/?>", re.IGNORECASE)

LABEL_LINE_GAP = 1


@dataclass
class GraphLabel:
    lines: list[str] = field(default_factory=lambda: [""])
    width: int = 0

    def content_height(self) -> int:
        if not self.lines:
            return 0
        return len(self.lines) + (len(self.lines) - 1) * LABEL_LINE_GAP


def new_graph_label(raw: str) -> GraphLabel:
    normalized = _HTML_BREAK_RE.sub("\n", raw)
    normalized = normalized.replace("\\n", "\n")

    lines = normalized.split("\n")
    if not lines:
        lines = [""]

    label_width = max((_width(line) for line in lines), default=0)
    return GraphLabel(lines=lines, width=label_width)

"""Pie chart parser (VIEWMD-0043).

No upstream reference implementation to port from (mermaid-ascii has no pie-chart
support), so this is hand-written directly against Mermaid's own syntax
(https://mermaid.js.org/syntax/pie.html), not a port.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

PIE_DIAGRAM_KEYWORD = "pie"

_SLICE_RE = re.compile(r'^"(?P<label>[^"]*)"\s*:\s*(?P<value>-?\d+(?:\.\d+)?)\s*$')


class ParseError(Exception):
    pass


@dataclass
class Slice:
    label: str
    value: float


@dataclass
class PieChart:
    title: str = ""
    show_data: bool = False
    slices: list[Slice] = field(default_factory=list)


def sniff(text: str) -> bool:
    """Whether `text`'s first meaningful line declares a pie chart
    (case-insensitive, whole token -- matching er/flowchart's own sniff
    convention -- `pie`, optionally followed by `showData` and/or `title ...`
    on the same line)."""
    for line in text.split("\n"):
        t = line.strip()
        if t == "" or t.startswith("%%"):
            continue
        low = t.lower()
        kw = PIE_DIAGRAM_KEYWORD.lower()
        return low == kw or low.startswith(kw + " ")
    return False


def parse(text: str) -> PieChart:
    if not sniff(text):
        raise ParseError(f'expected "{PIE_DIAGRAM_KEYWORD}" keyword')

    lines = text.split("\n")
    # Find the first meaningful line (the `pie [showData] [title ...]` header) --
    # mirrors sniff's own comment/blank-line tolerance rather than assuming
    # line 0 is it.
    header_idx = next(
        i for i, ln in enumerate(lines) if ln.strip() and not ln.strip().startswith("%%")
    )
    header = lines[header_idx].strip()

    chart = PieChart()
    chart.show_data = "showData" in header.split()
    m = re.search(r"\btitle\s+(.+)$", header)
    if m:
        chart.title = m.group(1).strip()

    for raw in lines[header_idx + 1:]:
        line = raw.split("%%", 1)[0].strip()
        if not line:
            continue
        if line.startswith("title "):
            chart.title = line[len("title "):].strip()
            continue
        sm = _SLICE_RE.match(line)
        if not sm:
            raise ParseError(f"could not parse slice line: {raw.strip()!r}")
        value = float(sm.group("value"))
        if value < 0:
            raise ParseError(f"negative slice value not allowed: {raw.strip()!r}")
        chart.slices.append(Slice(label=sm.group("label"), value=value))

    return chart

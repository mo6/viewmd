"""Quadrant chart parser (VIEWMD-0047).

No upstream reference implementation to port from (mermaid-ascii has no
quadrant-chart support; termaid's own rendering is a cross-check during
design, not an oracle -- see the issue's Design notes), so this is
hand-written directly against Mermaid's own syntax
(https://mermaid.js.org/syntax/quadrantChart.html), not a port.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, field

from viewmd.mermaid.textutil import strip_front_matter

QUADRANT_DIAGRAM_KEYWORD = "quadrantChart"

_TITLE_RE = re.compile(r"^title\s+(?P<text>.+)$")
_XAXIS_RE = re.compile(r"^x-axis\s+(?P<low>.+?)(?:\s*-->\s*(?P<high>.+))?$")
_YAXIS_RE = re.compile(r"^y-axis\s+(?P<low>.+?)(?:\s*-->\s*(?P<high>.+))?$")
_QUADRANT_RE = re.compile(r"^quadrant-(?P<n>[1-4])\s+(?P<text>.+)$")
_CLASSDEF_RE = re.compile(r"^classDef\s+(?P<name>[\w-]+)\s+(?P<rest>.*)$")
# A point line's shape (`<label>: [<x>, <y>] <optional style>`), matched
# loosely on the bracket contents first so a non-numeric coordinate can be
# recognized as *this* shape with bad data (requirement 9: skipped, not an
# abort of the whole chart) rather than falling through as an unrecognized
# line (which does abort -- see the `raise` at the end of the main loop).
_POINT_SHAPE_RE = re.compile(
    r"^(?P<label>[^:\[]+?)(?::::(?P<cls>[\w-]+))?\s*:\s*\[(?P<coords>[^\]]*)\]\s*(?P<rest>.*)$"
)
_STYLE_TOKEN_RE = re.compile(r"([\w-]+)\s*:\s*([^,]+)")


class ParseError(Exception):
    pass


@dataclass
class Point:
    label: str
    x: float
    y: float
    color: str | None = None


@dataclass
class QuadrantChart:
    title: str = ""
    x_low: str = ""
    x_high: str = ""
    y_low: str = ""
    y_high: str = ""
    quadrants: dict[int, str] = field(default_factory=dict)  # 1..4, Mermaid's own numbering
    points: list[Point] = field(default_factory=list)


def sniff(text: str) -> bool:
    """Whether `text`'s first meaningful line (after an optional YAML
    front-matter block) declares a quadrant chart (case-insensitive,
    matching pie/packet's own sniff convention)."""
    for line in strip_front_matter(text).split("\n"):
        t = line.strip()
        if t == "" or t.startswith("%%"):
            continue
        return t.lower().startswith(QUADRANT_DIAGRAM_KEYWORD.lower())
    return False


def _unquote(s: str) -> str:
    """Strips a single matching pair of double quotes, Mermaid's own escape
    for a label containing special characters (e.g. `y-axis Not Important -->
    "Important ❤"`) -- not stripped by any of the line regexes themselves,
    which capture the raw remainder of the line verbatim."""
    if len(s) >= 2 and s[0] == '"' and s[-1] == '"':
        return s[1:-1]
    return s


def _parse_style(rest: str) -> dict[str, str]:
    return {k.strip(): v.strip() for k, v in _STYLE_TOKEN_RE.findall(rest)}


def parse(text: str) -> QuadrantChart:
    if not sniff(text):
        raise ParseError(f'expected "{QUADRANT_DIAGRAM_KEYWORD}" keyword')

    lines = strip_front_matter(text).split("\n")
    # Mirrors sniff's own comment/blank-line tolerance rather than assuming
    # line 0 is the header.
    header_idx = next(
        i for i, ln in enumerate(lines) if ln.strip() and not ln.strip().startswith("%%")
    )

    chart = QuadrantChart()
    class_defs: dict[str, dict[str, str]] = {}
    # Points are collected raw and resolved against class_defs only after the
    # full source is scanned -- a `:::class` reference is free to appear
    # before its own `classDef` line, as in the "Example on styling" fixture.
    raw_points: list[tuple[str, str | None, float, float, dict[str, str]]] = []

    for raw in lines[header_idx + 1:]:
        line = raw.split("%%", 1)[0].strip()
        if not line:
            continue
        if m := _TITLE_RE.match(line):
            chart.title = _unquote(m.group("text").strip())
            continue
        if m := _XAXIS_RE.match(line):
            low = m.group("low").strip()
            if "-->" in low:
                # A genuinely empty low/high label either side of `-->`
                # (e.g. "x-axis  --> ") can't satisfy the high group's `.+`,
                # so the regex backtracks and swallows the whole "-->" into
                # `low` instead of failing outright -- treat that the same
                # as any other unparseable line rather than accepting "-->"
                # as a label.
                raise ParseError(f"could not parse line: {raw.strip()!r}")
            chart.x_low = _unquote(low)
            chart.x_high = _unquote((m.group("high") or "").strip())
            continue
        if m := _YAXIS_RE.match(line):
            low = m.group("low").strip()
            if "-->" in low:
                raise ParseError(f"could not parse line: {raw.strip()!r}")
            chart.y_low = _unquote(low)
            chart.y_high = _unquote((m.group("high") or "").strip())
            continue
        if m := _QUADRANT_RE.match(line):
            chart.quadrants[int(m.group("n"))] = _unquote(m.group("text").strip())
            continue
        if m := _CLASSDEF_RE.match(line):
            class_defs[m.group("name")] = _parse_style(m.group("rest"))
            continue
        if m := _POINT_SHAPE_RE.match(line):
            coords = [c.strip() for c in m.group("coords").split(",")]
            if len(coords) != 2:
                continue  # requirement 9: malformed point line skipped, not an abort
            try:
                x, y = float(coords[0]), float(coords[1])
            except ValueError:
                continue  # requirement 9
            if not (math.isfinite(x) and math.isfinite(y)):
                # float() also accepts "nan"/"inf"/"-inf" -- valid floats but
                # not valid coordinates (the renderer's round()/grid-index
                # math can't place them); treat the same as a non-numeric
                # coordinate (requirement 9: skipped, not an abort).
                continue
            raw_points.append((
                _unquote(m.group("label").strip()), m.group("cls"), x, y,
                _parse_style(m.group("rest")),
            ))
            continue
        raise ParseError(f"could not parse line: {raw.strip()!r}")

    if not chart.x_low or not chart.y_low:
        raise ParseError("expected both an x-axis and a y-axis declaration")

    for label, cls, x, y, style in raw_points:
        color = style.get("color")
        if color is None and cls and cls in class_defs:
            color = class_defs[cls].get("color")
        chart.points.append(Point(label=label, x=x, y=y, color=color))

    return chart

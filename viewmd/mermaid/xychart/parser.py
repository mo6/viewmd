"""XY-chart parser (VIEWMD-0048).

No upstream reference implementation to port from (mermaid-ascii has no
XY-chart support; termaid's own rendering is a cross-check during design,
not an oracle -- see the issue's Design notes), so this is hand-written
directly against Mermaid's own syntax
(https://mermaid.js.org/syntax/xyChart.html), not a port.

v1 scope is the categorical x-axis form plus at most one `bar` and one
`line` dataset (the combo case). Numeric x-axis ranges, extra series, and
horizontal orientation are rejected or ignored per the issue's Non-goals.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, field

from viewmd.mermaid.textutil import strip_front_matter

XYCHART_DIAGRAM_KEYWORDS = ("xychart-beta", "xychart")

_TITLE_RE = re.compile(r"^title\s+(?P<text>.+)$")
_XAXIS_CATS_RE = re.compile(
    r'^x-axis(?:\s+"(?P<title>[^"]*)")?\s*\[(?P<inner>.*)\]\s*$'
)
_XAXIS_RANGE_RE = re.compile(
    r'^x-axis(?:\s+"(?P<title>[^"]*)")?\s+(?P<lo>\S+)\s+-->\s+(?P<hi>\S+)\s*$'
)
_YAXIS_RE = re.compile(
    r'^y-axis(?:\s+"(?P<title>[^"]*)")?\s+(?P<lo>\S+)\s+-->\s+(?P<hi>\S+)\s*$'
)
_DATASET_RE = re.compile(
    r'^(?P<kind>bar|line)(?:\s+"(?P<name>[^"]*)")?\s*\[(?P<inner>.*)\]\s*$'
)
# A plain decimal; rejects `0.1.2`, `nan`, `inf` (float() would accept the
# last two), and per-point line labels (`1.5 "label"`).
_NUM_RE = re.compile(r"^[+-]?(?:\d+(?:\.\d*)?|\.\d+)$")


class ParseError(Exception):
    pass


@dataclass
class XYChart:
    title: str = ""
    x_title: str = ""
    y_title: str = ""
    categories: list[str] = field(default_factory=list)
    y_min: float | None = None
    y_max: float | None = None
    bar: list[float] | None = None
    line: list[float] | None = None
    horizontal: bool = False  # parsed and ignored; v1 always renders bottom-up


def sniff(text: str) -> bool:
    """Whether `text`'s first meaningful line (after an optional YAML
    front-matter block) declares an XY chart (`xychart-beta` or the bare
    `xychart` alias, case-insensitive, optionally followed by `horizontal`)."""
    for line in strip_front_matter(text).split("\n"):
        t = line.strip()
        if t == "" or t.startswith("%%"):
            continue
        return _header_keyword(t) is not None
    return False


def _header_keyword(line: str) -> str | None:
    parts = line.split()
    if not parts:
        return None
    kw = parts[0].lower()
    if kw in XYCHART_DIAGRAM_KEYWORDS:
        return kw
    return None


def _unquote(s: str) -> str:
    if len(s) >= 2 and s[0] == '"' and s[-1] == '"':
        return s[1:-1]
    return s


def _parse_number(s: str) -> float | None:
    s = s.strip()
    if not _NUM_RE.match(s):
        return None
    try:
        v = float(s)
    except ValueError:
        return None
    if not math.isfinite(v):
        return None
    return v


def _split_list(inner: str) -> list[str]:
    """Comma-split that respects double-quoted items (so a category
    `"Category 1"` stays one item)."""
    if not inner.strip():
        return []
    items: list[str] = []
    buf: list[str] = []
    in_quote = False
    for ch in inner:
        if ch == '"':
            in_quote = not in_quote
            buf.append(ch)
        elif ch == "," and not in_quote:
            items.append(_unquote("".join(buf).strip()))
            buf = []
        else:
            buf.append(ch)
    if in_quote:
        raise ParseError("unterminated quote in list")
    items.append(_unquote("".join(buf).strip()))
    return items


def _parse_values(inner: str, raw: str) -> list[float]:
    items = _split_list(inner)
    values: list[float] = []
    for item in items:
        v = _parse_number(item)
        if v is None:
            raise ParseError(f"could not parse dataset value {item!r} in {raw.strip()!r}")
        values.append(v)
    return values


def parse(text: str) -> XYChart:
    if not sniff(text):
        raise ParseError('expected "xychart-beta" or "xychart" keyword')

    lines = strip_front_matter(text).split("\n")
    header_idx = next(
        i for i, ln in enumerate(lines) if ln.strip() and not ln.strip().startswith("%%")
    )
    header_parts = lines[header_idx].split()
    chart = XYChart()
    chart.horizontal = any(p.lower() == "horizontal" for p in header_parts[1:])

    saw_categorical_x = False

    for raw in lines[header_idx + 1:]:
        line = raw.split("%%", 1)[0].strip()
        if not line:
            continue
        if m := _TITLE_RE.match(line):
            chart.title = _unquote(m.group("text").strip())
            continue
        if m := _XAXIS_CATS_RE.match(line):
            chart.x_title = m.group("title") or ""
            chart.categories = _split_list(m.group("inner"))
            saw_categorical_x = True
            continue
        if m := _XAXIS_RANGE_RE.match(line):
            # Numeric x-axis (Non-goal). Valid numbers are unsupported input
            # (fall back to the raw fence); malformed numbers are tolerated
            # without raising, matching termaid's own parser (requirement 9).
            lo = _parse_number(m.group("lo"))
            hi = _parse_number(m.group("hi"))
            if lo is not None and hi is not None:
                raise ParseError("numeric x-axis is not supported")
            continue
        if m := _YAXIS_RE.match(line):
            lo = _parse_number(m.group("lo"))
            hi = _parse_number(m.group("hi"))
            if lo is None or hi is None:
                # Malformed range: leave unset so render auto-scales
                # (requirement 9 / termaid's own tolerance).
                continue
            chart.y_title = m.group("title") or ""
            chart.y_min, chart.y_max = (lo, hi) if lo <= hi else (hi, lo)
            continue
        if line.lower().startswith("y-axis"):
            # Title-only / unparseable y-axis: same auto-scale fallback.
            continue
        if m := _DATASET_RE.match(line):
            kind = m.group("kind")
            values = _parse_values(m.group("inner"), raw)
            if kind == "bar":
                if chart.bar is not None:
                    raise ParseError("multiple bar datasets are not supported")
                chart.bar = values
            else:
                if chart.line is not None:
                    raise ParseError("multiple line datasets are not supported")
                chart.line = values
            continue
        raise ParseError(f"could not parse line: {raw.strip()!r}")

    if chart.bar is None and chart.line is None:
        raise ParseError("expected a bar or line dataset")

    if saw_categorical_x:
        n = len(chart.categories)
        for kind, values in (("bar", chart.bar), ("line", chart.line)):
            if values is not None and len(values) != n:
                raise ParseError(
                    f"{kind} dataset has {len(values)} values, expected {n} categories"
                )
    # No categorical x-axis (including a tolerated malformed range line):
    # parse succeeds so the parser unit test can assert "without raising";
    # the renderer then produces a title-only/empty result rather than
    # crashing (requirement 9).

    return chart

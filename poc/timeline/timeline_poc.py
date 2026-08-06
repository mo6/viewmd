#!/usr/bin/env python3
"""Proof of concept for VIEWMD-0035 (Mermaid timeline diagrams).

Not part of the shipped `viewmd` package -- a throwaway script to validate the
issue's box-drawing layout (section/period/event boxes, drop-lines, per-section
coloring, multi-event stacking, and `<br>` handling) against real input before
committing to the design. Run against the bundled examples:

    python3 poc/timeline/timeline_poc.py poc/timeline/industry.mmd
    python3 poc/timeline/timeline_poc.py poc/timeline/england.mmd
    python3 poc/timeline/timeline_poc.py poc/timeline/england.mmd --color always
    python3 poc/timeline/timeline_poc.py poc/timeline/england.mmd --color never
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


@dataclass
class Period:
    section: str | None
    label: str
    events: list[str] = field(default_factory=list)


@dataclass
class Timeline:
    title: str | None
    periods: list[Period] = field(default_factory=list)


class ParseError(Exception):
    pass


def _strip_front_matter(text: str) -> str:
    text = text.lstrip("\n")
    if text.startswith("---\n"):
        end = text.find("\n---", 4)
        if end != -1:
            return text[end + 4 :].lstrip("\n")
    return text


def sniff(text: str) -> bool:
    return _strip_front_matter(text).lstrip().startswith("timeline")


def parse(text: str) -> Timeline:
    body = _strip_front_matter(text)
    lines = [l for l in body.splitlines() if l.strip() and not l.strip().startswith("%%")]
    if not lines or lines[0].strip() != "timeline":
        raise ParseError("expected a line reading 'timeline'")
    lines = lines[1:]

    title = None
    section: str | None = None
    periods: list[Period] = []

    for raw in lines:
        line = raw.strip()
        if line.startswith("title "):
            title = line[len("title ") :].strip()
            continue
        if line.startswith("section "):
            section = line[len("section ") :].strip()
            continue

        if ":" not in line:
            raise ParseError(f"expected 'period : event' or ' : event', got {line!r}")
        label, rest = line.split(":", 1)
        label = label.strip()
        events = [e.strip() for e in rest.split(":")]

        if not label:
            # A bare ` : event` continues the previous period (VIEWMD-0035
            # requirement: multi-event periods repeat the leading colon
            # instead of the period label on follow-up lines).
            if not periods:
                raise ParseError(f"event line before any period declared: {line!r}")
            periods[-1].events.extend(events)
        else:
            periods.append(Period(section=section, label=label, events=list(events)))

    if not periods:
        raise ParseError("empty timeline diagram")
    return Timeline(title=title, periods=periods)


# ---------------------------------------------------------------------------
# Color -- per-SECTION categorical fill (unlike VIEWMD-0034 kanban's
# per-column fill), values from Anthropic's `dataviz` skill's validated
# default palette (references/palette.md), dark-surface column.
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

HEADER_TEXT_HEX = "ffffff"


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


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------

WRAP_WIDTH = 20
GAP = 1


def _visible_len(s: str) -> int:
    return len(re.sub(r"\x1b\[[0-9;]*m", "", s))


def _center_visible(s: str, width: int) -> str:
    pad = max(0, width - _visible_len(s))
    left = pad // 2
    right = pad - left
    return " " * left + s + " " * right


def _wrap_event(event: str, width: int) -> list[str]:
    lines: list[str] = []
    for seg in event.split("<br>"):
        seg = seg.strip()
        lines.extend(textwrap.wrap(seg, width) or [""])
    return lines


@dataclass
class Column:
    section: str | None
    label: str
    events: list[list[str]]  # one wrapped-line-list per stacked event
    width: int  # interior content width, excludes the box's own borders


def _build_columns(periods: list[Period]) -> list[Column]:
    columns = []
    for p in periods:
        events = [_wrap_event(e, WRAP_WIDTH) for e in p.events]
        width = len(p.label)
        for lines in events:
            width = max(width, max((len(l) for l in lines), default=0))
        columns.append(Column(section=p.section, label=p.label, events=events, width=width + 2))
    return columns


def _group_sections(columns: list[Column]) -> list[tuple[str | None, list[Column]]]:
    groups: list[tuple[str | None, list[Column]]] = []
    for c in columns:
        if not groups or groups[-1][0] != c.section:
            groups.append((c.section, []))
        groups[-1][1].append(c)
    return groups


def _box_row(cols: list[Column], groups: list[tuple[str | None, list[Column]]], border: str) -> tuple[str, str, str]:
    top = mid = bot = ""
    for gi, (_, gcols) in enumerate(groups):
        for c in gcols:
            top += "┌" + "─" * c.width + "┐"
            bot += "└" + border * c.width + "┘"
        if gi != len(groups) - 1:
            top += " " * GAP
            bot += " " * GAP
    return top, mid, bot


def render(timeline: Timeline, c: Colorizer) -> str:
    columns = _build_columns(timeline.periods)
    groups = _group_sections(columns)
    has_sections = any(name is not None for name, _ in groups)
    section_hex = {
        name: CATEGORICAL[i % len(CATEGORICAL)][1]
        for i, (name, _) in enumerate(groups)
        if name is not None
    }

    out: list[str] = []
    if timeline.title:
        total_w = sum(col.width + 2 for col in columns) + GAP * (len(groups) - 1)
        out.append(timeline.title.center(total_w))
        out.append("")

    # section header boxes, one per section, spanning its periods' combined width
    if has_sections:
        top = mid = bot = ""
        for gi, (name, gcols) in enumerate(groups):
            inner = sum(gc.width + 2 for gc in gcols) - 2
            hex_ = section_hex.get(name, "666666")
            top += "┌" + "─" * inner + "┐"
            header = c.fg(name or "", HEADER_TEXT_HEX)
            mid += "│" + c.bg(_center_visible(header, inner), hex_) + "│"
            bot += "└" + "━" * inner + "┘"
            if gi != len(groups) - 1:
                top += " " * GAP
                mid += " " * GAP
                bot += " " * GAP
        out += [top, mid, bot, ""]

    # period boxes
    top = mid = bot = ""
    for gi, (name, gcols) in enumerate(groups):
        hex_ = section_hex.get(name)
        for col in gcols:
            top += "┌" + "─" * col.width + "┐"
            label = c.fg(col.label, HEADER_TEXT_HEX) if hex_ else col.label
            cell = c.bg(_center_visible(label, col.width), hex_) if hex_ else col.label.center(col.width)
            mid += "│" + cell + "│"
            bot += "└" + "━" * col.width + "┘"
        if gi != len(groups) - 1:
            top += " " * GAP
            mid += " " * GAP
            bot += " " * GAP
    out += [top, mid, bot]

    # drop-line centers (x position of each column's midpoint)
    centers = []
    x = 0
    for gi, (_, gcols) in enumerate(groups):
        for col in gcols:
            centers.append(x + 1 + col.width // 2)
            x += col.width + 2
        if gi != len(groups) - 1:
            x += GAP
    total_w = x

    def dropline() -> str:
        row = [" "] * total_w
        for cx in centers:
            if cx < total_w:
                row[cx] = "┊"
        return "".join(row).rstrip()

    out += [dropline(), dropline()]

    axis = list("─" * total_w)
    for cx in centers:
        axis[cx] = "┼"
    out.append("".join(axis) + "▶")

    out += [dropline(), dropline()]

    max_depth = max(len(col.events) for col in columns)
    for depth in range(max_depth):
        heights = [len(col.events[depth]) for col in columns if depth < len(col.events)]
        maxh = max(heights, default=1)

        top = ""
        bot = ""
        mids = [""] * maxh
        for gi, (name, gcols) in enumerate(groups):
            hex_ = section_hex.get(name)
            for col in gcols:
                if depth < len(col.events):
                    lines = col.events[depth]
                    top += "┌" + "─" * col.width + "┐"
                    for r in range(maxh):
                        text = lines[r] if r < len(lines) else ""
                        cell = c.bg(_center_visible(text, col.width), hex_) if hex_ else text.center(col.width)
                        mids[r] += "│" + cell + "│"
                    bot += "└" + "━" * col.width + "┘"
                else:
                    top += " " * (col.width + 2)
                    for r in range(maxh):
                        mids[r] += " " * (col.width + 2)
                    bot += " " * (col.width + 2)
            if gi != len(groups) - 1:
                top += " " * GAP
                for r in range(maxh):
                    mids[r] += " " * GAP
                bot += " " * GAP
        out.append(top)
        out.extend(mids)
        out.append(bot)
        if depth != max_depth - 1:
            out.append(dropline())

    out.append(dropline())
    tail = [" "] * total_w
    for cx in centers:
        tail[cx] = "▼"
    out.append("".join(tail).rstrip())

    return "\n".join(out)


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
    parser.add_argument("path", nargs="?", default=os.path.join(os.path.dirname(__file__), "industry.mmd"))
    parser.add_argument("--color", choices=["auto", "always", "never"], default="auto")
    args = parser.parse_args()

    with open(args.path, encoding="utf-8") as f:
        text = f.read()

    if not sniff(text):
        print("not a timeline fence", file=sys.stderr)
        raise SystemExit(1)

    timeline = parse(text)
    c = Colorizer(_resolve_color(args.color))
    print(render(timeline, c))


if __name__ == "__main__":
    main()

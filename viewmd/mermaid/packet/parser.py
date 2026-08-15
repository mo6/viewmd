"""Packet diagram parser (VIEWMD-0049).

No upstream reference implementation to port from (mermaid-ascii has no
packet-diagram support), so this is hand-written directly against Mermaid's
own syntax (https://mermaid.js.org/syntax/packet.html) and, for the exact
field-validation semantics, its actual parser source
(packages/mermaid/src/diagrams/packet/parser.ts's `populate()`), not a port.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from viewmd.mermaid.textutil import strip_front_matter

PACKET_DIAGRAM_KEYWORDS = ("packet-beta", "packet")

# A field line is either `<start>-<end>: "<label>"`, the single-bit shorthand
# `<start>: "<label>"`, or the cursor-relative `+<count>: "<label>"` -- three
# alternatives, matching packet.langium's `PacketBlock` grammar rule.
_FIELD_RE = re.compile(
    r'^(?:(?P<start>\d+)(?:-(?P<end>\d+))?|\+(?P<bits>\d+))\s*:\s*"(?P<label>[^"]*)"\s*$'
)


class ParseError(Exception):
    pass


@dataclass
class Field:
    start: int
    end: int
    label: str


@dataclass
class PacketDiagram:
    title: str = ""
    fields: list[Field] = field(default_factory=list)


def sniff(text: str) -> bool:
    """Whether `text`'s first meaningful line (after an optional YAML
    front-matter block) is exactly the `packet-beta` or `packet` keyword
    (case-insensitive) -- unlike `pie`, the packet grammar doesn't allow
    trailing tokens on the keyword's own line."""
    for line in strip_front_matter(text).split("\n"):
        t = line.strip()
        if t == "" or t.startswith("%%"):
            continue
        return t.lower() in PACKET_DIAGRAM_KEYWORDS
    return False


def parse(text: str) -> PacketDiagram:
    if not sniff(text):
        raise ParseError('expected "packet-beta" or "packet" keyword')

    lines = strip_front_matter(text).split("\n")
    header_idx = next(
        i for i, ln in enumerate(lines) if ln.strip() and not ln.strip().startswith("%%")
    )

    diagram = PacketDiagram()
    last_bit = -1
    for raw in lines[header_idx + 1:]:
        line = raw.split("%%", 1)[0].strip()
        if not line:
            continue
        if line.startswith("title "):
            diagram.title = line[len("title "):].strip()
            continue
        m = _FIELD_RE.match(line)
        if not m:
            raise ParseError(f"could not parse field line: {raw.strip()!r}")

        if m.group("bits") is not None:
            bits = int(m.group("bits"))
            if bits <= 0:
                raise ParseError(f"cannot have a zero-bit field: {raw.strip()!r}")
            start = last_bit + 1
            end = start + bits - 1
        else:
            start = int(m.group("start"))
            end = int(m.group("end")) if m.group("end") is not None else start
            if end < start:
                raise ParseError(
                    f"field {start}-{end} is invalid: end must be greater than or equal "
                    f"to start: {raw.strip()!r}"
                )
            if start != last_bit + 1:
                raise ParseError(
                    f"field {start}-{end} is not contiguous, it should start from "
                    f"{last_bit + 1}: {raw.strip()!r}"
                )

        diagram.fields.append(Field(start=start, end=end, label=m.group("label")))
        last_bit = end

    return diagram

"""Text preprocessing shared across Mermaid diagram parsers, ported from
pkg/diagram/utils.go."""

from __future__ import annotations

import re

from wcwidth import wcswidth

_NEWLINE_RE = re.compile(r"\n|\\n")


def width(s: str) -> int:
    """Display width of `s`, matching the Go port's `go-runewidth` usage."""
    w = wcswidth(s)
    return w if w >= 0 else len(s)


def split_lines(text: str) -> list[str]:
    """Split on real or escaped (``\\n``, for curl compatibility) newlines."""
    return _NEWLINE_RE.split(text)


def wrap_words(text: str, max_width: int) -> list[str]:
    """Greedy word-wrap `text` to display-width `max_width` (VIEWMD-0034), for
    a card label inside a fixed-width box. A single word wider than
    `max_width` on its own still overflows that one line rather than being
    split mid-word -- kanban card labels are prose, not data that benefits
    from a hard break."""
    words = text.split()
    if not words:
        return [""]
    lines: list[str] = []
    current = words[0]
    for word in words[1:]:
        candidate = f"{current} {word}"
        if width(candidate) <= max_width:
            current = candidate
        else:
            lines.append(current)
            current = word
    lines.append(current)
    return lines


def strip_front_matter(text: str) -> str:
    """Skips a leading YAML front-matter block (`---\\n...\\n---`), the
    mechanism Mermaid's own `title`/`config` overrides use. Its contents are
    parsed away/ignored, not interpreted, but its mere presence must not
    prevent the diagram keyword after it from being recognized."""
    lines = text.split("\n")
    if lines and lines[0].strip() == "---":
        for i in range(1, len(lines)):
            if lines[i].strip() == "---":
                return "\n".join(lines[i + 1:])
    return text


def remove_comments(lines: list[str]) -> list[str]:
    """Drop Mermaid ``%%`` comments: full-line comments are removed outright,
    inline ``%%`` truncates the rest of the line. Lines left empty afterward are
    dropped too."""
    cleaned: list[str] = []
    for line in lines:
        if line.strip().startswith("%%"):
            continue
        idx = line.find("%%")
        if idx != -1:
            line = line[:idx].strip()
        if line.strip():
            cleaned.append(line)
    return cleaned

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

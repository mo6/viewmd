"""Splice rendered Mermaid diagrams into a Markdown body as plain code fences.

Rich has no public extension point for custom fenced-code-block rendering (the
same constraint noted in wikilinks.py), so this runs as a text-level
preprocessing pass before the body reaches `rich.markdown.Markdown`: it finds
` ```mermaid ` fences, renders their contents to box-drawing ASCII/Unicode art,
and replaces the fence's info string so Rich treats the result as preformatted
text rather than trying to syntax-highlight it as an unrecognized language.

A fence that isn't a supported diagram type, or fails to parse, is left
untouched -- the reader sees the original Mermaid source instead of a crash.
"""

from __future__ import annotations

import re

from viewmd.mermaid import MermaidError, render

_FENCE_RE = re.compile(r"^(\s*)(`{3,}|~{3,})(.*)$")


def render_mermaid_blocks(text: str) -> str:
    lines = text.split("\n")
    out: list[str] = []
    i = 0
    n = len(lines)
    while i < n:
        match = _FENCE_RE.match(lines[i])
        if match and match.group(3).strip().lower() == "mermaid":
            indent, fence, _ = match.groups()
            body, end = _find_closing_fence(lines, i + 1, fence[0])
            if end is not None:
                rendered = _try_render("\n".join(body))
                if rendered is not None:
                    out.append(f"{indent}{fence}")
                    out.extend(rendered.rstrip("\n").split("\n"))
                    out.append(f"{indent}{fence}")
                    i = end + 1
                    continue
        out.append(lines[i])
        i += 1
    return "\n".join(out)


def _find_closing_fence(
    lines: list[str], start: int, fence_char: str
) -> tuple[list[str], int | None]:
    """Body lines and the index of the closing fence starting from `start`, or
    (body-so-far, None) if the fence is never closed."""
    body: list[str] = []
    for j in range(start, len(lines)):
        close = _FENCE_RE.match(lines[j])
        if close and close.group(2)[0] == fence_char and not close.group(3).strip():
            return body, j
        body.append(lines[j])
    return body, None


def _try_render(mermaid_source: str) -> str | None:
    try:
        return render(mermaid_source)
    except MermaidError:
        return None

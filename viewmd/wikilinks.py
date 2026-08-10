"""Rewrite Obsidian-style [[wikilinks]] into ordinary Markdown links (VIEWMD-0006).

Rich has no public extension point for custom inline rules, so this runs as a text-level
preprocessing pass before the body reaches ``rich.markdown.Markdown``. Rewriting to
``[Display](<wikilink:Target>)`` reuses Rich's existing ``markdown.link_url`` styling; the
``wikilink:`` scheme is inert (never opened) and exists only so the text is a valid Markdown
link. The destination is wrapped in ``<...>`` (with backslash/``<``/``>`` escaped) because
CommonMark only allows spaces in a link destination inside that bracketed form -- a bare
``(wikilink:Target With Spaces)`` is invalid and Rich falls back to printing the raw markdown.
"""

from __future__ import annotations

import re

_WIKILINK_RE = re.compile(r"\[\[([^\]|]+)(?:\|([^\]]+))?\]\]")
_FENCE_RE = re.compile(r"^(```|~~~)")


def rewrite_wikilinks(text: str) -> str:
    """Rewrite ``[[Target]]`` / ``[[Target|Display]]`` outside of code into Markdown links.

    Fenced code blocks (any line whose content, ignoring leading indentation, starts with
    `` ``` `` or ``~~~`` toggles fence state -- so a fence indented under a list item or
    blockquote is still recognized) and single-backtick inline code spans are left untouched.
    """
    lines = text.split("\n")
    out: list[str] = []
    in_fence = False
    for line in lines:
        if _FENCE_RE.match(line.lstrip()):
            in_fence = not in_fence
            out.append(line)
            continue
        if in_fence:
            out.append(line)
            continue
        out.append(_rewrite_line(line))
    return "\n".join(out)


def _rewrite_line(line: str) -> str:
    """Rewrite wikilinks on one non-fenced line, skipping single-backtick inline code."""
    result: list[str] = []
    i = 0
    n = len(line)
    while i < n:
        if line[i] == "`":
            close = line.find("`", i + 1)
            if close == -1:
                result.append(line[i:])
                break
            result.append(line[i : close + 1])
            i = close + 1
            continue
        if line.startswith("[[", i):
            match = _WIKILINK_RE.match(line, i)
            if match:
                target = match.group(1)
                display = match.group(2) if match.group(2) is not None else target
                dest = f"wikilink:{target}".replace("\\", "\\\\").replace("<", "\\<").replace(">", "\\>")
                result.append(f"[{display}](<{dest}>)")
                i = match.end()
                continue
        result.append(line[i])
        i += 1
    return "".join(result)

"""Strip `viewmd:mark` sentinel HTML comments from Markdown source, recording the marked
region(s) they delimit (VIEWMD-0104).

A pair of sentinel comments -- `<!-- viewmd:mark start kind=KIND -->` ... `<!-- viewmd:mark end
-->`, each alone on its own line between blocks -- brackets a *marked region*: one or more block
elements a caller (e.g. gitgleam) wants viewmd to tint with a colored background when rendering
with color. This module only locates and removes those sentinel lines from the raw Markdown text,
the same "rewrite text before rich.markdown.Markdown ever parses it" stage wikilinks.py and
mermaid/preprocess.py already run at -- stripping the *line* here (not suppressing an unknown
block element after Rich has already parsed one) is what keeps the surrounding blank-line spacing
identical to the sentinel simply having been deleted from the source (requirement 8). Turning the
recorded line ranges into an actual rendered background tint is render.py's job, once the
stripped text has been parsed into markdown-it tokens with source-line maps of their own.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

# Flexible inner whitespace: `<!--viewmd:mark start-->` and `<!--  viewmd:mark  start  kind=added
# -->` must both match (requirement 2). The whole (stripped) line must be exactly one sentinel --
# no other content sharing the line.
_MARK_LINE_RE = re.compile(
    r"^<!--\s*viewmd:mark\s+(start|end)(?:\s+kind\s*=\s*([A-Za-z]+))?\s*-->$"
)
# Looser net for requirement 10's "any viewmd:mark comment that cannot be parsed" -- a single-line
# HTML comment that clearly *attempts* the sentinel syntax (a typo'd action, an unexpected extra
# token) but doesn't match `_MARK_LINE_RE` exactly. Anything this loose pattern also fails to
# match (an ordinary comment that merely mentions "viewmd:mark" in prose, spread across multiple
# lines, etc.) is left to `rich.markdown.Markdown`'s existing generic HTML-comment handling,
# matching requirement 9's "other <!-- ... --> keep their current handling".
_MARK_ATTEMPT_RE = re.compile(r"^<!--.*viewmd:mark.*-->$")

# Same fence-tracking convention `wikilinks.py` already uses (`_FENCE_RE`/`_BLOCKQUOTE_PREFIX_RE`
# there) -- a sentinel-*looking* line inside a fenced code block (e.g. a docs page showing the
# marker syntax as a literal example) is real code-block content, not a directive, and must not be
# stripped or warned about, the same way `rewrite_wikilinks` leaves `[[bracket]]`-looking text
# inside a fence untouched.
_FENCE_RE = re.compile(r"^(```|~~~)")
_BLOCKQUOTE_PREFIX_RE = re.compile(r"^(?:\s*>)*\s*")

VALID_KINDS = ("added", "changed", "removed")
DEFAULT_KIND = "changed"


@dataclass(frozen=True)
class MarkRegion:
    """One marked region, as 0-indexed inclusive line numbers in the *stripped* text this
    module returns -- i.e. the same line numbering markdown-it will assign to the body it parses
    next, since sentinel-stripping is the last text-level rewrite before that parse."""

    kind: str
    start_line: int
    end_line: int


def strip_marks(text: str) -> tuple[str, list[MarkRegion], list[str]]:
    """Remove every `viewmd:mark` sentinel line from `text`, returning `(stripped_text, regions,
    warnings)`.

    A missing/unrecognized `kind` defaults to `DEFAULT_KIND` (requirement 2). An unbalanced start
    (no matching end) closes at the end of the document; a stray end (no open start) is ignored;
    a `start` nested inside an already-open region is ignored (regions are flat -- Non-goals); a
    single-line comment that attempts the sentinel syntax but doesn't parse (a typo'd action, an
    unexpected token) is stripped and ignored the same way, rather than surviving into Rich's
    parser as an unrecognized HTML block and silently reproducing the exact blank-line-doubling
    bug requirement 8 exists to fix. Each such case appends one message to `warnings` for the
    caller to print to stderr, per requirement 10 -- none of them raise. A sentinel-looking line
    inside a fenced code block is left completely alone (not stripped, no warning): it's code
    content, not a directive.
    """
    lines = text.split("\n")
    out_lines: list[str] = []
    regions: list[MarkRegion] = []
    warnings: list[str] = []
    open_kind: str | None = None
    open_start_line = 0
    in_fence = False

    for line in lines:
        if _FENCE_RE.match(_BLOCKQUOTE_PREFIX_RE.sub("", line, count=1)):
            in_fence = not in_fence
            out_lines.append(line)
            continue
        if in_fence:
            out_lines.append(line)
            continue

        stripped_line = line.strip()
        match = _MARK_LINE_RE.match(stripped_line)
        if match is None:
            if _MARK_ATTEMPT_RE.match(stripped_line):
                warnings.append(f"malformed viewmd:mark comment ignored: {stripped_line!r}")
                continue
            out_lines.append(line)
            continue

        action, kind_raw = match.groups()
        if action == "start":
            if open_kind is not None:
                warnings.append(
                    "nested viewmd:mark start ignored (regions may not overlap)"
                )
                continue
            kind = (
                kind_raw.lower() if kind_raw and kind_raw.lower() in VALID_KINDS else DEFAULT_KIND
            )
            open_kind = kind
            open_start_line = len(out_lines)
        else:
            if open_kind is None:
                warnings.append("viewmd:mark end with no open start ignored")
                continue
            end_line = len(out_lines) - 1
            if end_line >= open_start_line:
                regions.append(MarkRegion(open_kind, open_start_line, end_line))
            open_kind = None
        # The sentinel line itself is never appended -- this is the "delete the line" step
        # requirement 8 requires (as opposed to leaving it for Rich to render-and-suppress).

    if open_kind is not None:
        end_line = len(out_lines) - 1
        if end_line >= open_start_line:
            regions.append(MarkRegion(open_kind, open_start_line, end_line))
        warnings.append(
            "unbalanced viewmd:mark start (no matching end); region extended to end of document"
        )

    return "\n".join(out_lines), regions, warnings

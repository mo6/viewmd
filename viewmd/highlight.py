"""Strip standalone HTML comments from Markdown source -- `viewmd:mark` sentinels specially
(recording the marked region(s) they delimit, VIEWMD-0104), any other comment generically
(VIEWMD-0107).

A pair of sentinel comments -- `<!-- viewmd:mark start kind=KIND -->` ... `<!-- viewmd:mark end
-->`, each alone on its own line between blocks -- brackets a *marked region*: one or more block
elements a caller (e.g. gitgleam) wants viewmd to tint with a colored background when rendering
with color. This module locates and removes those sentinel lines from the raw Markdown text, the
same "rewrite text before rich.markdown.Markdown ever parses it" stage wikilinks.py and
mermaid/preprocess.py already run at -- stripping the *line* here (not suppressing an unknown
block element after Rich has already parsed one) is what keeps the surrounding blank-line spacing
identical to the sentinel simply having been deleted from the source (requirement 8). Turning the
recorded line ranges into an actual rendered background tint is render.py's job, once the
stripped text has been parsed into markdown-it tokens with source-line maps of their own.

VIEWMD-0107 widens the same stripping to *any* standalone HTML comment, not just `viewmd:mark`
ones: `rich.markdown.Markdown` has no built-in handling for an HTML comment block, so it always
hit the same "unknown block element -> blank line doubled on both sides" bug VIEWMD-0104
diagnosed and fixed only for marks -- there's no reason an author's own ordinary editorial
comment, left alone on its own line the same way a mark sentinel is, should keep suffering it. An
inline HTML comment embedded in running text (`text <!-- x --> more text`) is untouched: Rich
handles `html_inline` tokens on a completely different code path from `html_block` ones, and the
doubling bug is specific to the latter (requirement 3).
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
# Looser net for VIEWMD-0104 requirement 10's "any viewmd:mark comment that cannot be parsed" -- a
# single-line HTML comment that clearly *attempts* the sentinel syntax (a typo'd action, an
# unexpected extra token) but doesn't match `_MARK_LINE_RE` exactly, which gets its own warning
# below. Anything this loose pattern also fails to match (an ordinary comment that merely mentions
# "viewmd:mark" in prose, a multi-line one, etc.) still gets stripped -- just silently, by the
# generic standalone-comment branch further down (VIEWMD-0107), with no warning and no special
# "attempted sentinel" treatment, since it's ordinary content, not a malformed directive.
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
    """Remove every standalone HTML comment from `text` -- `viewmd:mark` sentinels specially,
    tracking the regions they delimit, any other comment generically (VIEWMD-0107) -- returning
    `(stripped_text, regions, warnings)`.

    A missing/unrecognized `kind` defaults to `DEFAULT_KIND` (requirement 2). An unbalanced start
    (no matching end) closes at the end of the document; a stray end (no open start) is ignored;
    a `start` nested inside an already-open region is ignored (regions are flat -- Non-goals); a
    single-line comment that attempts the sentinel syntax but doesn't parse (a typo'd action, an
    unexpected token) is stripped and ignored the same way, rather than surviving into Rich's
    parser as an unrecognized HTML block and silently reproducing the exact blank-line-doubling
    bug requirement 8 exists to fix. Each such case appends one message to `warnings` for the
    caller to print to stderr, per requirement 10 -- none of them raise. Any other standalone
    comment (single-line, or spanning several lines up through the first one containing `-->`,
    per CommonMark's own HTML-comment block rule) is stripped silently, no warning -- it's
    ordinary content, not a malformed directive. A comment-looking line inside a fenced code
    block is left completely alone (not stripped, no warning): it's code content, not a
    directive.
    """
    lines = text.split("\n")
    out_lines: list[str] = []
    regions: list[MarkRegion] = []
    warnings: list[str] = []
    open_kind: str | None = None
    open_start_line = 0
    in_fence = False

    i = 0
    n = len(lines)
    while i < n:
        line = lines[i]
        if _FENCE_RE.match(_BLOCKQUOTE_PREFIX_RE.sub("", line, count=1)):
            in_fence = not in_fence
            out_lines.append(line)
            i += 1
            continue
        if in_fence:
            out_lines.append(line)
            i += 1
            continue

        stripped_line = line.strip()
        match = _MARK_LINE_RE.match(stripped_line)
        if match is not None:
            action, kind_raw = match.groups()
            if action == "start":
                if open_kind is not None:
                    warnings.append(
                        "nested viewmd:mark start ignored (regions may not overlap)"
                    )
                    i += 1
                    continue
                kind = (
                    kind_raw.lower()
                    if kind_raw and kind_raw.lower() in VALID_KINDS
                    else DEFAULT_KIND
                )
                open_kind = kind
                open_start_line = len(out_lines)
            else:
                if open_kind is None:
                    warnings.append("viewmd:mark end with no open start ignored")
                    i += 1
                    continue
                end_line = len(out_lines) - 1
                if end_line >= open_start_line:
                    regions.append(MarkRegion(open_kind, open_start_line, end_line))
                open_kind = None
            # The sentinel line itself is never appended -- this is the "delete the line" step
            # requirement 8 requires (as opposed to leaving it for Rich to render-and-suppress).
            i += 1
            continue

        if _MARK_ATTEMPT_RE.match(stripped_line):
            warnings.append(f"malformed viewmd:mark comment ignored: {stripped_line!r}")
            i += 1
            continue

        if stripped_line.startswith("<!--"):
            # Any other standalone HTML comment (VIEWMD-0107) -- strip the whole comment block,
            # single-line or (per CommonMark's own HTML-comment rule) spanning several lines up
            # through the first one containing "-->", the same "delete it from the source" way a
            # mark sentinel is stripped, so it renders with no doubled blank line either.
            if "-->" in stripped_line:
                i += 1
                continue
            j = i + 1
            while j < n and "-->" not in lines[j]:
                j += 1
            if j >= n:
                # Unterminated -- per CommonMark's own HTML-comment block rule this swallows the
                # rest of the document either way (markdown-it itself would parse it as one
                # html_block running to EOF); warn instead of silently dropping everything after
                # it with no trace, the same courtesy an unbalanced viewmd:mark start already gets
                # below.
                warnings.append("unterminated HTML comment; rest of document dropped")
                break
            i = j + 1
            continue

        out_lines.append(line)
        i += 1

    if open_kind is not None:
        end_line = len(out_lines) - 1
        if end_line >= open_start_line:
            regions.append(MarkRegion(open_kind, open_start_line, end_line))
        warnings.append(
            "unbalanced viewmd:mark start (no matching end); region extended to end of document"
        )

    return "\n".join(out_lines), regions, warnings

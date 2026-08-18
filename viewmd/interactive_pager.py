"""viewmd's own interactive terminal pager (VIEWMD-0007, extended to every paged case by
VIEWMD-0072), replacing external `less`/`$PAGER` delegation entirely: raw terminal input,
line-based scroll with mouse-wheel support, a two-line Info-style mode-line/echo-area status
split, a table-of-contents popup (when there's a heading outline to build one from), forward
search with match highlighting, horizontal scroll for content wider than the terminal, a
render-width toggle, a mouse-capture toggle, direct terminal-resize handling, and a `?` help
screen.

Three public entry points share one scrolling engine (`_run()`): `run()` for a single Markdown
document (VIEWMD-0007), `run_directory_listing()` for a bare directory listing (VIEWMD-0065's
table-of-contents view, VIEWMD-0072), and `run_multi_file()` for a multi-file concatenation
(VIEWMD-0013, VIEWMD-0072) -- the latter two have no heading outline to build a ToC popup from,
so that feature is simply inert for them (see `_run`'s docstring). Ported from
`poc/pager/pager_poc.py`, the proof-of-concept built to de-risk this architecture shape before it
was scoped for real building -- see VIEWMD-0007's Design notes for the full rationale.
`viewmd/pager.py` decides when to reach for which entry point here versus a plain print; this
module doesn't make that decision itself.
"""

from __future__ import annotations

import os
import re
import select
import shutil
import signal
import sys
import termios
import tty
import urllib.parse
from dataclasses import dataclass

from wcwidth import wcswidth

from viewmd.render import ViewmdMarkdown, heading_outline, render_markdown

# SGR color codes ("\x1b[...m") and OSC 8 hyperlink wrappers ("\x1b]8;id=..;url\x1b\\", closed by
# a matching "\x1b]8;;\x1b\\") -- Rich emits both for a colored render (VIEWMD-0006 turns
# [[wikilinks]] into real links, so an ordinary document with any is full of them). Anything else
# (cursor moves, erase-line) is deliberately NOT matched here -- see `_overlay`'s docstring for
# why stripping-then-reslicing colored text is unsafe in general and avoided for popup rows.
_ANSI_RE = re.compile(r"\x1b\[[0-9;]*m|\x1b\]8;[^\x1b]*\x1b\\")

# Terminal setup/teardown sequences. 1049 = alternate screen buffer (so quitting restores
# whatever was on screen before, like `less` does); 25 = cursor visibility; 1000+1006 = xterm
# mouse reporting with SGR (extended, non-ambiguous) coordinate encoding, which also carries
# wheel-scroll events as synthetic "buttons" 64/65 (vertical) and 66/67 (horizontal tilt/swipe,
# VIEWMD-0075) -- this is the same mechanism VIEWMD-0067 leaned on via `less --mouse`, now handled
# here directly instead of by an external pager.
#
# Enabling mouse reporting at all is also what stops a plain click-drag from doing the terminal's
# own native text selection -- once the app is receiving mouse events, most terminals route every
# button press/drag to it instead, not just wheel scroll. The 'm' key (see `run`) toggles
# `_MOUSE_ON`/`_MOUSE_OFF` independently of the alternate screen so text can still be selected
# without quitting the pager; most terminals also let a modifier key (Option on macOS, Shift on
# Linux/Windows terminals) bypass app mouse capture for a single drag without toggling anything.
_MOUSE_ON = "\x1b[?1000h\x1b[?1006h"
_MOUSE_OFF = "\x1b[?1000l\x1b[?1006l"
_ENTER_SCREEN = "\x1b[?1049h\x1b[?25l" + _MOUSE_ON
_EXIT_SCREEN = _MOUSE_OFF + "\x1b[?25h\x1b[?1049l"
_HOME = "\x1b[H"
_CLEAR_EOL = "\x1b[K"

# Popup box coloring: a dark blue interior background with near-white text, so the box reads as
# a distinct panel rather than plain text with a border; the selected row gets a brighter,
# bolded background on top of that so the selection is legible even where the box's own bg
# already lifts it off the surrounding document.
_POPUP_BG = "\x1b[48;5;24;38;5;231m"
_POPUP_SELECTED_BG = "\x1b[48;5;33;1m"
# Mode line: an explicit teal background rather than reverse video or plain grey -- reverse video
# swaps to the *terminal's own* current fg/bg (a plain-white bar on a light-on-dark theme, the
# common case), and flat grey reads as merely dimmed rather than an intentional accent; a genuine
# hue looks the same everywhere and reads as a deliberate status-bar color, not a dimmed one.
_MODE_LINE_BG = "\x1b[48;5;30;38;5;231m"
# Keycap style for the echo area's keybinding summary: a chip with a saturated background and
# bold black text, standing in for a "[key]" bracket notation. Must be a real hue, not a dark
# grey -- 256-color grey shades (e.g. 236) sit almost exactly on top of the near-black background
# most dark terminal themes already use by default, which is invisible rather than "a colored
# chip" (the same mistake an earlier grey mode-line background made).
_KEYCAP_BG = "\x1b[48;5;178;38;5;16;1m"
# Search-match highlight: classic find-in-page yellow, bold black text.
_SEARCH_HIGHLIGHT_BG = "\x1b[48;5;226;38;5;16;1m"
_RESET = "\x1b[0m"


def _keycap(key: str) -> str:
    return f"{_KEYCAP_BG}{key}{_RESET}"


def _highlight_matches(plain_line: str, query: str) -> str | None:
    """`plain_line` with every case-insensitive occurrence of `query` wrapped in
    `_SEARCH_HIGHLIGHT_BG`, or `None` if `query` doesn't appear in it at all -- callers use that
    to leave a non-matching row exactly as it was (its real syntax color included) rather than
    rebuilding every visible row from its plain twin just to highlight the few that match.

    Built from `plain_line`, not a colored line, for the same reason `_overlay` rebuilds from the
    plain twin instead of splicing into colored text directly: a highlight span opened partway
    through an existing color span (a heading, a hyperlink) would either leak past it or lose its
    own styling with nothing left to restore. Every returned span is self-contained (opens, then
    always closes with `_RESET` before the next literal character), so this is always safe to
    drop into a row wholesale -- see that same docstring for what "safe" is protecting against.
    """
    if not query:
        return None
    q = query.lower()
    lower = plain_line.lower()
    if q not in lower:
        return None
    out: list[str] = []
    i = 0
    n = len(query)
    while True:
        j = lower.find(q, i)
        if j == -1:
            out.append(plain_line[i:])
            break
        out.append(plain_line[i:j])
        out.append(f"{_SEARCH_HIGHLIGHT_BG}{plain_line[j : j + n]}{_RESET}")
        i = j + n
    return "".join(out)


@dataclass
class HeadingLoc:
    text: str
    level: int
    row: int  # index into `lines` where this heading's rendered text lives


def _strip_ansi(s: str) -> str:
    return _ANSI_RE.sub("", s)


def _display_width(s: str) -> int:
    """Terminal column count via `wcwidth.wcswidth` -- matches `viewmd.render`'s own
    `_display_width` convention, never `len()` (VIEWMD-0070). A negative `wcswidth` result
    (control/unprintable characters) falls back to `len(s)`, the same fallback `render.py` uses."""
    width = wcswidth(s)
    return width if width >= 0 else len(s)


def _char_width(ch: str) -> int:
    """Column width of a single character -- `wcswidth` handles a length-1 string the same as
    `wcwidth` would, so this reuses `_display_width`'s import rather than a second one. Used by
    `_ansi_slice`'s column walk, which needs a running per-character width, not a whole-string
    total."""
    w = wcswidth(ch)
    return w if w >= 0 else 1


def _wc_ljust(s: str, width: int, fillchar: str = " ") -> str:
    """`str.ljust`, but padding to `width` *display columns* (`_display_width`), not `width`
    characters -- needed anywhere padded content can come from arbitrary document text (a ToC
    entry is a heading, which can contain a wide character) rather than this module's own
    hardcoded ASCII labels, where plain `str.ljust` already agrees with column count."""
    pad = max(0, width - _display_width(s))
    return s + fillchar * pad


def _locate_headings(lines: list[str], outline) -> list[HeadingLoc]:
    """Map each VIEWMD-0062 `HeadingOutline` entry to the rendered row it lands on, by scanning
    for the first not-yet-claimed line whose stripped text matches. Headings render on their own
    line and don't repeat, so first-match-in-order is exact for any real document."""
    locs: list[HeadingLoc] = []
    search_from = 0
    for h in outline:
        for i in range(search_from, len(lines)):
            if _strip_ansi(lines[i]).strip() == h.text.strip():
                locs.append(HeadingLoc(text=h.text, level=h.level, row=i))
                search_from = i + 1
                break
    return locs


def _load(
    text: str, width: int, *, color_kwargs: dict
) -> tuple[list[str], list[str], list[HeadingLoc]]:
    """Returns (colored lines, plain lines, headings). The two renders agree line-for-line for
    ordinary content -- Rich's own color on/off never changes its wrapping decisions, only which
    escape codes ride along with the same text -- so `plain_lines[i]` is usually `colored_lines[i]`
    with every SGR/OSC8 sequence removed, character-position-for-character-position. `_overlay`
    leans on that to composite the popup onto the plain twin of a row instead of slicing through
    live color state (see its docstring).

    That agreement is NOT guaranteed for a Mermaid diagram, though: `render_markdown` threads
    `color` into its own preprocessing pass (VIEWMD-0043), and a diagram renderer is free to size
    or lay itself out differently depending on it -- the kanban renderer's per-column background
    fill is a real example where the color=True and color=False renders of the same source row end
    up genuinely different widths. Code that needs "how wide is this specific row" (`_crop_row`'s
    truncation-marker decision, notably) has to measure the row it's actually about to display,
    not assume `plain_lines[i]`'s length describes it.

    `color_kwargs` carries `full_front_matter`/`toc` through to both renders unchanged, so the
    interactive view matches exactly what `--no-pager`/a piped invocation would have shown."""
    colored_raw = render_markdown(text, width=width, color=True, **color_kwargs)
    plain_raw = render_markdown(text, width=width, color=False, **color_kwargs)
    colored = colored_raw.rstrip("\n").split("\n")
    plain = plain_raw.rstrip("\n").split("\n")
    markdown = ViewmdMarkdown(text, code_theme="monokai")
    outline = heading_outline(markdown)
    return colored, plain, _locate_headings(plain, outline)


def _max_content_width(plain_lines: list[str]) -> int:
    """Widest rendered line, in display columns -- fenced code (VIEWMD-0019) and Mermaid diagrams
    (VIEWMD-0018) both render `crop=False`, so a line can be wider than either the terminal or the
    configured render width. Recomputed after any reload (`_load`) that could change it: the
    initial load, a width toggle, and a resize while full-width mode is active."""
    return max((_display_width(row) for row in plain_lines), default=0)


# ---------------------------------------------------------------------------
# Popup layout (mirrors the issue's mockup: a bordered box overlaid mid-screen)
# ---------------------------------------------------------------------------


def _nearest_heading_index(headings: list[HeadingLoc], top: int) -> int:
    """The heading whose section the reader is currently scrolled into: the last heading at or
    above `top`, or the first heading if `top` is above all of them (e.g. still in the front
    matter)."""
    if not headings:
        return 0
    idx = 0
    for i, h in enumerate(headings):
        if h.row <= top:
            idx = i
        else:
            break
    return idx


def _popup_box(
    headings: list[HeadingLoc], selected: int, term_w: int, avail_h: int
) -> tuple[list[str], int]:
    """Returns (box lines, scroll offset). When there are more headings than fit, the window
    scrolls to keep `selected` roughly centered (clamped at the top/bottom of the list rather
    than overscrolling past either end), and the row(s) at the very top/bottom of the box show
    `▲`/`▼` in the marker column whenever there's more content in that direction -- not just at
    the list's hard edges. `scroll` (VIEWMD-0076) is what a caller needs to map a clicked content
    row (`_popup_hit`) back to a heading index: `scroll + content_row`."""
    entries = [h.text for h in headings]
    # `_display_width`, not `len()` -- a heading can contain a wide character (an emoji in
    # prose, or Rich's own image-placeholder glyph, VIEWMD-0070's motivating case), and sizing
    # the box from character *count* instead of terminal *columns* would make it too narrow for
    # its own content once one appears.
    inner_w = min(max((_display_width(e) for e in entries), default=0) + 2, term_w - 4)
    title = " Table of contents "
    inner_w = max(inner_w, len(title))
    box_w = inner_w + 2
    max_rows = max(3, avail_h - 2)  # just the two border rows as overhead
    n = len(entries)

    if n <= max_rows:
        scroll = 0
    else:
        half = max_rows // 2
        scroll = max(0, min(selected - half, n - max_rows))
    window = range(scroll, min(scroll + max_rows, n))
    more_above = scroll > 0
    more_below = scroll + max_rows < n

    def styled(content: str) -> str:
        # Every row opens the box's own bg/fg and closes with a full reset, so a row is always
        # self-contained -- `_overlay` splices plain (uncolored) document text back in right
        # after it, and that must never inherit color left dangling from here.
        return f"{_POPUP_BG}{content}{_RESET}"

    box: list[str] = [styled("┌" + title.center(box_w, "─") + "┐")]
    for pos, i in enumerate(window):
        entry = entries[i]
        if i == selected:
            marker = "▸"
        elif pos == 0 and more_above:
            marker = "▲"
        elif pos == len(window) - 1 and more_below:
            marker = "▼"
        else:
            marker = " "
        text = _wc_ljust(f"{marker}{entry}", box_w)
        if i == selected:
            # Brighter background on top of the box's own, not reverse video -- reverse video
            # would swap to the *terminal's* default colors, not the box's, breaking the panel
            # look precisely on the one row meant to stand out most.
            text = f"{_POPUP_SELECTED_BG}{text}{_POPUP_BG}"
        box.append(styled("│" + text + "│"))
    box.append(styled("└" + ("─" * box_w) + "┘"))
    return box, scroll


def _overlay(
    body_rows: list[str], plain_rows: list[str], popup: list[str], term_w: int
) -> list[str]:
    """Paste `popup`'s rows centered over `body_rows`, leaving everything outside the box
    untouched.

    Rows the popup doesn't touch are returned exactly as given, colors and all. A row the popup
    *does* touch is rebuilt from `plain_rows` (the color=False twin of the same line, see `_load`)
    instead of `body_rows` -- slicing a colored row at an arbitrary column is unsafe in general: a
    color span or OSC8 hyperlink can start before the cut and still be "open" after it, so the
    surviving fragment either leaks color/link state past the box into the popup's own text or
    loses its own styling with no code left to restore it. Rebuilding from the plain row sidesteps
    that at the cost of the affected row's own styling outside the box, which is invisible or a
    minor readability trade-off -- exactly the row(s) the box sits on are the ones losing color.
    """
    if not popup:
        return body_rows
    # `_popup_origin`, not a from-scratch (top, left) computation -- click hit-testing
    # (`_popup_hit`, VIEWMD-0076) needs the exact same origin this splice uses (it also handles
    # the `_display_width`-not-`len()` wide-character concern VIEWMD-0070 raised here originally,
    # since a popup row can contain one -- a heading entry in `_popup_box`), so both share it.
    top, left = _popup_origin(popup, len(body_rows), term_w)
    out = list(body_rows)
    for i, prow in enumerate(popup):
        r = top + i
        if 0 <= r < len(out):
            base = plain_rows[r] if r < len(plain_rows) else ""
            # The resume column after the popup must be based on `prow`'s *visible* width, not
            # its raw character count -- the selected row wraps its whole width in background-
            # color SGR codes (`_popup_box`), which would otherwise push the splice point past
            # where the box actually ends on screen and eat into the row's right-hand text.
            visible_w = _display_width(_strip_ansi(prow))
            # `_ansi_slice`, not raw character-index slicing -- `base` is the underlying document
            # row (`plain_rows`), which can have a wide character anywhere in it (VIEWMD-0070);
            # cutting it at character offset `left` would land on the wrong terminal column
            # whenever one appears before that point, the same reason `_ansi_slice` itself exists
            # rather than a plain `line[start:start+width]`.
            left_part = _ansi_slice(base, 0, left)
            # Pad only far enough to reach the box's own left edge, as plain trailing spaces
            # (never inside a color span, and always appended after real content) -- never all
            # the way to `term_w`: writing literal space characters past the row's real content
            # paints over whatever the terminal would otherwise leave alone, where `_CLEAR_EOL`
            # (an erase, not a write) is what every other row relies on for that instead; on a
            # terminal whose default background isn't flat black (an image, a transparent/tinted
            # profile) an explicit space write paints over it while an erase doesn't, which would
            # make a popup row's background look like it "disappeared".
            left_part += " " * max(0, left - _display_width(_strip_ansi(left_part)))
            right_part = _ansi_slice(base, left + visible_w, max(0, term_w - left - visible_w))
            out[r] = left_part + prow + right_part
    return out


# Tokenizes a line into SGR codes, OSC8 hyperlink wrappers, or single visible characters --
# `_ANSI_RE`'s two escape alternatives first (regex alternation tries left-to-right, so an escape
# always wins over the catch-all when one starts at the current position), `.` for everything
# else. Used by `_ansi_slice` to walk a colored line one token at a time.
_ANSI_TOKEN_RE = re.compile(r"\x1b\[[0-9;]*m|\x1b\]8;[^\x1b]*\x1b\\|.")
_OSC8_CLOSE = "\x1b]8;;\x1b\\"


def _ansi_slice(line: str, start_col: int, width: int) -> str:
    """The horizontal-scroll counterpart to `_overlay`'s vertical splicing: return just display
    columns `[start_col, start_col + width)` of `line`, which may carry SGR color and/or OSC8
    hyperlink escapes.

    A naive `line[start_col:start_col+width]` would count escape bytes as columns (wrong window)
    and, worse, could cut a line mid-span -- e.g. scroll partway into a colored word and the
    result either starts uncolored (the opening code was cut away) or, if a reset was also cut
    away, bleeds that color into whatever prints after it. This walks the line token-by-token
    instead, tracking whatever SGR/OSC8 state is active at `start_col` and re-opening it at the
    start of the result, then closing with `_RESET` at the end if anything was left open --
    exactly the "self-contained span" contract `_overlay`'s own docstring establishes, just
    applied to an arbitrary column cut instead of a fixed set of popup-covered rows.

    Column width per character comes from `_char_width` (`wcwidth`, VIEWMD-0070) -- a double-width
    character (an emoji, most CJK text) whose column span only partially overlaps `[start_col,
    start_col + width)` can't be rendered half a glyph, so that overlap is padded with plain
    space(s) instead of emitting it; a character entirely inside or entirely outside the window
    is unaffected (this is exactly what a single-width character always is, since an integer
    column boundary can never fall inside a 1-column span -- so ordinary content goes through the
    identical code path it always did, unchanged).
    """
    if start_col <= 0 and width >= _display_width(_strip_ansi(line)):
        return line  # fast path: nothing is actually being cut
    col = 0
    end_col = start_col + width
    active_sgr = ""
    active_link = ""
    entered = False
    out: list[str] = []
    for tok in _ANSI_TOKEN_RE.findall(line):
        if tok.startswith("\x1b["):
            active_sgr = "" if tok == _RESET else active_sgr + tok
            if entered:
                out.append(tok)
            continue
        if tok.startswith("\x1b]"):
            active_link = "" if tok == _OSC8_CLOSE else tok
            if entered:
                out.append(tok)
            continue
        w = _char_width(tok)
        span_start, span_end = col, col + w
        col = span_end
        if span_end <= start_col or span_start >= end_col:
            continue  # entirely outside the window -- still advances `col` above, just no output
        if not entered:
            entered = True
            if active_sgr or active_link:
                out.append(active_sgr + active_link)
        overlap = min(span_end, end_col) - max(span_start, start_col)
        out.append(tok if overlap == w else " " * overlap)
        if col >= end_col:
            break
    if entered and (active_sgr or active_link):
        out.append(_RESET)
    return "".join(out)


# OSC8 open token body is "id=<n>;<href>" (or ";<href>" with no id) -- group(1) captures
# everything after the first ";", href included, still URL-encoded (Rich percent-encodes a
# wikilink target's spaces, e.g. `wikilink:Target%20Note`).
_OSC8_OPEN_RE = re.compile(r"\x1b\]8;[^;]*;(.*)\x1b\\$")


def _link_at(colored_line: str, col: int) -> str | None:
    """The href of whatever OSC8-wrapped link span covers display column `col` of
    `colored_line` (VIEWMD-0076's click-to-follow), or `None` if that column isn't inside a
    link -- reuses the same token walk `_ansi_slice` does for horizontal-scroll cropping rather
    than a second parser, see `poc/pager/click_nav_poc.py` where this was prototyped."""
    active_link: str | None = None
    c = 0
    for tok in _ANSI_TOKEN_RE.findall(colored_line):
        if tok.startswith("\x1b]"):
            if tok == _OSC8_CLOSE:
                active_link = None
            else:
                m = _OSC8_OPEN_RE.match(tok)
                active_link = urllib.parse.unquote(m.group(1)) if m else None
            continue
        if tok.startswith("\x1b["):
            continue
        w = _char_width(tok)
        if c <= col < c + w:
            return active_link
        c += w
    return None


_EXTERNAL_SCHEME_RE = re.compile(r"^[a-zA-Z][a-zA-Z0-9+.-]*:(?!/[^/])")


def _resolve_link_target(href: str, current_dir: str) -> str | None:
    """Resolve a clicked link's href to an existing local `.md` file's path, or `None` if it
    isn't one -- an external URL/scheme, a missing file, or a non-`.md` target (VIEWMD-0076
    requirements 3 and 5).

    A `wikilink:Target` href (`viewmd/wikilinks.py`'s static rewrite of `[[Target]]`) resolves
    the way Obsidian does for a flat vault: `Target.md` directly in `current_dir` first, falling
    back to a recursive search under `current_dir` if not found there. An ordinary link's href is
    resolved as a filesystem path relative to `current_dir` directly, no search."""
    if href.startswith("wikilink:"):
        target = href[len("wikilink:") :]
        direct = os.path.join(current_dir, f"{target}.md")
        if os.path.isfile(direct):
            return direct
        for root, _dirs, files in os.walk(current_dir):
            if f"{target}.md" in files:
                return os.path.join(root, f"{target}.md")
        return None
    if href.startswith(("http://", "https://", "mailto:")) or (
        _EXTERNAL_SCHEME_RE.match(href) and "://" in href
    ):
        return None
    # An absolute href isn't "a filesystem path relative to `current_dir`" at all -- MUST reject
    # it explicitly rather than let `os.path.join` silently discard `current_dir` and resolve the
    # href as-is (`os.path.join(a, "/etc/hosts.md") == "/etc/hosts.md"`), which would let a click
    # navigate anywhere reachable on disk instead of only within the document's own directory.
    if os.path.isabs(href):
        return None
    candidate = os.path.normpath(os.path.join(current_dir, href))
    if os.path.isfile(candidate) and candidate.lower().endswith(".md"):
        return candidate
    return None


def _popup_origin(popup: list[str], body_h: int, term_w: int) -> tuple[int, int]:
    """The (top, left) terminal-body coordinates `_overlay` centers `popup` at -- factored out
    of `_overlay` itself (VIEWMD-0076) so click hit-testing (`_popup_hit`) can compute the exact
    same rectangle a click needs to land inside, rather than re-deriving it a second time."""
    if not popup:
        return 0, 0
    popup_w = max(_display_width(_strip_ansi(row)) for row in popup)
    left = max(0, (term_w - popup_w) // 2)
    top = max(0, (body_h - len(popup)) // 2)
    return top, left


def _popup_hit(popup: list[str], body_h: int, term_w: int, col0: int, row0: int) -> int | None:
    """0-indexed content-row index within `popup` (excluding its own border/title rows) that
    0-indexed body coordinates `(col0, row0)` land on, or `None` if they fall outside the box
    entirely or on a border/title row -- shared by the ToC popup (`_popup_box`) and the help
    screen (`_help_box`), which both share the same bordered-box shape (VIEWMD-0076)."""
    if not popup:
        return None
    top, left = _popup_origin(popup, body_h, term_w)
    popup_w = max(_display_width(_strip_ansi(row)) for row in popup)
    if not (top <= row0 < top + len(popup) and left <= col0 < left + popup_w):
        return None
    content_row = row0 - top - 1
    if content_row < 0 or content_row > len(popup) - 3:
        return None
    return content_row


def _content_col(plain_len: int, left_col: int, width: int, screen_col: int) -> int | None:
    """The original (pre-horizontal-scroll) display column a 0-indexed on-screen column
    `screen_col` corresponds to, mirroring `_crop_row`'s own left/right-marker reservation --
    `None` if `screen_col` landed on a `‹`/`›` truncation marker rather than real content
    (VIEWMD-0076's click hit-testing has to undo the same cropping `_crop_row` applied)."""
    left_more = left_col > 0
    right_more = plain_len > left_col + width
    inner_width = width - (1 if left_more else 0) - (1 if right_more else 0)
    start = 1 if left_more else 0
    if screen_col < start or screen_col >= start + inner_width:
        return None
    return left_col + (screen_col - start)


# Truncation-edge markers: a distinct bold orange, not reused from any other chip (search
# highlight, keycaps, popup selection), so "there's more this way" reads as its own thing.
_TRUNCATION_STYLE = "\x1b[1;38;5;214m"


def _crop_row(colored_row: str, plain_len: int, left_col: int, width: int) -> str:
    """The horizontal-scroll counterpart to plain `_ansi_slice`: crop `colored_row` to exactly
    `width` columns starting at `left_col`, like `_ansi_slice` does, but additionally reserve the
    row's first/last column for a `‹`/`›` marker whenever content is actually scrolled out of view
    in that direction -- `plain_len` (the row's real, un-cropped display width, via
    `_display_width`, not `len()` -- VIEWMD-0070) is what decides that, not anything about the
    cropped result itself.

    This is what every visible document row must go through unconditionally, not just when
    `left_col != 0` -- a row wider than `width` prints past the terminal's own edge and the
    terminal wraps it onto an extra physical row on its own, which is indistinguishable from this
    module's own line-based scrolling breaking (each logical row must map to exactly one physical
    terminal row for the `_HOME`-and-redraw scheme in `draw()` to stay correct at all).
    """
    left_more = left_col > 0
    right_more = plain_len > left_col + width
    reserved = (1 if left_more else 0) + (1 if right_more else 0)
    inner_width = max(0, width - reserved)
    sliced = _ansi_slice(colored_row, left_col, inner_width)
    if left_more:
        sliced = f"{_TRUNCATION_STYLE}‹{_RESET}" + sliced
    if right_more:
        sliced = sliced + f"{_TRUNCATION_STYLE}›{_RESET}"
    return sliced


# ---------------------------------------------------------------------------
# Input: raw bytes -> logical events, including SGR mouse wheel reports
# ---------------------------------------------------------------------------


@dataclass
class Event:
    kind: str  # "key" | "wheel_up" | "wheel_down" | "wheel_left" | "wheel_right" | "click"
    value: str = ""
    col: int = 0  # 1-indexed terminal column ("click" only, from the SGR report's Cx)
    row: int = 0  # 1-indexed terminal row ("click" only, from the SGR report's Cy)


def _read_event(fd: int) -> Event:
    b = os.read(fd, 1)
    if b in (b"\x7f", b"\x08"):
        return Event("key", "backspace")
    if b != b"\x1b":
        return Event("key", b.decode(errors="replace"))
    # Distinguish a bare Esc (no more bytes within a short window) from the start of an escape
    # sequence (arrow keys, SGR mouse reports) -- xterm sends the whole sequence back-to-back.
    ready, _, _ = select.select([fd], [], [], 0.05)
    if not ready:
        return Event("key", "esc")
    b2 = os.read(fd, 1)
    if b2 != b"[":
        return Event("key", "esc")
    seq = b""
    while True:
        ch = os.read(fd, 1)
        seq += ch
        if ch.isalpha() or ch in (b"~",):
            break
    text = seq.decode(errors="replace")
    if text.startswith("<"):
        # SGR mouse report: "<Cb;Cx;Cy" then 'M' (press) or 'm' (release).
        m = re.match(r"<(\d+);(\d+);(\d+)([Mm])", text)
        if m:
            btn = int(m.group(1))
            if btn == 64:
                return Event("wheel_up")
            if btn == 65:
                return Event("wheel_down")
            if btn == 66:
                return Event("wheel_left")
            if btn == 67:
                return Event("wheel_right")
            # Shift + vertical wheel (SGR adds 4 for a held Shift): the fallback for terminals
            # that never send native horizontal-wheel codes 66/67 at all (confirmed on macOS
            # Terminal.app -- an actual two-finger horizontal trackpad swipe produces nothing
            # there, not even 66/67) -- Shift+wheel-as-horizontal-scroll is the same convention
            # browsers and other GUI apps fall back to for the same reason.
            if btn == 68:
                return Event("wheel_left")
            if btn == 69:
                return Event("wheel_right")
            # A plain (unmodified) left-click press (VIEWMD-0076) -- the release ('m') is ignored,
            # and any modifier-click (Ctrl/Alt/Shift, which SGR encodes into `btn` the same way it
            # does for the Shift+wheel fallback above) deliberately does not match `btn == 0`
            # exactly, matching this issue's Non-goals (modifier-click is out of scope).
            if btn == 0 and m.group(4) == "M":
                return Event("click", col=int(m.group(2)), row=int(m.group(3)))
        return Event("key", "")
    arrows = {
        "A": Event("key", "up"),
        "B": Event("key", "down"),
        "C": Event("key", "right"),
        "D": Event("key", "left"),
    }
    return arrows.get(text, Event("key", ""))


# ---------------------------------------------------------------------------
# Mode line / echo area / help screen
# ---------------------------------------------------------------------------


def _mode_line(
    name: str,
    total: int,
    top: int,
    end: int,
    term_w: int,
    section: str | None = None,
    left_col: int = 0,
) -> str:
    """Info's own mode-line shape: `-----Info: (emacs.info)Copying, 40 lines --Top-------------`
    -- a filename/line-count/scroll-position core, padded out to the full terminal width with a
    continuous double-line rule (`═`) instead of Info's own ASCII `-` or blank space.

    `section`, when given, is the heading of whatever part of the document is currently at the
    top of the screen (see `_nearest_heading_index`) -- appended right-aligned at the very end of
    the line, past the rule fill, so a reader mid-scroll can tell which section they're in without
    the static VIEWMD-0062 ToC (possibly off-screen) or opening the popup. Truncated with a
    trailing `…` if there isn't room for it in full; dropped entirely if there isn't room for even
    a token amount of it plus the minimum rule fill on either side of the core.

    `left_col`, when nonzero, adds a `col N` marker -- there's otherwise no on-screen sign that a
    line has scrolled off to the left, unlike vertical position which the reader can just see."""
    if total <= 0 or (top <= 0 and end >= total):
        pos = "All"
    elif top <= 0:
        pos = "Top"
    elif end >= total:
        pos = "Bot"
    else:
        pos = f"{round(100 * end / total)}%"
    col_marker = f" col {left_col + 1} ══" if left_col else ""
    # `name`/`section` are arbitrary document text (a filename, a heading) and can contain a wide
    # character (VIEWMD-0070), so every width here is `_display_width`, not `len()`; truncation
    # goes through `_ansi_slice` (this line carries no ANSI itself, but the same column-aware
    # walk correctly avoids cutting a wide character in half either way).
    core = f"════ viewmd: {name}, {total} lines ══ {pos} ══{col_marker}"
    core_w = _display_width(core)
    if core_w >= term_w:
        return _ansi_slice(core, 0, term_w)
    remaining = term_w - core_w

    min_fill = 4
    section_block = ""
    if section and remaining - min_fill > 2:
        max_text_w = remaining - min_fill - 2  # 2 = the block's own leading/trailing space
        text = section
        if _display_width(text) > max_text_w:
            text = _ansi_slice(text, 0, max(0, max_text_w - 1)) + "…" if max_text_w >= 1 else ""
        if text:
            section_block = f" {text} "

    return core + "═" * (remaining - _display_width(section_block)) + section_block


# The full keybinding reference, grouped for the '?' help screen (`_help_box`) -- the echo area's
# own default content (`_keybind_help`) only ever shows a short subset of this, pointing at '?'
# for the rest, so it always fits on one line regardless of terminal width.
#
# Each entry's third element (VIEWMD-0076) is the single `Event` clicking that row in the help
# screen synthesizes -- fed through the same base-state dispatch (`_dispatch_base`) a real
# keypress goes through, so a click behaves exactly like pressing that key, inert cases (e.g. `t`
# with no headings) included for free. `None` marks a row with no single unambiguous action to
# invoke -- either it names two different keys doing two different things ("n / p": next *or*
# previous are different actions) or a direction-ambiguous one ("up/down, wheel": which way?), or
# it only describes behavior inside a different mode (the ToC popup's own move/jump/cancel, which
# only mean what this table says while the popup is already open -- not the base view a help-
# screen click always returns to first). A click on such a row is simply a no-op, matching the
# same "outside the box, or a non-actionable row" no-op the issue's requirement 8 already allows.
_HELP_GROUPS: list[tuple[str, list[tuple[str, str, Event | None]]]] = [
    (
        "Scrolling",
        [
            ("up/down, wheel", "scroll one line", None),
            ("space", "page down", Event("key", " ")),
            ("b / - / Backspace", "page back up", Event("key", "b")),
            ("g / ^", "jump to top", Event("key", "g")),
            ("G / $", "jump to bottom", Event("key", "G")),
            ("n / p", "jump to next / previous heading", None),
            ("j / k", "vim-style down / up (same as wheel)", None),
            ("left/right, h/l", "scroll sideways -- for lines wider than the terminal", None),
            ("0", "back to the left edge", Event("key", "0")),
        ],
    ),
    (
        "Search",
        [
            ("/", "search forward -- Enter confirms, Esc cancels", Event("key", "/")),
            ("N", "repeat the last search, no prompt", Event("key", "N")),
            ("Esc", "(with nothing else open) clear the search highlight", Event("key", "esc")),
        ],
    ),
    (
        "Table of contents",
        [
            ("t", "open/close the popup", Event("key", "t")),
            ("up/down, wheel, j/k", "move the selection (in the popup)", None),
            ("Enter", "jump to the selected heading (in the popup)", None),
            ("Esc / t", "cancel, keep the current position (in the popup)", None),
        ],
    ),
    (
        "Links",
        [
            ("click a link", "follow it, if it resolves to a local .md file", None),
            ("B", "go back to the file you navigated from", Event("key", "B")),
        ],
    ),
    (
        "Other",
        [
            ("w", "toggle configured width <-> full terminal width", Event("key", "w")),
            (
                "m",
                "toggle mouse capture -- off lets a drag select text natively",
                Event("key", "m"),
            ),
            ("?", "show/hide this help", Event("key", "?")),
            ("q", "quit", Event("key", "q")),
        ],
    ),
]

# Most terminals also let a modifier key bypass mouse capture for a single drag, no toggling
# needed -- worth surfacing since 'm' off/on is the heavier-handed option.
_MOUSE_SELECT_TIP = "tip: Option-drag (macOS Terminal/iTerm2) or Shift-drag (most others) selects"

# Help-screen table styling: group headers and key names each get their own bold hue, distinct
# from each other and from the popup's own blue panel background, so the table reads as three
# visual tiers (header / key / action) at a glance instead of one flat block of text.
_HELP_HEADER_STYLE = "\x1b[1;38;5;213m"  # bold pink/magenta
_HELP_KEY_STYLE = "\x1b[1;38;5;220m"  # bold gold


def _keybind_help(
    popup_open: bool,
    width_toggle: str | None = None,
    highlight_active: bool = False,
    *,
    has_headings: bool = True,
    has_back: bool = False,
) -> str:
    """The echo area's default content: a short, always-fits keybinding taste, pointing at '?'
    for the complete reference (`_HELP_GROUPS`/`_help_box`) rather than trying to cram every
    binding onto one row -- doing that used to silently lose all its keycap coloring on a narrow
    terminal (see `_pad_ansi`'s plain-text fallback), which is worse than just being short.

    Each key renders as a keycap chip (`_keycap`) rather than a "[key]" bracket notation. The
    result carries color escapes, so it can't be padded/truncated the same way as plain text --
    callers must go through `_pad_ansi` (see its docstring for why).

    `width_toggle`, when given, is appended as a `w: ...` hint -- omitted entirely rather than
    shown disabled when there's nothing for `w` to do (the configured/`--width` render already
    fills the terminal), since a keybinding that's always a no-op isn't worth advertising.
    `highlight_active` likewise only advertises `Esc: clear highlight` while there's a highlight
    to clear. `has_headings` (VIEWMD-0072) likewise drops the `t: contents` hint for content with
    no heading outline to build a popup from (a directory listing, a multi-file view) -- `t` is
    inert there, same reasoning as the other two omissions. `has_back` (VIEWMD-0076) only
    advertises `B: prev file` once there's actually somewhere to go back to -- i.e. after the
    reader has clicked at least one link to navigate away from where they started; showing it
    unconditionally would advertise a key that's a no-op for the entire session until then."""
    if popup_open:
        pairs = [("up/down,wheel,j/k", "move"), ("Enter", "jump"), ("Esc/t", "cancel")]
    else:
        pairs = [("up/down,wheel", "scroll"), ("/", "search")]
        if has_headings:
            pairs.append(("t", "contents"))
        if has_back:
            pairs.append(("B", "prev file"))
        if width_toggle:
            pairs.append(("w", width_toggle))
        if highlight_active:
            pairs.append(("Esc", "clear hl"))
        pairs.append(("?", "help"))
    pairs.append(("q", "quit"))
    return "  ".join(f"{_keycap(key)} {label}" for key, label in pairs)


def _help_box(
    term_w: int, avail_h: int, scroll: int = 0
) -> tuple[list[str], list[Event | None]]:
    """Returns (box lines, per-content-row invoke events). The '?' help screen: every binding
    from `_HELP_GROUPS`, in a table, overlaid the same way as the ToC popup (`_popup_box`/
    `_overlay`) -- same panel styling, same "freeze the scroll position underneath" behavior.
    Unlike the ToC popup there's nothing to select or confirm, so up/down/wheel/j-k scroll the
    table itself when it doesn't fit (`scroll`, in row units, clamped here to the valid range)
    and a dedicated key (Esc/`?`/`q`) closes it instead of "any key".

    Each row is built as (lead, plain_rest, colored_rest): `lead` is the row's own first visible
    column, kept separate from everything colored after it so a `▲`/`▼` scroll indicator can
    replace just that one column without touching -- or needing to parse -- any embedded escape
    codes. Every colored piece is built directly from known plain text here (never sliced out of
    an already-colored string), so this never risks the "cut mid-span" problem `_overlay`'s
    docstring describes: padding is always literal trailing spaces appended after the event, the
    same convention `_crop_row`/`_pad_ansi` use.

    The second return value (VIEWMD-0076) is `_HELP_GROUPS`' own third element per row -- `None`
    for a border/title row, a blank spacer, a group header, or a binding with no single
    unambiguous action (see `_HELP_GROUPS`' own comment) -- aligned index-for-index with the
    *visible* window (after `scroll` is applied), so a caller resolving a click (`_popup_hit`)
    can index straight into it with the content-row index `_popup_hit` returns.

    `avail_h` is the caller's budget for the whole box (borders included) via `max_rows = avail_h
    - 2`, not the full screen body height -- `_overlay` centers the box within whatever body_rows
    it's given, so passing something less than the true body height here is what keeps a margin of
    real document visible above and below the box, rather than the box filling the entire screen
    edge-to-edge whenever the table is long enough to want to. The caller (`draw`) is responsible
    for that margin decision; this function just fills whatever budget it's handed.
    """
    key_w = max(len(key) for _, entries in _HELP_GROUPS for key, _, _ in entries)
    action_w = max(len(action) for _, entries in _HELP_GROUPS for _, action, _ in entries)
    inner_w = min(max(key_w + 2 + action_w, len(_MOUSE_SELECT_TIP)), term_w - 4)
    title = " Keybindings "
    inner_w = max(inner_w, len(title))
    box_w = inner_w + 2

    def styled(content: str) -> str:
        return f"{_POPUP_BG}{content}{_RESET}"

    def row(lead: str, plain_rest: str, colored_rest: str) -> str:
        pad = " " * max(0, box_w - 1 - len(plain_rest))
        return lead + colored_rest + pad

    rows: list[str] = []
    invokes: list[Event | None] = []
    for gi, (group_name, entries) in enumerate(_HELP_GROUPS):
        if gi > 0:
            rows.append(row(" ", "", ""))  # blank line above every header but the first
            invokes.append(None)
        header_rest = f"{group_name}"
        rows.append(row(" ", header_rest, f"{_HELP_HEADER_STYLE}{header_rest}{_POPUP_BG}"))
        invokes.append(None)
        for key, action, invoke in entries:
            key_text = key.ljust(key_w)
            action_text = action
            fixed = f" {key_text}  "
            if len(fixed) + len(action_text) > inner_w:
                action_text = action_text[: max(0, inner_w - len(fixed))]
            plain_rest = f"{key_text}  {action_text}"
            colored_rest = f"{_HELP_KEY_STYLE}{key_text}{_POPUP_BG}  {action_text}"
            rows.append(row(" ", plain_rest, colored_rest))
            invokes.append(invoke)
    rows.append(row(" ", "", ""))
    invokes.append(None)
    rows.append(row(" ", _MOUSE_SELECT_TIP, _MOUSE_SELECT_TIP))
    invokes.append(None)

    max_rows = max(3, avail_h - 2)
    scroll = max(0, min(scroll, max(0, len(rows) - max_rows)))
    window = rows[scroll : scroll + max_rows]
    window_invokes = invokes[scroll : scroll + max_rows]
    more_above = scroll > 0
    more_below = scroll + max_rows < len(rows)

    box: list[str] = [styled("┌" + title.center(box_w, "─") + "┐")]
    for i, colored_row in enumerate(window):
        if i == 0 and more_above:
            colored_row = "▲" + colored_row[1:]
        elif i == len(window) - 1 and more_below:
            colored_row = "▼" + colored_row[1:]
        box.append(styled("│" + colored_row + "│"))
    box.append(styled("└" + ("─" * box_w) + "┘"))
    return box, window_invokes


def _pad_ansi(text: str, width: int) -> str:
    """Pad or truncate `text` (which may carry `_ANSI_RE`-matched color escapes) to exactly
    `width` visible columns, without slicing through a live color span the way plain `str[:n]`/
    `.ljust(n)` would (see `_overlay`'s docstring for why that corrupts colored text in general).
    Padding is always safe (appended after everything, as plain spaces); truncation to a shorter
    width falls back to the plain (uncolored) text instead, since only the echo area's keybind
    summary carries color at all and it's short enough that this path is a rare-terminal-width
    fallback, not something worth building exact colored truncation for."""
    visible = _display_width(_strip_ansi(text))
    if visible <= width:
        return text + " " * (width - visible)
    return _ansi_slice(_strip_ansi(text), 0, width)


def _search(plain_lines: list[str], query: str, start_after: int) -> int | None:
    """First line at/after `start_after + 1` containing `query` (case-insensitive), wrapping
    around to the top if nothing matches below -- Info's own forward `s`/`/` search."""
    if not query:
        return None
    q = query.lower()
    n = len(plain_lines)
    for i in (*range(start_after + 1, n), *range(0, start_after + 1)):
        if q in plain_lines[i].lower():
            return i
    return None


# ---------------------------------------------------------------------------
# Main interactive loop
# ---------------------------------------------------------------------------


def run(
    text: str,
    name: str,
    *,
    width: int,
    color: bool,
    full_front_matter: bool = False,
    toc: bool = True,
) -> None:
    """Page `text` (raw Markdown source) interactively. `name` is the display name shown in the
    mode line (typically the source path, or "-" for stdin); only its basename is shown.

    The only one of the three `_run()` entry points that supports click-to-follow a local-file
    link (VIEWMD-0076) -- it's the only one with a single well-defined file and directory to
    resolve a relative link/wikilink against (`run_directory_listing()`/`run_multi_file()` don't,
    and stdin, `name == "-"`, has no directory either) -- `doc_dir`/`open_path` are left `None`
    for all of those, which makes a click on a link (and the 'B' back key) a no-op in `_run()`.
    """
    color_kwargs = {"full_front_matter": full_front_matter, "toc": toc}
    display_name = "(stdin)" if name == "-" else os.path.basename(name)
    doc_dir = None if name == "-" else os.path.dirname(os.path.abspath(name))

    def open_path(path: str) -> tuple | None:
        # `_resolve_link_target` already confirmed `path` exists and is a `.md` file, but not
        # that it's still readable or valid UTF-8 by the time a click actually opens it (a
        # permissions change, a TOCTOU race, or simply a non-UTF-8 `.md` file) -- `None` on
        # failure lets the caller treat this exactly like any other unresolvable link (a no-op,
        # with an echo-area message) rather than crashing the whole interactive session, matching
        # how `viewmd/__main__.py`'s own `_resolve_document()` handles the identical read for the
        # document viewmd was originally invoked with.
        try:
            with open(path, encoding="utf-8") as f:
                new_text = f.read()
        except (OSError, UnicodeDecodeError):
            return None
        return (
            lambda w: _load(new_text, w, color_kwargs=color_kwargs),
            os.path.basename(path),
            os.path.dirname(os.path.abspath(path)),
        )

    _run(
        lambda w: _load(text, w, color_kwargs=color_kwargs),
        display_name,
        width=width,
        fallback=lambda: render_markdown(text, width=width, color=color, **color_kwargs),
        doc_dir=doc_dir,
        open_path=open_path,
    )


def run_directory_listing(dir_path: str, *, width: int, color: bool) -> None:
    """Page a bare directory listing interactively (VIEWMD-0065's table-of-contents view, no
    `_Index.md` note present). No heading outline to build a ToC popup from (VIEWMD-0072
    Non-goals: no per-entry ToC) -- the 't' key is inert and omitted from the keybinding summary,
    same as any document with no headings of its own; scrolling, search, mouse, resize, and the
    width toggle all work exactly as for a single document."""
    from viewmd.render import render_directory_listing

    def loader(w: int) -> tuple[list[str], list[str], list[HeadingLoc]]:
        colored = render_directory_listing(dir_path, width=w, color=True).rstrip("\n").split("\n")
        plain = render_directory_listing(dir_path, width=w, color=False).rstrip("\n").split("\n")
        return colored, plain, []

    display_name = os.path.basename(os.path.normpath(dir_path)) + "/"
    _run(
        loader,
        display_name,
        width=width,
        fallback=lambda: render_directory_listing(dir_path, width=width, color=color),
    )


def run_multi_file(
    entries: list[tuple[str, str | None]],
    *,
    width: int,
    directory_width: int,
    color: bool,
    full_front_matter: bool,
    toc: bool,
) -> None:
    """Page a multi-file concatenation (two or more `path` arguments) interactively. `entries` is
    `(display_path, text)` per already-resolved path (VIEWMD-0072) -- `text` is the raw Markdown
    source for a plain file/index note, or `None` for a bare directory listing among the paths
    (rendered at the fixed `directory_width`, VIEWMD-0071, not affected by the 'w' toggle below,
    since that default is already the full terminal width in the common case). No heading outline
    across files (VIEWMD-0072 Non-goals: no per-file ToC) -- continuous scroll only, matching
    today's behavior."""
    from viewmd.render import render_multi_file

    def loader(w: int) -> tuple[list[str], list[str], list[HeadingLoc]]:
        colored = render_multi_file(entries, width=w, directory_width=directory_width, color=True,
                                    full_front_matter=full_front_matter, toc=toc)
        plain = render_multi_file(entries, width=w, directory_width=directory_width, color=False,
                                  full_front_matter=full_front_matter, toc=toc)
        return colored.rstrip("\n").split("\n"), plain.rstrip("\n").split("\n"), []

    display_name = f"{len(entries)} files"
    _run(
        loader,
        display_name,
        width=width,
        fallback=lambda: render_multi_file(entries, width=width, directory_width=directory_width,
                                           color=color, full_front_matter=full_front_matter,
                                           toc=toc),
    )


def _run(
    loader,
    display_name: str,
    *,
    width: int,
    fallback,
    doc_dir: str | None = None,
    open_path=None,
) -> None:
    """Shared interactive scrolling engine behind `run()`/`run_directory_listing()`/
    `run_multi_file()` (VIEWMD-0072) -- mouse-wheel scroll, resize handling, search, horizontal
    scroll, width toggle, help screen, and (when `loader` ever returns a non-empty heading list)
    the ToC popup. `loader(w)` re-renders content at width `w`, returning (colored lines,
    plain-twin lines, heading locations) -- called once up front and again on a width toggle or a
    resize while full-width mode is active.

    Reads keyboard/mouse input from `/dev/tty`, not `sys.stdin` -- the underlying content may have
    been read from a pipe (`cat file.md | viewmd -`), in which case stdin itself is already fully
    drained and disconnected from the keyboard by the time this runs, the same reason external
    pagers like `less` used to reopen the controlling terminal for their own input rather than
    trusting their own stdin. `fallback()` renders once, plainly, for when `/dev/tty` can't be
    opened at all (no controlling terminal), which should be rare given the caller already checked
    `sys.stdout.isatty()` before reaching here.

    `doc_dir`/`open_path` (VIEWMD-0076) enable click-to-follow a local `.md` link: `doc_dir` is
    the directory the *currently open* document's relative links/wikilinks resolve against, and
    `open_path(path)` returns a fresh `(loader, display_name, doc_dir)` triple for a resolved
    target file, ready to swap in as the session's new "current document" -- only `run()` passes
    these (see its own docstring); `None` for both (the default) makes link-following and the
    'B' back key inert, matching `run_directory_listing()`/`run_multi_file()`, which have no
    single file/directory of their own to resolve a relative link against.
    """
    try:
        tty_fd = os.open("/dev/tty", os.O_RDONLY)
    except OSError:
        print(fallback(), end="")
        return

    term_w, term_h = shutil.get_terminal_size()
    # The width actually requested (--width), *not* capped to the terminal -- horizontal scroll
    # (`_ansi_slice`) is exactly what makes a wider-than-terminal render viewable, so an oversized
    # width is the main way to actually exercise it (most ordinary Markdown wraps to fit the
    # terminal on its own and never needs to scroll sideways at all).
    configured_width = width
    width_is_full = configured_width == term_w
    full_width_active = False
    lines, plain_lines, headings = loader(configured_width)
    body_h = term_h - 2  # bottom two rows reserved: mode line + echo area (Info-style split)
    # Widest rendered line, in columns -- fenced code (VIEWMD-0019) and Mermaid diagrams
    # (VIEWMD-0018) both render `crop=False`, so a line can be wider than either the terminal or
    # the configured render width. `left_col` is how far into that width the view is scrolled.
    max_content_width = _max_content_width(plain_lines)
    left_col = 0
    h_step = 8
    # Back-stack for click-to-follow (VIEWMD-0076): each entry is the document being navigated
    # *away* from -- (loader, display_name, doc_dir, top, left_col, full_width_active) -- so 'B'
    # can restore it exactly, most-recently-left last (a plain list.pop()). `full_width_active`
    # is captured per-frame, not re-read from whatever it is at pop time: the reader could toggle
    # 'w' while on the "away" document, and re-wrapping the restored document at the *current*
    # width setting instead of the one `top`/`left_col` were actually measured against would
    # apply those raw offsets to a differently-wrapped document and land somewhere unrelated
    # (found in review).
    nav_stack: list[tuple] = []

    old_settings = termios.tcgetattr(tty_fd)
    top = 0
    popup_open = False
    popup_selected = 0
    saved_top = 0
    help_open = False
    help_scroll = 0
    search_active = False
    search_query = ""
    last_search_query = ""
    echo_message: str | None = None
    mouse_enabled = True

    # Resize handling: SIGWINCH's own Python-level handler only needs to exist (its body can be a
    # no-op) so the signal isn't SIG_DFL/SIG_IGN -- `signal.set_wakeup_fd` is what actually makes
    # this responsive, writing a byte to `resize_read_fd` on every such signal so the main loop's
    # `select.select` below wakes immediately instead of only noticing on the next real keypress
    # (PEP 475 auto-retries an interrupted blocking read/select with its original arguments, so a
    # bare `signal.signal` handler alone would set a flag but not actually unblock anything until
    # more input arrived -- this is the same self-pipe trick `less`'s own SIGWINCH handling is
    # built on, just via the stdlib's built-in wakeup-fd support instead of a hand-rolled pipe).
    resize_read_fd, resize_write_fd = os.pipe()
    os.set_blocking(resize_read_fd, False)
    os.set_blocking(resize_write_fd, False)  # set_wakeup_fd requires its fd to be non-blocking
    previous_wakeup_fd = signal.set_wakeup_fd(resize_write_fd)
    previous_winch_handler = signal.getsignal(signal.SIGWINCH)
    signal.signal(signal.SIGWINCH, lambda signum, frame: None)

    def draw() -> None:
        end = min(top + body_h, len(lines))
        # A row containing the active search term is rebuilt from its plain twin with the match
        # highlighted (see `_highlight_matches`); every other row keeps its real color untouched.
        # This runs on every redraw, at whatever scroll position, so matches stay highlighted as
        # the reader scrolls around after a search -- not just on the line the search jumped to.
        # Horizontal crop (with `‹`/`›` truncation markers) applies to every real document row
        # unconditionally, before the popup/help overlay (if any) is composited -- `_overlay`'s
        # own column math assumes each row already starts at absolute terminal column 0 and is
        # exactly `term_w` wide, so this has to run regardless of `left_col`, not only while
        # actually scrolled: an uncropped row wider than the terminal wraps onto an extra
        # physical row on its own, which `_crop_row`'s docstring covers in more detail.
        visible = []
        for i in range(top, end):
            row = None
            if last_search_query:
                row = _highlight_matches(plain_lines[i], last_search_query)
            row = row or lines[i]
            # `_crop_row`'s truncation-marker decision must be based on *this row's own* visible
            # length, not `len(plain_lines[i])` -- most diagram types render identical text with
            # color on/off (so the two would agree), but not all of them do (`render_markdown`'s
            # own docstring documents that a diagram type may size itself differently depending
            # on `color`, VIEWMD-0043) -- using the mismatched plain-twin length here would make
            # `_crop_row` decide whether more content exists off-screen using a number that
            # doesn't describe the row actually being cropped.
            visible.append(_crop_row(row, _display_width(_strip_ansi(row)), left_col, term_w))
        visible += [""] * (body_h - len(visible))
        if popup_open or help_open:
            plain_visible = [
                _crop_row(row, _display_width(row), left_col, term_w)
                for row in plain_lines[top:end]
            ]
            plain_visible += [""] * (body_h - len(plain_visible))
            overlay_box = (
                _popup_box(headings, popup_selected, term_w, body_h)[0]
                if popup_open
                else _help_box(term_w, max(3, body_h - 2), help_scroll)[0]
            )
            visible = _overlay(visible, plain_visible, overlay_box, term_w)
        # `_CLEAR_EOL` only when the row is genuinely shorter than the terminal -- a row cropped
        # to *exactly* `term_w` (any wide diagram line, `_crop_row`'s whole point) leaves the
        # cursor sitting in a "pending wrap" state at the last column, and many terminals' erase-
        # in-line in that state erases the character just written there instead of leaving it
        # alone, since the cursor hasn't logically advanced past it yet. That character is
        # whatever's in the row's last column -- for a cropped row, exactly the `›` truncation
        # marker `_crop_row` just placed there, silently wiping out the one thing this feature
        # exists to show. Erasing is only needed (and only safe) when there's real blank trailing
        # space to clear, i.e. the row is shorter than `term_w` in the first place.
        visible = [
            row if _display_width(_strip_ansi(row)) >= term_w else row + _CLEAR_EOL
            for row in visible
        ]
        section = None
        if headings:
            section = headings[_nearest_heading_index(headings, top)].text
        mode_line_text = _mode_line(
            display_name, len(lines), top, end, term_w, section, left_col
        )
        mode_line = f"{_MODE_LINE_BG}{mode_line_text}{_RESET}"
        if help_open:
            echo_text = f"{_keycap('up/down,wheel,j/k')} scroll  {_keycap('Esc/?/q')} close help"
        elif search_active:
            # A literal block glyph, not a real cursor position -- the real terminal cursor is
            # hidden for the whole session (`_ENTER_SCREEN`'s `\x1b[?25l`), and any attempt to
            # mimic one with reverse-video SGR here would hit the same "slicing through live
            # color state" problem `_overlay` was built to avoid (see its docstring); a plain
            # character sidesteps that entirely while still reading as "text is being typed here".
            echo_text = f"Search: {search_query}█"
        elif echo_message:
            echo_text = echo_message
        else:
            width_toggle = None
            if not width_is_full:
                width_toggle = f"{configured_width} cols" if full_width_active else "full width"
            echo_text = _keybind_help(popup_open, width_toggle, bool(last_search_query),
                                      has_headings=bool(headings), has_back=bool(nav_stack))
        # `_pad_ansi` always fills exactly `term_w` columns, so there's never real trailing space
        # left to erase -- no `_CLEAR_EOL` here, for the same pending-wrap-cursor reason `visible`
        # only appends one conditionally above.
        echo_line = _pad_ansi(echo_text, term_w)
        out = _HOME + "\n".join(visible) + "\n" + mode_line + "\n" + echo_line
        sys.stdout.write(out)
        sys.stdout.flush()

    def _dispatch_base(ev: Event) -> bool:
        """Handle one event in the base (no popup/search/help overlay open) state -- factored out
        of the main loop (VIEWMD-0076) so a help-screen click-invoke can feed a synthesized `Event`
        through the exact same dispatch a real keypress goes through, inert cases (e.g. `t` with
        no headings) included for free, rather than re-deriving what each key does a second time.
        Returns `True` if 'q' was pressed (or invoked) and the pager should quit -- a nested
        function can't `break` its caller's loop directly, so this is the substitute signal.

        `max_top` here is always freshly computed from the *current* `lines`/`body_h` at the top
        of this call, not the outer loop's own per-iteration `max_top` -- deliberately a separate
        local (not `nonlocal`), so a `lines`-reloading branch below (`w`, or a click-navigate) can
        safely reassign its own copy without also having to keep the outer loop's copy in sync.
        """
        nonlocal top, left_col, popup_open, saved_top, popup_selected, help_open, help_scroll
        nonlocal search_active, search_query, last_search_query, echo_message, mouse_enabled
        nonlocal full_width_active, lines, plain_lines, headings, max_content_width
        nonlocal loader, display_name, doc_dir
        max_top = max(0, len(lines) - body_h)
        if ev.value == "q" and ev.kind == "key":
            return True
        if ev.kind == "key" and ev.value == "t" and headings:
            popup_open = True
            saved_top = top
            popup_selected = _nearest_heading_index(headings, top)
        elif ev.kind == "key" and ev.value == "?":
            help_open = True
            help_scroll = 0
        elif ev.kind == "key" and ev.value == "/":
            search_active = True
            # Prefilled with the last query, not blank -- Enter alone repeats it, or
            # Backspace clears it out to type a fresh one; either way it's remembered
            # rather than making every search start from scratch.
            search_query = last_search_query
        elif ev.kind == "key" and ev.value == "N":
            # Repeat the last search without opening the prompt at all -- Info's own
            # `/`-then-Enter reuses its last pattern the same way, just one keystroke.
            if last_search_query:
                found = _search(plain_lines, last_search_query, top)
                if found is not None:
                    top = min(max_top, found)
                else:
                    echo_message = f'Search failed: "{last_search_query}"'
            else:
                echo_message = "No previous search"
        elif ev.kind == "key" and ev.value == "esc" and last_search_query:
            # Esc with nothing else open clears the highlight rather than doing nothing --
            # otherwise there'd be no way to turn it off short of searching for something
            # that can't match.
            last_search_query = ""
        elif ev.kind in ("wheel_up",) or (ev.kind == "key" and ev.value in ("up", "k")):
            top = max(0, top - 1)
        elif ev.kind in ("wheel_down",) or (
            ev.kind == "key" and ev.value in ("down", "j")
        ):
            top = min(max_top, top + 1)
        elif ev.kind == "key" and ev.value == " ":
            top = min(max_top, top + body_h)
        elif ev.kind == "key" and ev.value in ("b", "backspace", "-"):
            top = max(0, top - body_h)
        elif ev.kind == "key" and ev.value == "n":
            later = [h.row for h in headings if h.row > top]
            if later:
                top = min(max_top, later[0])
        elif ev.kind == "key" and ev.value == "p":
            earlier = [h.row for h in headings if h.row < top]
            if earlier:
                top = min(max_top, earlier[-1])
        elif ev.kind == "key" and ev.value in ("g", "^"):
            top = 0
        elif ev.kind == "key" and ev.value in ("G", "$"):
            top = max_top
        elif ev.kind == "wheel_left" or (ev.kind == "key" and ev.value in ("left", "h")):
            left_col = max(0, left_col - h_step)
        elif ev.kind == "wheel_right" or (ev.kind == "key" and ev.value in ("right", "l")):
            max_left_col = max(0, max_content_width - term_w)
            left_col = min(max_left_col, left_col + h_step)
        elif ev.kind == "key" and ev.value == "0":
            left_col = 0
        elif ev.kind == "key" and ev.value == "m":
            mouse_enabled = not mouse_enabled
            sys.stdout.write(_MOUSE_ON if mouse_enabled else _MOUSE_OFF)
            sys.stdout.flush()
            echo_message = (
                "Mouse capture on -- wheel scrolls; drag to select text needs 'm' off"
                if mouse_enabled
                else "Mouse capture off -- drag to select text; 'm' re-enables wheel scroll"
            )
        elif ev.kind == "key" and ev.value == "w" and not width_is_full:
            full_width_active = not full_width_active
            new_width = term_w if full_width_active else configured_width
            # Width changes rewrap the whole document, so every line/row number shifts --
            # re-derive from the section the reader was actually in, not the raw `top`
            # line offset, so the toggle lands back in roughly the same place instead of
            # some arbitrary point mid-paragraph a few lines off from where they were.
            section = _nearest_heading_index(headings, top)
            lines, plain_lines, headings = loader(new_width)
            max_top = max(0, len(lines) - body_h)
            if headings:
                top = min(max_top, headings[min(section, len(headings) - 1)].row)
            else:
                top = 0
            max_content_width = _max_content_width(plain_lines)
            left_col = min(left_col, max(0, max_content_width - term_w))
        elif ev.kind == "key" and ev.value == "B":
            # Go back to the file navigated *from* (VIEWMD-0076 requirement 6) -- a no-op with
            # nothing on the stack, including for `run_directory_listing()`/`run_multi_file()`,
            # which never push anything at all (no `open_path`, see `_run`'s own docstring).
            if nav_stack:
                (
                    loader,
                    display_name,
                    doc_dir,
                    saved_doc_top,
                    saved_doc_left,
                    full_width_active,
                ) = nav_stack.pop()
                eff_width = term_w if full_width_active else configured_width
                lines, plain_lines, headings = loader(eff_width)
                max_content_width = _max_content_width(plain_lines)
                new_max_top = max(0, len(lines) - body_h)
                top = min(saved_doc_top, new_max_top)
                left_col = min(saved_doc_left, max(0, max_content_width - term_w))
                popup_selected = 0
                # Same reasoning as the click-navigate branch below: a search highlight/query
                # from the file being left behind doesn't describe the one being returned to.
                search_active = False
                search_query = ""
                last_search_query = ""
            else:
                echo_message = "No previous file to go back to"
        elif ev.kind == "click" and doc_dir is not None and open_path is not None:
            # Click-to-follow a local-file link (VIEWMD-0076 requirements 2-6): resolve which
            # rendered row/column the click landed on, undo horizontal-scroll cropping to get
            # back to the row's real display column, find whatever link (if any) covers it, and
            # -- only if its href resolves to an existing local `.md` file -- swap the session
            # over to that file, after pushing the file being left onto the back-stack. Every
            # other case (no link under the click, an external URL, a missing/non-.md target)
            # is a deliberate no-op, so a terminal's own native OSC8 click-to-open still gets a
            # chance at a link this doesn't resolve (requirement 5).
            body_row = ev.row - 1
            if 0 <= body_row < body_h:
                doc_row = top + body_row
                if 0 <= doc_row < len(lines):
                    plain_len = _display_width(_strip_ansi(lines[doc_row]))
                    content_col = _content_col(plain_len, left_col, term_w, ev.col - 1)
                    if content_col is not None:
                        href = _link_at(lines[doc_row], content_col)
                        if href is not None:
                            target = _resolve_link_target(href, doc_dir)
                            if target is not None:
                                opened = open_path(target)
                                if opened is None:
                                    # Resolved to a real .md file, but it couldn't actually be
                                    # read (permissions, a race, invalid UTF-8) -- a message, not
                                    # a crash or a silent no-op that leaves no trace of why.
                                    echo_message = f"Could not open {os.path.basename(target)}"
                                else:
                                    nav_stack.append(
                                        (
                                            loader,
                                            display_name,
                                            doc_dir,
                                            top,
                                            left_col,
                                            full_width_active,
                                        )
                                    )
                                    loader, display_name, doc_dir = opened
                                    eff_width = (
                                        term_w if full_width_active else configured_width
                                    )
                                    lines, plain_lines, headings = loader(eff_width)
                                    max_content_width = _max_content_width(plain_lines)
                                    top = 0
                                    left_col = 0
                                    popup_selected = 0
                                    # A search highlight/query from the file being left doesn't
                                    # describe the new one at all -- carrying it over would
                                    # highlight spurious matches and let 'N' repeat a search
                                    # against unrelated content (found in review).
                                    search_active = False
                                    search_query = ""
                                    last_search_query = ""
        return False

    try:
        tty.setcbreak(tty_fd)
        sys.stdout.write(_ENTER_SCREEN)
        draw()
        while True:
            ready, _, _ = select.select([tty_fd, resize_read_fd], [], [])
            if resize_read_fd in ready:
                try:
                    os.read(resize_read_fd, 4096)  # drain the wakeup byte(s); content is unused
                except BlockingIOError:
                    pass
                new_w, new_h = shutil.get_terminal_size()
                if (new_w, new_h) != (term_w, term_h):
                    term_w, term_h = new_w, new_h
                    width_is_full = configured_width == term_w
                    if full_width_active:
                        # Full-width mode means "whatever the terminal's width currently is" --
                        # a resize while active has to rewrap, the same as pressing 'w' itself.
                        lines, plain_lines, headings = loader(term_w)
                        max_content_width = _max_content_width(plain_lines)
                    body_h = term_h - 2
                    top = min(top, max(0, len(lines) - body_h))
                    left_col = min(left_col, max(0, max_content_width - term_w))
                    popup_selected = min(popup_selected, max(0, len(headings) - 1))
                draw()
                continue
            if tty_fd not in ready:
                continue
            ev = _read_event(tty_fd)
            max_top = max(0, len(lines) - body_h)
            # Any keypress clears a prior one-shot echo-area message (e.g. "Search failed") back
            # to the keybinding summary, exactly like Info's echo area reverting to blank -- if
            # this key produces a new message (search failing again below), it's set again after.
            echo_message = None
            if help_open:
                # Purely informational -- there's nothing to select or confirm -- but the table
                # can be taller than the screen, so up/down/wheel/j-k scroll it instead of closing
                # it; `_help_box`'s own scroll clamp keeps `help_scroll` in range regardless of how
                # far this pushes it. A dedicated key closes it, matching the ToC popup's Esc/t
                # rather than "any key" -- that would make scrolling impossible.
                if ev.kind in ("wheel_up",) or (ev.kind == "key" and ev.value in ("up", "k")):
                    help_scroll = max(0, help_scroll - 1)
                elif ev.kind in ("wheel_down",) or (
                    ev.kind == "key" and ev.value in ("down", "j")
                ):
                    help_scroll += 1
                elif ev.kind == "key" and ev.value in ("esc", "?", "q"):
                    help_open = False
                    help_scroll = 0
                elif ev.kind == "click":
                    # Click-invoke (VIEWMD-0076, requirement 8): resolve which row the click
                    # landed on, then close help first and feed the row's own invoke `Event`
                    # (if it has one) through the same base-state dispatch a real keypress
                    # would go through -- so it behaves exactly as if that key were pressed,
                    # inert cases (e.g. `t` with no headings) included for free.
                    box, invokes = _help_box(term_w, max(3, body_h - 2), help_scroll)
                    hit = _popup_hit(box, body_h, term_w, ev.col - 1, ev.row - 1)
                    if hit is not None and hit < len(invokes) and invokes[hit] is not None:
                        help_open = False
                        help_scroll = 0
                        if _dispatch_base(invokes[hit]):
                            break
            elif search_active:
                if ev.kind == "key" and ev.value == "esc":
                    search_active = False
                    search_query = ""
                elif ev.kind == "key" and ev.value in ("\r", "\n"):
                    search_active = False
                    # Remembered either way: a typed term becomes the active search/highlight, and
                    # an empty one (typically after backspacing out a prefilled query) clears it --
                    # confirming blank reads as "I want the highlight gone", not "repeat last".
                    last_search_query = search_query
                    if search_query:
                        found = _search(plain_lines, search_query, top)
                        if found is not None:
                            top = min(max_top, found)
                        else:
                            echo_message = f'Search failed: "{search_query}"'
                elif ev.kind == "key" and ev.value == "backspace":
                    search_query = search_query[:-1]
                elif ev.kind == "key" and len(ev.value) == 1 and ev.value.isprintable():
                    # Typed as the search query, not a command -- 'q' quits the pager everywhere
                    # else, but here it's just a letter someone might be searching for.
                    search_query += ev.value
            elif popup_open:
                if ev.kind == "key" and ev.value == "esc":
                    popup_open = False
                    top = saved_top
                elif ev.kind == "key" and ev.value == "t":
                    popup_open = False
                    top = saved_top
                elif ev.kind in ("wheel_up",) or (ev.kind == "key" and ev.value in ("up", "k")):
                    popup_selected = max(0, popup_selected - 1)
                elif ev.kind in ("wheel_down",) or (
                    ev.kind == "key" and ev.value in ("down", "j")
                ):
                    popup_selected = min(len(headings) - 1, popup_selected + 1)
                elif ev.kind == "key" and ev.value in ("\r", "\n"):
                    if headings:
                        top = min(max_top, headings[popup_selected].row)
                    popup_open = False
                elif ev.kind == "key" and ev.value == "q":
                    break
                elif ev.kind == "click":
                    # Click-select-and-confirm (VIEWMD-0076, requirement 7): a click on an entry
                    # row picks it and jumps immediately, same as arrowing to it then Enter -- a
                    # click on the box's own border/title row, or outside the box entirely,
                    # is a no-op (`_popup_hit` returns `None` for both).
                    box, scroll = _popup_box(headings, popup_selected, term_w, body_h)
                    hit = _popup_hit(box, body_h, term_w, ev.col - 1, ev.row - 1)
                    if hit is not None:
                        idx = scroll + hit
                        if idx < len(headings):
                            popup_selected = idx
                            top = min(max_top, headings[popup_selected].row)
                            popup_open = False
            else:
                if _dispatch_base(ev):
                    break
            draw()
    finally:
        sys.stdout.write(_EXIT_SCREEN)
        sys.stdout.flush()
        termios.tcsetattr(tty_fd, termios.TCSADRAIN, old_settings)
        signal.signal(signal.SIGWINCH, previous_winch_handler)
        signal.set_wakeup_fd(previous_wakeup_fd if previous_wakeup_fd >= 0 else -1)
        os.close(resize_read_fd)
        os.close(resize_write_fd)
        os.close(tty_fd)

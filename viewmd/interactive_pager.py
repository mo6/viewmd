"""viewmd's own interactive terminal pager (VIEWMD-0007), replacing the default delegation to an
external `less` subprocess: raw terminal input, line-based scroll with mouse-wheel support, a
two-line Info-style mode-line/echo-area status split, a table-of-contents popup, forward search
with match highlighting, horizontal scroll for content wider than the terminal, a render-width
toggle, a mouse-capture toggle, direct terminal-resize handling, and a `?` help screen.

Ported from `poc/pager/pager_poc.py`, the proof-of-concept built to de-risk this architecture
shape before it was scoped for real building -- see that issue's Design notes for the full
rationale. `viewmd/pager.py` decides when to reach for `run()` here versus the plain-print or
`$PAGER`-subprocess paths; this module doesn't make that decision itself.
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
from dataclasses import dataclass

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
# wheel-scroll events as synthetic "buttons" 64/65 -- this is the same mechanism VIEWMD-0067
# leaned on via `less --mouse`, now handled here directly instead of by an external pager.
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


def _popup_box(headings: list[HeadingLoc], selected: int, term_w: int, avail_h: int) -> list[str]:
    """When there are more headings than fit, the window scrolls to keep `selected` roughly
    centered (clamped at the top/bottom of the list rather than overscrolling past either end),
    and the row(s) at the very top/bottom of the box show `▲`/`▼` in the marker column whenever
    there's more content in that direction -- not just at the list's hard edges."""
    entries = [h.text for h in headings]
    inner_w = min(max((len(e) for e in entries), default=0) + 2, term_w - 4)
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
        text = f"{marker}{entry}".ljust(box_w)
        if i == selected:
            # Brighter background on top of the box's own, not reverse video -- reverse video
            # would swap to the *terminal's* default colors, not the box's, breaking the panel
            # look precisely on the one row meant to stand out most.
            text = f"{_POPUP_SELECTED_BG}{text}{_POPUP_BG}"
        box.append(styled("│" + text + "│"))
    box.append(styled("└" + ("─" * box_w) + "┘"))
    return box


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
    popup_w = max(len(_strip_ansi(row)) for row in popup)
    left = max(0, (term_w - popup_w) // 2)
    top = max(0, (len(body_rows) - len(popup)) // 2)
    out = list(body_rows)
    for i, prow in enumerate(popup):
        r = top + i
        if 0 <= r < len(out):
            base = plain_rows[r] if r < len(plain_rows) else ""
            # The resume column after the popup must be based on `prow`'s *visible* width, not
            # its raw character count -- the selected row wraps its whole width in background-
            # color SGR codes (`_popup_box`), which would otherwise push the splice point past
            # where the box actually ends on screen and eat into the row's right-hand text.
            visible_w = len(_strip_ansi(prow))
            # Pad only far enough to reach the box's own right edge, never all the way to
            # `term_w`: padding further than the row's real content (or the box) needs writes
            # literal space characters over whatever the terminal would otherwise leave alone --
            # every other row relies on `_CLEAR_EOL` (an erase, not a write) for that instead, and
            # on terminals where the default background isn't flat black (a background image, a
            # transparent/tinted profile) an explicit space write paints over it while an erase
            # doesn't, which would make a popup row's background look like it "disappeared".
            padded = base.ljust(left + visible_w)
            out[r] = padded[:left] + prow + padded[left + visible_w:]
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

    Assumes one column per character (no `wcwidth`); a CJK/emoji-heavy line would misalign here
    the same as everywhere else in this module.
    """
    if start_col <= 0 and width >= len(_strip_ansi(line)):
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
        if col == start_col and not entered:
            entered = True
            if active_sgr or active_link:
                out.append(active_sgr + active_link)
        if start_col <= col < end_col:
            out.append(tok)
        col += 1
        if col >= end_col:
            break
    if entered and (active_sgr or active_link):
        out.append(_RESET)
    return "".join(out)


# Truncation-edge markers: a distinct bold orange, not reused from any other chip (search
# highlight, keycaps, popup selection), so "there's more this way" reads as its own thing.
_TRUNCATION_STYLE = "\x1b[1;38;5;214m"


def _crop_row(colored_row: str, plain_len: int, left_col: int, width: int) -> str:
    """The horizontal-scroll counterpart to plain `_ansi_slice`: crop `colored_row` to exactly
    `width` columns starting at `left_col`, like `_ansi_slice` does, but additionally reserve the
    row's first/last column for a `‹`/`›` marker whenever content is actually scrolled out of view
    in that direction -- `plain_len` (the row's real, un-cropped display width) is what decides
    that, not anything about the cropped result itself.

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
    kind: str  # "key" | "wheel_up" | "wheel_down"
    value: str = ""


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
    core = f"════ viewmd: {name}, {total} lines ══ {pos} ══{col_marker}"
    if len(core) >= term_w:
        return core[:term_w]
    remaining = term_w - len(core)

    min_fill = 4
    section_block = ""
    if section and remaining - min_fill > 2:
        max_text_w = remaining - min_fill - 2  # 2 = the block's own leading/trailing space
        text = section
        if len(text) > max_text_w:
            text = text[: max(0, max_text_w - 1)] + "…" if max_text_w >= 1 else ""
        if text:
            section_block = f" {text} "

    return core + "═" * (remaining - len(section_block)) + section_block


# The full keybinding reference, grouped for the '?' help screen (`_help_box`) -- the echo area's
# own default content (`_keybind_help`) only ever shows a short subset of this, pointing at '?'
# for the rest, so it always fits on one line regardless of terminal width.
_HELP_GROUPS: list[tuple[str, list[tuple[str, str]]]] = [
    (
        "Scrolling",
        [
            ("up/down, wheel", "scroll one line"),
            ("space", "page down"),
            ("b / - / Backspace", "page back up"),
            ("g / ^", "jump to top"),
            ("G / $", "jump to bottom"),
            ("n / p", "jump to next / previous heading"),
            ("j / k", "vim-style down / up (same as wheel)"),
            ("left/right, h/l", "scroll sideways -- for lines wider than the terminal"),
            ("0", "back to the left edge"),
        ],
    ),
    (
        "Search",
        [
            ("/", "search forward -- Enter confirms, Esc cancels"),
            ("N", "repeat the last search, no prompt"),
            ("Esc", "(with nothing else open) clear the search highlight"),
        ],
    ),
    (
        "Table of contents",
        [
            ("t", "open/close the popup"),
            ("up/down, wheel, j/k", "move the selection (in the popup)"),
            ("Enter", "jump to the selected heading (in the popup)"),
            ("Esc / t", "cancel, keep the current position (in the popup)"),
        ],
    ),
    (
        "Other",
        [
            ("w", "toggle configured width <-> full terminal width"),
            ("m", "toggle mouse capture -- off lets a drag select text natively"),
            ("?", "show/hide this help"),
            ("q", "quit"),
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
    popup_open: bool, width_toggle: str | None = None, highlight_active: bool = False
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
    to clear."""
    if popup_open:
        pairs = [("up/down,wheel,j/k", "move"), ("Enter", "jump"), ("Esc/t", "cancel")]
    else:
        pairs = [("up/down,wheel", "scroll"), ("/", "search"), ("t", "contents")]
        if width_toggle:
            pairs.append(("w", width_toggle))
        if highlight_active:
            pairs.append(("Esc", "clear hl"))
        pairs.append(("?", "help"))
    pairs.append(("q", "quit"))
    return "  ".join(f"{_keycap(key)} {label}" for key, label in pairs)


def _help_box(term_w: int, avail_h: int, scroll: int = 0) -> list[str]:
    """The '?' help screen: every binding from `_HELP_GROUPS`, in a table, overlaid the same way
    as the ToC popup (`_popup_box`/`_overlay`) -- same panel styling, same "freeze the scroll
    position underneath" behavior. Unlike the ToC popup there's nothing to select or confirm, so
    up/down/wheel/j-k scroll the table itself when it doesn't fit (`scroll`, in row units, clamped
    here to the valid range) and a dedicated key (Esc/`?`/`q`) closes it instead of "any key".

    Each row is built as (lead, plain_rest, colored_rest): `lead` is the row's own first visible
    column, kept separate from everything colored after it so a `▲`/`▼` scroll indicator can
    replace just that one column without touching -- or needing to parse -- any embedded escape
    codes. Every colored piece is built directly from known plain text here (never sliced out of
    an already-colored string), so this never risks the "cut mid-span" problem `_overlay`'s
    docstring describes: padding is always literal trailing spaces appended after the event, the
    same convention `_crop_row`/`_pad_ansi` use.

    `avail_h` is the caller's budget for the whole box (borders included) via `max_rows = avail_h
    - 2`, not the full screen body height -- `_overlay` centers the box within whatever body_rows
    it's given, so passing something less than the true body height here is what keeps a margin of
    real document visible above and below the box, rather than the box filling the entire screen
    edge-to-edge whenever the table is long enough to want to. The caller (`draw`) is responsible
    for that margin decision; this function just fills whatever budget it's handed.
    """
    key_w = max(len(key) for _, entries in _HELP_GROUPS for key, _ in entries)
    action_w = max(len(action) for _, entries in _HELP_GROUPS for _, action in entries)
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
    for gi, (group_name, entries) in enumerate(_HELP_GROUPS):
        if gi > 0:
            rows.append(row(" ", "", ""))  # blank line above every header but the first
        header_rest = f"{group_name}"
        rows.append(row(" ", header_rest, f"{_HELP_HEADER_STYLE}{header_rest}{_POPUP_BG}"))
        for key, action in entries:
            key_text = key.ljust(key_w)
            action_text = action
            fixed = f" {key_text}  "
            if len(fixed) + len(action_text) > inner_w:
                action_text = action_text[: max(0, inner_w - len(fixed))]
            plain_rest = f"{key_text}  {action_text}"
            colored_rest = f"{_HELP_KEY_STYLE}{key_text}{_POPUP_BG}  {action_text}"
            rows.append(row(" ", plain_rest, colored_rest))
    rows.append(row(" ", "", ""))
    rows.append(row(" ", _MOUSE_SELECT_TIP, _MOUSE_SELECT_TIP))

    max_rows = max(3, avail_h - 2)
    scroll = max(0, min(scroll, max(0, len(rows) - max_rows)))
    window = rows[scroll : scroll + max_rows]
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
    return box


def _pad_ansi(text: str, width: int) -> str:
    """Pad or truncate `text` (which may carry `_ANSI_RE`-matched color escapes) to exactly
    `width` visible columns, without slicing through a live color span the way plain `str[:n]`/
    `.ljust(n)` would (see `_overlay`'s docstring for why that corrupts colored text in general).
    Padding is always safe (appended after everything, as plain spaces); truncation to a shorter
    width falls back to the plain (uncolored) text instead, since only the echo area's keybind
    summary carries color at all and it's short enough that this path is a rare-terminal-width
    fallback, not something worth building exact colored truncation for."""
    visible = len(_strip_ansi(text))
    if visible <= width:
        return text + " " * (width - visible)
    return _strip_ansi(text)[:width]


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

    Reads keyboard/mouse input from `/dev/tty`, not `sys.stdin` -- `text` may have been read from
    a pipe (`cat file.md | viewmd -`), in which case stdin itself is already fully drained and
    disconnected from the keyboard by the time this runs, the same reason external pagers like
    `less` reopen the controlling terminal for their own input rather than trusting their own
    stdin. Falls back to a plain, non-interactive render if `/dev/tty` can't be opened at all
    (no controlling terminal), which should be rare given the caller already checked
    `sys.stdout.isatty()` before reaching here.
    """
    color_kwargs = {"full_front_matter": full_front_matter, "toc": toc}
    try:
        tty_fd = os.open("/dev/tty", os.O_RDONLY)
    except OSError:
        print(render_markdown(text, width=width, color=color, **color_kwargs), end="")
        return

    display_name = "(stdin)" if name == "-" else os.path.basename(name)
    term_w, term_h = shutil.get_terminal_size()
    # The width actually requested (--width), *not* capped to the terminal -- horizontal scroll
    # (`_ansi_slice`) is exactly what makes a wider-than-terminal render viewable, so an oversized
    # width is the main way to actually exercise it (most ordinary Markdown wraps to fit the
    # terminal on its own and never needs to scroll sideways at all).
    configured_width = width
    width_is_full = configured_width == term_w
    full_width_active = False
    lines, plain_lines, headings = _load(text, configured_width, color_kwargs=color_kwargs)
    body_h = term_h - 2  # bottom two rows reserved: mode line + echo area (Info-style split)
    # Widest rendered line, in columns -- fenced code (VIEWMD-0019) and Mermaid diagrams
    # (VIEWMD-0018) both render `crop=False`, so a line can be wider than either the terminal or
    # the configured render width. `left_col` is how far into that width the view is scrolled.
    max_content_width = max((len(row) for row in plain_lines), default=0)
    left_col = 0
    h_step = 8

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
            visible.append(_crop_row(row, len(_strip_ansi(row)), left_col, term_w))
        visible += [""] * (body_h - len(visible))
        if popup_open or help_open:
            plain_visible = [
                _crop_row(row, len(row), left_col, term_w) for row in plain_lines[top:end]
            ]
            plain_visible += [""] * (body_h - len(plain_visible))
            overlay_box = (
                _popup_box(headings, popup_selected, term_w, body_h)
                if popup_open
                else _help_box(term_w, max(3, body_h - 2), help_scroll)
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
            row if len(_strip_ansi(row)) >= term_w else row + _CLEAR_EOL for row in visible
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
            echo_text = _keybind_help(popup_open, width_toggle, bool(last_search_query))
        # `_pad_ansi` always fills exactly `term_w` columns, so there's never real trailing space
        # left to erase -- no `_CLEAR_EOL` here, for the same pending-wrap-cursor reason `visible`
        # only appends one conditionally above.
        echo_line = _pad_ansi(echo_text, term_w)
        out = _HOME + "\n".join(visible) + "\n" + mode_line + "\n" + echo_line
        sys.stdout.write(out)
        sys.stdout.flush()

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
                        lines, plain_lines, headings = _load(
                            text, term_w, color_kwargs=color_kwargs
                        )
                        max_content_width = max((len(row) for row in plain_lines), default=0)
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
            else:
                if ev.kind == "key" and ev.value == "q":
                    break
                if ev.kind == "key" and ev.value == "t":
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
                elif ev.kind == "key" and ev.value in ("left", "h"):
                    left_col = max(0, left_col - h_step)
                elif ev.kind == "key" and ev.value in ("right", "l"):
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
                    lines, plain_lines, headings = _load(
                        text, new_width, color_kwargs=color_kwargs
                    )
                    max_top = max(0, len(lines) - body_h)
                    if headings:
                        top = min(max_top, headings[min(section, len(headings) - 1)].row)
                    else:
                        top = 0
                    max_content_width = max((len(row) for row in plain_lines), default=0)
                    left_col = min(left_col, max(0, max_content_width - term_w))
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

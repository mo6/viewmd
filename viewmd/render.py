"""Render Markdown text to an ANSI string using Rich."""

import io
import os
import re
import urllib.parse
from dataclasses import dataclass
from datetime import datetime

from rich import box
from rich.cells import cell_len
from rich.color import Color
from rich.console import Console, ConsoleOptions, RenderResult
from rich.containers import Renderables
from rich.markdown import BlockQuote, CodeBlock, ListItem, Markdown, Paragraph
from rich.markup import escape
from rich.rule import Rule
from rich.segment import Segment
from rich.style import Style
from rich.syntax import Syntax
from rich.table import Table
from rich.text import Text
from wcwidth import wcswidth

from viewmd.frontmatter import drop_empty, parse_front_matter, split_front_matter
from viewmd.mermaid.preprocess import MERMAID_RENDERED_INFO
from viewmd.preprocessors import preprocess

# The per-directory landing note(s) viewmd looks for when a `path` argument is a directory
# (VIEWMD-0065), analogous to Obsidian-style vault index notes. Checked in this order -- the
# original Obsidian-style convention first, then the two lowercase static-site-generator
# conventions (`index.md`: plain/Jekyll-style; `_index.md`: Hugo section index) -- so a directory
# with more than one present picks the same file every time (VIEWMD-0074).
INDEX_FILENAMES = ("_Index.md", "index.md", "_index.md")


class ViewmdCodeBlock(CodeBlock):
    """Code fence that never wraps or loses content, mermaid art included.

    Rich 15's default ``CodeBlock`` hardcodes ``Syntax(..., word_wrap=True,
    padding=1)``, which folds long lines onto extra rows instead of letting
    them run wide. A line longer than the render width should stay intact and
    scroll horizontally in the pager rather than being torn onto a second
    line -- or, as an earlier version of this
    class did, silently cropped and lost (VIEWMD-0019). Mermaid-rendered
    fences (tagged with ``MERMAID_RENDERED_INFO``) already got this treatment
    for VIEWMD-0018; ordinary fences now get the same one, via ``Syntax``
    re-rendered at its own natural width (at least the console's width, so a
    block whose lines all fit still fills the row as before) instead of the
    console's declared width, so nothing is truncated.
    """

    def __rich_console__(
        self, console: Console, options: ConsoleOptions
    ) -> RenderResult:
        code = str(self.text).rstrip()
        if self.lexer_name == MERMAID_RENDERED_INFO:
            for line in code.splitlines():
                yield Segment(line)
                yield Segment.line()
            return
        syntax = Syntax(
            code, self.lexer_name, theme=self.theme, word_wrap=False, padding=1
        )
        natural_width = max((len(line) for line in code.splitlines()), default=0) + 2
        wide_options = options.update(width=max(natural_width, options.max_width))
        for line in console.render_lines(syntax, wide_options, pad=False, new_lines=True):
            yield from line


# GFM task-list prefixes as they appear in the already-parsed list-item text
# (rich's MarkdownIt build has no task-list rule, so `[x] ` is literal text).
_TASK_MARKERS = {
    "[ ] ": False,
    "[x] ": True,
    "[X] ": True,
}
_TASK_CHECKED_BULLET = " ✅ "
_TASK_UNCHECKED_BULLET = " ⬜ "
_TASK_CHECKED_STYLE = Style(dim=True, strike=True)


class ViewmdListItem(ListItem):
    """A bullet-list item that renders GFM task-list checkboxes as glyphs.

    ``rich.markdown.Markdown`` does not enable a task-list rule, so a source
    line like ``- [x] label`` arrives as an ordinary list item whose text
    starts with the literal ``[x] ``. Detect that prefix (and ``[ ] `` /
    ``[X] ``), swap the default ``•`` bullet for ``✅`` / ``⬜``, strip the
    marker from the label, and dim+strike a checked item's remaining text.
    Anything else -- including a lookalike like ``[y]`` -- falls through to
    ``ListItem.render_bullet`` unchanged (VIEWMD-0058).
    """

    def __init__(self) -> None:
        super().__init__()
        self._task_checked: bool | None = None
        self._task_inspected = False

    def render_bullet(self, console: Console, options: ConsoleOptions) -> RenderResult:
        checked = self._apply_task_marker()
        if checked is None:
            yield from super().render_bullet(console, options)
            return

        glyph = _TASK_CHECKED_BULLET if checked else _TASK_UNCHECKED_BULLET
        glyph_width = cell_len(glyph)
        render_options = options.update(width=options.max_width - glyph_width)
        lines = console.render_lines(self.elements, render_options, style=self.style)
        bullet_style = console.get_style("markdown.item.bullet", default="none")
        bullet = Segment(glyph, bullet_style)
        padding = Segment(" " * glyph_width, bullet_style)
        new_line = Segment("\n")
        first = True
        for line in lines:
            yield bullet if first else padding
            yield from line
            yield new_line
            first = False

    def _apply_task_marker(self) -> bool | None:
        """Strip a leading GFM task marker from the first paragraph, if present.

        Returns True (checked), False (unchecked), or None (not a task item).
        Idempotent: a second call returns the same answer without re-stripping.
        """
        if self._task_inspected:
            return self._task_checked
        self._task_inspected = True
        child = next(iter(self.elements), None)
        if not isinstance(child, Paragraph):
            return None
        for prefix, checked in _TASK_MARKERS.items():
            if child.text.plain.startswith(prefix):
                child.text = child.text[len(prefix) :]
                if checked:
                    child.text.stylize(_TASK_CHECKED_STYLE)
                self._task_checked = checked
                return checked
        return None


# Obsidian/GitHub admonition marker: `[!TYPE]` at the start of a blockquote's
# first paragraph. An optional trailing `+`/`-` (Obsidian's fold flag, a no-op
# in a one-shot terminal render) is consumed so it doesn't leak into the body.
_ADMONITION_RE = re.compile(r"^\[!([^\]\s]+)\][+-]?[ \t]*")

# Round-box glyphs, the same four corners `viewmd/mermaid/grid/canvas.py`
# uses for `shape == "round"` -- copied rather than imported, because a
# Markdown element must not size itself against a Mermaid `Drawing` grid.
_CALLOUT_TL, _CALLOUT_TR, _CALLOUT_BL, _CALLOUT_BR = "╭", "╮", "╰", "╯"
_CALLOUT_H, _CALLOUT_V = "─", "│"


@dataclass(frozen=True)
class _AdmonitionKind:
    icon: str
    color: str
    # Spaces between the icon and the label in the header. Normally 1; some
    # terminals render a base-codepoint+VS16 pair (e.g. WARNING's ⚠️) one
    # column wider than `wcswidth` reports, visually crowding the label --
    # this widens the gap to compensate, hand-verified per icon (VIEWMD-0059).
    icon_pad: int = 1
    # Column width to charge the icon in the header's dash-fill math. Usually
    # None, meaning "trust wcswidth". `⚠️` (U+26A0+U+FE0F) is the one
    # exception hand-verified so far: wcswidth reports 2 for the pair
    # (Unicode's emoji-presentation rule), but `wcwidth` on the bare base
    # codepoint alone reports 1, and several terminal fonts render the pair
    # narrow -- unlike the fully-astral-plane NOTE/TIP/CAUTION icons (no
    # narrow fallback, render wide everywhere) or IMPORTANT's `❗` (both
    # wcswidth and per-character wcwidth agree it's 2, no override needed).
    # Trusting wcswidth for ⚠️ undershoots the real terminal's column count,
    # landing the right border short of the other cards' (VIEWMD-0060,
    # hand-verified in-terminal -- do not assume other icons need the same
    # override without independently re-verifying each one).
    icon_width: int | None = None


# GitHub's five canonical alert types. Colors follow Primer's dark-theme
# palette so the card stays readable on the dark terminals viewmd pages into.
_CANONICAL_ADMONITIONS: dict[str, _AdmonitionKind] = {
    "NOTE": _AdmonitionKind("📝", "#58a6ff"),
    "TIP": _AdmonitionKind("💡", "#3fb950"),
    "IMPORTANT": _AdmonitionKind("❗", "#bc8cff"),
    # U+26A0+U+FE0F; wcswidth==2, but renders a column wider than that in
    # several terminals -- icon_pad=2 compensates, hand-verified in-terminal.
    "WARNING": _AdmonitionKind("⚠️", "#d29922", icon_pad=2, icon_width=1),
    "CAUTION": _AdmonitionKind("🛑", "#f85149"),
}
_GENERIC_ADMONITION = _AdmonitionKind("", "default")


def parse_admonition_marker(text: str) -> tuple[str, str] | None:
    """Return ``(TYPE, remainder)`` if ``text`` starts with a ``[!TYPE]`` marker.

    ``TYPE`` is the literal token (original case). Malformed lookalikes -- an
    empty ``[!]``, an unterminated ``[!NOTE`` -- return None so the caller can
    fall through to a plain blockquote (VIEWMD-0059).
    """
    match = _ADMONITION_RE.match(text)
    if match is None:
        return None
    return match.group(1), text[match.end() :]


def _display_width(s: str) -> int:
    """Terminal column count via ``wcwidth.wcswidth``, never ``len()``."""
    width = wcswidth(s)
    return width if width >= 0 else len(s)


def _drop_quote_color(segment: Segment, quote_color: Color | None) -> Segment:
    """Strip the inherited ``markdown.block_quote`` color, keep emphasis/links."""
    if quote_color is None:
        return segment
    style = segment.style
    if style is None or style.color != quote_color:
        return segment
    return Segment(segment.text, style.without_color, segment.control)


class ViewmdBlockQuote(BlockQuote):
    """A blockquote that renders ``[!TYPE]`` markers as bordered callout cards.

    A first paragraph that begins with a well-formed ``[!TYPE]`` marker is an
    admonition: the marker is stripped and the quote is redrawn as a round
    box with the type's icon and label in the top border. Anything else -- a
    plain quote, ``[!]``, an unterminated bracket -- falls through to
    ``BlockQuote.__rich_console__`` unchanged (VIEWMD-0059).
    """

    def __init__(self) -> None:
        super().__init__()
        self._admonition_inspected = False
        self._admonition_token: str | None = None

    def __rich_console__(
        self, console: Console, options: ConsoleOptions
    ) -> RenderResult:
        token = self._apply_admonition_marker()
        if token is None:
            yield from super().__rich_console__(console, options)
            return

        kind = _CANONICAL_ADMONITIONS.get(token.upper(), _GENERIC_ADMONITION)
        border_style = Style() if kind.color == "default" else Style(color=kind.color)
        width = options.max_width
        label = token.upper()
        left = f"{_CALLOUT_TL}{_CALLOUT_H} "
        right = _CALLOUT_TR
        if kind.icon:
            mid = f"{kind.icon}{' ' * kind.icon_pad}{label} "
            icon_width = (
                kind.icon_width if kind.icon_width is not None else _display_width(kind.icon)
            )
            mid_width = icon_width + kind.icon_pad + _display_width(label) + 1
        else:
            mid = f"{label} "
            mid_width = _display_width(mid)
        fill = max(0, width - _display_width(left) - mid_width - _display_width(right))
        header = left + mid + (_CALLOUT_H * fill) + right
        footer = f"{_CALLOUT_BL}{_CALLOUT_H * max(0, width - 2)}{_CALLOUT_BR}"

        yield Segment(header, border_style)
        yield Segment.line()

        inner_width = max(width - 4, 1)
        body_options = options.update(width=inner_width)
        quote_color = self.style.color
        lines = console.render_lines(self.elements, body_options, pad=True)
        left_seg = Segment(f"{_CALLOUT_V} ", border_style)
        right_seg = Segment(f" {_CALLOUT_V}", border_style)
        for line in lines:
            yield left_seg
            for segment in line:
                yield _drop_quote_color(segment, quote_color)
            yield right_seg
            yield Segment.line()

        yield Segment(footer, border_style)
        yield Segment.line()

    def _apply_admonition_marker(self) -> str | None:
        """Strip a leading ``[!TYPE]`` marker from the first paragraph, if present.

        Returns the TYPE token, or None (not an admonition). Idempotent: a
        second call returns the same answer without re-stripping.
        """
        if self._admonition_inspected:
            return self._admonition_token
        self._admonition_inspected = True
        child = next(iter(self.elements), None)
        if not isinstance(child, Paragraph):
            return None
        parsed = parse_admonition_marker(child.text.plain)
        if parsed is None:
            return None
        token, remainder = parsed
        # Slice by the number of characters consumed so inline styles on the
        # remainder (bold, links) stay attached to the surviving text.
        consumed = len(child.text.plain) - len(remainder)
        child.text = child.text[consumed:]
        if not child.text.plain:
            self.elements = Renderables(list(self.elements)[1:])
        self._admonition_token = token
        return token


class ViewmdMarkdown(Markdown):
    """Markdown renderer with viewmd's element overrides wired in."""

    elements = {
        **Markdown.elements,
        "fence": ViewmdCodeBlock,
        "code_block": ViewmdCodeBlock,
        "list_item_open": ViewmdListItem,
        "blockquote_open": ViewmdBlockQuote,
    }


def _make_console(buffer: io.StringIO, *, width: int, color: bool) -> Console:
    # Both width and height must be set: Console.size ignores an explicit width
    # (and returns 80x25) when force_terminal=True on a dumb/unknown TERM.
    # Height is otherwise unused -- Markdown clears it on the render options.
    return Console(
        file=buffer,
        force_terminal=color,
        no_color=not color,
        color_system="truecolor" if color else None,
        width=width,
        height=4096,
        highlight=False,
    )


# Rich's ListItem.render_bullet prefixes each item with " • " (3 columns) and nested
# lists inherit that indent, so each heading level below h1 steps 3 columns -- matching
# the body's own Markdown bullet lists (VIEWMD-0068).
_TOC_BULLET = " • "
_TOC_NEST_COLUMNS = 3
_TOC_LEVELS = {"h1": 1, "h2": 2, "h3": 3}
# Cap on ToC *entries* (one per included heading), not wrapped terminal rows.
_TOC_MAX_ENTRIES = 20
# Same-document anchor-link scheme for the static ToC block's own entries (VIEWMD-0077), mirroring
# `viewmd/wikilinks.py`'s `wikilink:` precedent -- inert outside viewmd, matching that docstring's
# own "never opened" convention. The interactive pager (`viewmd/interactive_pager.py`) resolves it
# by heading *text*, not position: this ToC can be a level-cut/truncated subset of the full
# outline (`_fit_toc_outline`, below), so an index into *this* list wouldn't line up with the
# pager's own full `HeadingLoc` list once truncation/level-cutting actually kicks in.
_TOC_ANCHOR_SCHEME = "viewmd-toc:"

# Directory-listing subdirectory row link scheme (VIEWMD-0081), same "inert outside viewmd"
# precedent as `_TOC_ANCHOR_SCHEME`/`wikilink:` above -- the interactive pager
# (`viewmd/interactive_pager.py`) recognizes this scheme and resolves it to a subdirectory name
# relative to the listing's own directory, distinct from `.md` file rows, which carry no link
# at all yet (VIEWMD-0081 Non-goals).
_DIR_ANCHOR_SCHEME = "viewmd-dir:"


@dataclass(frozen=True)
class HeadingOutline:
    """One h1/h2/h3 heading as it appears in the document, for the table of contents."""

    text: str
    level: int  # 1, 2, or 3


def _inline_plain_text(token) -> str:
    """Collect visible text from a markdown-it inline token, dropping markup tokens.

    A heading's following ``inline`` token still carries the raw markup in ``content``
    (``**bold**``, ``[link](url)``); the parsed children hold the readable text.
    """
    if token.children:
        return "".join(_inline_plain_text(child) for child in token.children)
    if token.type in {"text", "code_inline"}:
        return token.content
    return ""


def heading_outline(markdown: Markdown) -> list[HeadingOutline]:
    """h1/h2/h3 headings in document order, taken from ``markdown.parsed``.

    Walks Rich's already-parsed markdown-it token stream (the same one the body
    render uses) so the ToC cannot disagree with what the body itself treats as a
    heading (VIEWMD-0062). h4+ tokens are skipped. Headings inside fenced code are
    not in this stream as ``heading_open`` (they stay fence content).
    """
    outline: list[HeadingOutline] = []
    tokens = markdown.parsed
    i = 0
    while i < len(tokens):
        token = tokens[i]
        if token.type == "heading_open":
            level = _TOC_LEVELS.get(token.tag)
            if level is not None:
                text = ""
                if i + 1 < len(tokens) and tokens[i + 1].type == "inline":
                    text = _inline_plain_text(tokens[i + 1])
                outline.append(HeadingOutline(text=text, level=level))
        i += 1
    return outline


def _fit_toc_outline(outline: list[HeadingOutline]) -> tuple[list[HeadingOutline], int]:
    """Pick the deepest heading level whose ToC still fits in ``_TOC_MAX_ENTRIES``.

    Tries h1–h3, then h1–h2, then h1-only. If the chosen cut still overflows,
    truncate to the first ``_TOC_MAX_ENTRIES`` entries in document order and
    report how many were omitted (VIEWMD-0068). If a shallower cut would be
    empty (no headings at that depth -- an irregular document of only h3s, for
    example), keep the deeper outline and truncate that, rather than rendering
    nothing.
    """
    selected = list(outline)
    for max_level in (3, 2):
        if len(selected) <= _TOC_MAX_ENTRIES:
            return selected, 0
        shallower = [h for h in outline if h.level <= max_level - 1]
        if not shallower:
            break
        selected = shallower
    if len(selected) <= _TOC_MAX_ENTRIES:
        return selected, 0
    omitted = len(selected) - _TOC_MAX_ENTRIES
    return selected[:_TOC_MAX_ENTRIES], omitted


def _toc_occurrence_ranks(full_outline: list[HeadingOutline]) -> dict[int, int]:
    """Maps `id(heading)` to its 0-indexed occurrence rank among same-*text* entries in
    `full_outline` (VIEWMD-0077) -- two different headings can share the exact same text (e.g.
    `## Overview` under two different sections), so a link resolved by text alone would always
    land on the *first* one no matter which was actually clicked. `full_outline` must be the
    *un-fitted* `heading_outline()` result (before `_fit_toc_outline` drops/truncates anything) --
    `viewmd/interactive_pager.py`'s `_locate_headings()` builds its own `headings` list from that
    same un-fitted outline, in the same order, so a rank computed here lines up with a rank-based
    lookup there even when the *fitted* ToC block only shows a subset of the full outline."""
    ranks: dict[int, int] = {}
    seen: dict[str, int] = {}
    for h in full_outline:
        ranks[id(h)] = seen.get(h.text, 0)
        seen[h.text] = ranks[id(h)] + 1
    return ranks


def _toc_lines(outline: list[HeadingOutline], full_outline: list[HeadingOutline]) -> list[Text]:
    """One bulleted, heading-styled line per outline entry, nested by level. `outline` is what's
    actually rendered (post `_fit_toc_outline`); `full_outline` is the un-fitted result, needed
    only to disambiguate a duplicate heading text's link target (see `_toc_occurrence_ranks`)."""
    ranks = _toc_occurrence_ranks(full_outline)
    lines: list[Text] = []
    for heading in outline:
        indent = " " * (_TOC_NEST_COLUMNS * (heading.level - 1))
        # Marker uses the same style as the body's Markdown bullet lists; the
        # entry text keeps markdown.h1 / h2 / h3 so weight and color still match
        # the body heading (VIEWMD-0068). The Text itself has no base style, so
        # the heading span does not inherit the bullet's bold. Alignment is
        # flush-left with nest indent, not the body's centered h1.
        line = Text()
        line.append(indent + _TOC_BULLET, style="markdown.item.bullet")
        heading_start = len(line)
        line.append(heading.text, style=f"markdown.h{heading.level}")
        # `stylize`, not folded into the `append` above's own `style=` -- a `Style(link=...)`
        # carries no color/weight of its own, so layering it on top via a second span leaves the
        # heading's visible styling completely unchanged (VIEWMD-0077 requirement 2) while still
        # making Rich emit a real OSC8 hyperlink around just the heading text, not the bullet.
        # The rank prefix (`<n>:<text>`) only matters for a duplicate heading text -- it's still
        # included unconditionally (rather than only when actually ambiguous) so the href format
        # is one predictable shape, not two.
        rank = ranks.get(id(heading), 0)
        href = f"{_TOC_ANCHOR_SCHEME}{rank}:{urllib.parse.quote(heading.text)}"
        line.stylize(Style(link=href), heading_start, len(line))
        lines.append(line)
    return lines


def _split_parsed_at_leading_h1(tokens: list) -> tuple[list, list] | None:
    """Split a parsed token stream after the first h1, or None if that heading is not an h1.

    Title and rest keep the *same* token objects as the full-document parse (VIEWMD-0062), so
    inline links in the title still resolve against reference definitions that appear later.
    """
    for i, token in enumerate(tokens):
        if token.type != "heading_open":
            continue
        if token.tag == "h1":
            for j in range(i + 1, len(tokens)):
                if tokens[j].type == "heading_close":
                    return list(tokens[: j + 1]), list(tokens[j + 1 :])
            return None
        if token.tag in _TOC_LEVELS:
            return None
    return None


def _markdown_with_tokens(source: Markdown, tokens: list) -> ViewmdMarkdown:
    """A Markdown renderable that draws ``tokens`` from an already-parsed document."""
    view = ViewmdMarkdown("", code_theme=source.code_theme)
    view.markup = source.markup
    view.parsed = tokens
    view.justify = source.justify
    view.style = source.style
    view.hyperlinks = source.hyperlinks
    view.inline_code_lexer = source.inline_code_lexer
    view.inline_code_theme = source.inline_code_theme
    return view


def _print_toc(
    console: Console,
    outline: list[HeadingOutline],
    full_outline: list[HeadingOutline],
    omitted: int = 0,
) -> None:
    if not outline:
        return
    for line in _toc_lines(outline, full_outline):
        console.print(line)
    if omitted:
        console.print(f"... {omitted} more")
    console.print()


def render_markdown(
    text: str,
    *,
    width: int,
    color: bool,
    full_front_matter: bool = False,
    toc: bool = True,
) -> str:
    """Render `text` to an ANSI string, `width` columns wide.

    Rendering is pure (writes to an in-memory buffer, never real stdout) so callers decide
    separately whether/how to display the result (see pager.py).

    A leading YAML-style front-matter block (`--- ... ---`) renders as a table, followed by a
    divider, ahead of the rendered document body (VIEWMD-0004). A file with no front matter, an
    unterminated `---` block, or a front-matter block that parses to no pairs, renders unchanged.
    Fields with an empty value are omitted from the table unless `full_front_matter` is True
    (VIEWMD-0005). When `toc` is True (the default), a document with two or more h1/h2/h3 headings
    gets a bulleted outline: after the front-matter divider (if any) the leading h1 renders as
    the document title, then the ToC (that title omitted from the list), then the rest of the
    body. Depth is chosen dynamically so the ToC stays at most 20 entries: h1–h3, then h1–h2,
    then h1-only; if the chosen cut still overflows, it is truncated to the first 20 entries
    in document order with a trailing ``... N more`` note (VIEWMD-0068). The body is run through
    viewmd's preprocessor pipeline (see preprocessors.py)
    before Rich sees it -- Obsidian-style ``[[wikilinks]]`` become ordinary Markdown links
    (VIEWMD-0006), and ` ```mermaid ` fences are rendered to box-drawing art (VIEWMD-0014). `color`
    and `width` are passed into that preprocessing pass too (VIEWMD-0043) -- Mermaid diagrams are
    rendered to plain text before Rich's own `Console` (built from `color`/`width` further down)
    ever sees the body, so a diagram type that wants to look different with/without color, or size
    itself relative to the document's actual render width rather than the raw terminal, needs both
    values itself, not Rich's after-the-fact styling/wrapping.

    ``crop=False`` on the body print lets fenced-code rows wider than ``width`` -- mermaid
    diagram art (VIEWMD-0018) and ordinary code lines alike (VIEWMD-0019) -- survive intact
    instead of being cropped away; ``ViewmdCodeBlock`` is what renders them at their own natural
    width in the first place. Paragraphs, tables, and other elements still wrap to ``width``
    during render — only fenced code is exempt, and only the final buffer crop is disabled.
    """
    raw_front_matter, body = split_front_matter(text)
    front_matter = parse_front_matter(raw_front_matter) if raw_front_matter is not None else {}
    if not full_front_matter:
        front_matter = drop_empty(front_matter)
    body = preprocess(body, color=color, width=width)

    buffer = io.StringIO()
    console = _make_console(buffer, width=width, color=color)
    if front_matter:
        console.print(_front_matter_table(front_matter))
        # A double-line rule, distinct from Markdown's own "-" horizontal rule, so a reader never
        # mistakes this divider for document content.
        console.print(Rule(characters="═", style="dim"))
    # One parse for the ToC outline and the title/rest split: ViewmdMarkdown.__init__
    # is what produces markdown.parsed (Rich's markdown-it token stream). A leading
    # h1 is sliced out of that stream and rendered from the same tokens so it is
    # not duplicated in the ToC or again below it, and so later link-reference
    # definitions still resolve in the title (VIEWMD-0062).
    markdown = ViewmdMarkdown(body, code_theme="monokai")
    if toc:
        outline = heading_outline(markdown)
        if len(outline) >= 2:
            split = _split_parsed_at_leading_h1(markdown.parsed)
            if split is not None and outline[0].level == 1:
                title_tokens, rest_tokens = split
                console.print(_markdown_with_tokens(markdown, title_tokens), crop=False)
                console.print()
                fitted, omitted = _fit_toc_outline(outline[1:])
                # `outline` (title included), not `outline[1:]` -- occurrence ranks (VIEWMD-0077)
                # must be computed against the *same* full list `_locate_headings()`
                # (`viewmd/interactive_pager.py`) builds its own `headings` from, which also
                # includes the title.
                _print_toc(console, fitted, outline, omitted)
                console.print(_markdown_with_tokens(markdown, rest_tokens), crop=False)
            else:
                fitted, omitted = _fit_toc_outline(outline)
                _print_toc(console, fitted, outline, omitted)
                console.print(markdown, crop=False)
            return buffer.getvalue()
    console.print(markdown, crop=False)
    return buffer.getvalue()


def render_file_heading(path: str, *, width: int, color: bool) -> str:
    """Render a bold heading line naming `path`, printed ahead of each file's content when
    multiple files are given on the command line (VIEWMD-0013)."""
    buffer = io.StringIO()
    console = _make_console(buffer, width=width, color=color)
    console.print(f"[bold]{escape(path)}[/bold]")
    return buffer.getvalue()


def render_divider(*, width: int, color: bool) -> str:
    """Render the same double-line divider used between front matter and body (VIEWMD-0004),
    reused here to separate consecutive files (VIEWMD-0013)."""
    buffer = io.StringIO()
    console = _make_console(buffer, width=width, color=color)
    console.print(Rule(characters="═", style="dim"))
    return buffer.getvalue()


def _markdown_title(path: str) -> str:
    """Best-effort display title for a Markdown file at `path`: front-matter `title`, else the
    first heading, else the filename -- used by `render_directory_listing`'s per-entry metadata.
    A file that can't be read or decoded falls back to its filename rather than raising, since a
    directory listing must still show every entry even if one is unreadable."""
    try:
        with open(path, encoding="utf-8") as f:
            text = f.read()
    except (OSError, UnicodeDecodeError):
        return os.path.basename(path)

    raw_front_matter, body = split_front_matter(text)
    if raw_front_matter is not None:
        title = parse_front_matter(raw_front_matter).get("title")
        if title:
            return str(title)

    in_fence = False
    for line in body.splitlines():
        stripped = line.strip()
        if stripped.startswith("```") or stripped.startswith("~~~"):
            in_fence = not in_fence
            continue
        if not in_fence and stripped.startswith("#"):
            return stripped.lstrip("#").strip() or os.path.basename(path)

    return os.path.basename(path)


def render_directory_listing(dir_path: str, *, width: int, color: bool) -> str:
    """Render a one-level table-of-contents view of `dir_path`, used when a `path` argument is a
    directory with none of `INDEX_FILENAMES` inside it (VIEWMD-0065, VIEWMD-0074). Lists immediate
    subdirectories and Markdown files only (no recursion), subdirectories first then files, each
    alphabetically; a raw `OSError` from listing the directory (e.g. permission denied) is left
    to propagate, matching how an unreadable file is handled elsewhere in this module.
    """
    entry_names = os.listdir(dir_path)
    dirs = sorted(
        name for name in entry_names if os.path.isdir(os.path.join(dir_path, name))
    )
    files = sorted(
        name for name in entry_names
        if name.lower().endswith(".md") and os.path.isfile(os.path.join(dir_path, name))
    )

    table = Table(show_header=True, header_style="bold cyan", box=box.ROUNDED, expand=False)
    table.add_column("Name", style="cyan", no_wrap=True)
    table.add_column("Type", no_wrap=True)
    table.add_column("Title")
    table.add_column("Modified", no_wrap=True)

    for name in dirs:
        # A `Text` cell (rather than the plain, markup-escaped strings the other columns use)
        # so a real OSC8 link can be layered on via `stylize` -- same pattern as the static ToC
        # block's own heading links (`_toc_lines`, above). `Text` never parses console markup,
        # so no `escape()` call is needed here the way the plain-string cells still need one.
        name_cell = Text(name + "/")
        href = f"{_DIR_ANCHOR_SCHEME}{urllib.parse.quote(name)}"
        name_cell.stylize(Style(link=href))
        table.add_row(name_cell, "dir", "", "")
    for name in files:
        full_path = os.path.join(dir_path, name)
        title = _markdown_title(full_path)
        modified = datetime.fromtimestamp(os.path.getmtime(full_path)).strftime("%Y-%m-%d %H:%M")
        table.add_row(escape(name), "file", escape(title), modified)

    buffer = io.StringIO()
    console = _make_console(buffer, width=width, color=color)
    console.print(f"[bold]{escape(dir_path)}/[/bold]")
    console.print(table)
    return buffer.getvalue()


def render_multi_file(
    entries: list[tuple[str, str | None]],
    *,
    width: int,
    directory_width: int,
    color: bool,
    full_front_matter: bool,
    toc: bool,
) -> str:
    """Render a resolved multi-file concatenation (two or more `path` arguments, VIEWMD-0013),
    each entry preceded by a heading naming its path and separated by a divider. `entries` is
    `(display_path, text)` per already-read/resolved path -- `text` is `None` for a bare directory
    listing among the paths (rendered at `directory_width`, VIEWMD-0071's own full-terminal-width
    default), or the raw Markdown source otherwise (rendered at `width`). Callers do their own
    file reading/error handling (`viewmd/__main__.py`) before building `entries`; this function is
    pure re-rendering, so it can be called again at a different `width` for the interactive
    pager's width toggle/resize reload (`viewmd.interactive_pager.run_multi_file`, VIEWMD-0072)
    without re-reading anything from disk.
    """
    parts: list[str] = []
    for display_path, text in entries:
        if parts:
            parts.append(render_divider(width=width, color=color))
        parts.append(render_file_heading(display_path, width=width, color=color))
        if text is None:
            parts.append(render_directory_listing(display_path, width=directory_width, color=color))
        else:
            parts.append(render_markdown(text, width=width, color=color,
                                         full_front_matter=full_front_matter, toc=toc))
    return "".join(parts)


def _front_matter_table(data: dict[str, str]) -> Table:
    table = Table(show_header=True, header_style="bold cyan", box=box.ROUNDED, expand=False)
    table.add_column("Field", style="cyan", no_wrap=True)
    table.add_column("Value")
    for key, value in data.items():
        table.add_row(key, value)
    return table

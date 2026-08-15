"""Render Markdown text to an ANSI string using Rich."""

import io
import re
from dataclasses import dataclass

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
from wcwidth import wcswidth

from viewmd.frontmatter import drop_empty, parse_front_matter, split_front_matter
from viewmd.mermaid.preprocess import MERMAID_RENDERED_INFO
from viewmd.preprocessors import preprocess


class ViewmdCodeBlock(CodeBlock):
    """Code fence that never wraps or loses content, mermaid art included.

    Rich 15's default ``CodeBlock`` hardcodes ``Syntax(..., word_wrap=True,
    padding=1)``, which folds long lines onto extra rows instead of letting
    them run wide. A line longer than the render width should stay intact and
    scroll horizontally in the pager (``less -S``, set in pager.py) rather
    than being torn onto a second line -- or, as an earlier version of this
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


# GitHub's five canonical alert types. Colors follow Primer's dark-theme
# palette so the card stays readable on the dark terminals viewmd pages into.
_CANONICAL_ADMONITIONS: dict[str, _AdmonitionKind] = {
    "NOTE": _AdmonitionKind("📝", "#58a6ff"),
    "TIP": _AdmonitionKind("💡", "#3fb950"),
    "IMPORTANT": _AdmonitionKind("❗", "#bc8cff"),
    "WARNING": _AdmonitionKind("⚠️", "#d29922"),  # U+26A0+U+FE0F; wcswidth==2, verified in-terminal
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
        mid = f"{kind.icon} {label} " if kind.icon else f"{label} "
        right = _CALLOUT_TR
        fill = max(0, width - _display_width(left) - _display_width(mid) - _display_width(right))
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


def render_markdown(text: str, *, width: int, color: bool, full_front_matter: bool = False) -> str:
    """Render `text` to an ANSI string, `width` columns wide.

    Rendering is pure (writes to an in-memory buffer, never real stdout) so callers decide
    separately whether/how to display the result (see pager.py).

    A leading YAML-style front-matter block (`--- ... ---`) renders as a table, followed by a
    divider, ahead of the rendered document body (VIEWMD-0004). A file with no front matter, an
    unterminated `---` block, or a front-matter block that parses to no pairs, renders unchanged.
    Fields with an empty value are omitted from the table unless `full_front_matter` is True
    (VIEWMD-0005). The body is run through viewmd's preprocessor pipeline (see preprocessors.py)
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
    console.print(ViewmdMarkdown(body, code_theme="monokai"), crop=False)
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


def _front_matter_table(data: dict[str, str]) -> Table:
    table = Table(show_header=True, header_style="bold cyan", box=box.ROUNDED, expand=False)
    table.add_column("Field", style="cyan", no_wrap=True)
    table.add_column("Value")
    for key, value in data.items():
        table.add_row(key, value)
    return table

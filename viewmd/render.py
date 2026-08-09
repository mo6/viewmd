"""Render Markdown text to an ANSI string using Rich."""

import io

from rich import box
from rich.console import Console, ConsoleOptions, RenderResult
from rich.markdown import CodeBlock, Markdown
from rich.markup import escape
from rich.rule import Rule
from rich.segment import Segment
from rich.syntax import Syntax
from rich.table import Table

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


class ViewmdMarkdown(Markdown):
    """Markdown renderer with viewmd's code-block override wired in."""

    elements = {
        **Markdown.elements,
        "fence": ViewmdCodeBlock,
        "code_block": ViewmdCodeBlock,
    }


def _make_console(buffer: io.StringIO, *, width: int, color: bool) -> Console:
    return Console(
        file=buffer,
        force_terminal=color,
        no_color=not color,
        color_system="truecolor" if color else None,
        width=width,
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

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
    """Code fence that truncates ordinary lines and leaves mermaid art alone.

    Rich 15's default ``CodeBlock`` hardcodes ``Syntax(..., word_wrap=True,
    padding=1)``, which folds long lines and right-pads to the console width.
    Ordinary fences here keep the original ``padding=1`` (same blank-line/
    left-margin look as before) but set ``word_wrap=False`` so a line longer
    than the render width is hard-cropped to that width instead of folding
    (VIEWMD-0019). Mermaid-rendered fences (tagged with
    ``MERMAID_RENDERED_INFO``) emit raw segments at the diagram's natural
    width with no wrap, pad, or crop (VIEWMD-0018).
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
        yield Syntax(
            code, self.lexer_name, theme=self.theme, word_wrap=False, padding=1
        )


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
    (VIEWMD-0006), and ` ```mermaid ` fences are rendered to box-drawing art (VIEWMD-0014).

    ``crop=False`` on the body print lets mermaid diagram rows wider than ``width`` survive
    intact (VIEWMD-0018); ordinary code fences still hard-crop to ``width`` inside
    ``ViewmdCodeBlock`` (VIEWMD-0019). Paragraphs and other elements still wrap to ``width``
    during render — only the final buffer crop is disabled.
    """
    raw_front_matter, body = split_front_matter(text)
    front_matter = parse_front_matter(raw_front_matter) if raw_front_matter is not None else {}
    if not full_front_matter:
        front_matter = drop_empty(front_matter)
    body = preprocess(body)

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

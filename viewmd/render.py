"""Render Markdown text to an ANSI string using Rich."""

import io

from rich import box
from rich.console import Console
from rich.markdown import Markdown
from rich.markup import escape
from rich.rule import Rule
from rich.table import Table

from viewmd.frontmatter import drop_empty, parse_front_matter, split_front_matter
from viewmd.preprocessors import preprocess


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
    console.print(Markdown(body, code_theme="monokai"))
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

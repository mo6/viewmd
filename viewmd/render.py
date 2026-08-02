"""Render Markdown text to an ANSI string using Rich."""

import io

from rich import box
from rich.console import Console
from rich.markdown import Markdown
from rich.rule import Rule
from rich.table import Table

from viewmd.frontmatter import drop_empty, parse_front_matter, split_front_matter
from viewmd.wikilinks import rewrite_wikilinks


def render_markdown(text: str, *, width: int, color: bool, full_front_matter: bool = False) -> str:
    """Render `text` to an ANSI string, `width` columns wide.

    Rendering is pure (writes to an in-memory buffer, never real stdout) so callers decide
    separately whether/how to display the result (see pager.py).

    A leading YAML-style front-matter block (`--- ... ---`) renders as a table, followed by a
    divider, ahead of the rendered document body (VIEWMD-0004). A file with no front matter, an
    unterminated `---` block, or a front-matter block that parses to no pairs, renders unchanged.
    Fields with an empty value are omitted from the table unless `full_front_matter` is True
    (VIEWMD-0005). Obsidian-style ``[[wikilinks]]`` in the body are rewritten to ordinary
    Markdown links before Rich sees them, so they pick up the same ``markdown.link_url``
    highlight (VIEWMD-0006).
    """
    raw_front_matter, body = split_front_matter(text)
    front_matter = parse_front_matter(raw_front_matter) if raw_front_matter is not None else {}
    if not full_front_matter:
        front_matter = drop_empty(front_matter)
    body = rewrite_wikilinks(body)

    buffer = io.StringIO()
    console = Console(
        file=buffer,
        force_terminal=color,
        no_color=not color,
        color_system="truecolor" if color else None,
        width=width,
        highlight=False,
    )
    if front_matter:
        console.print(_front_matter_table(front_matter))
        # A double-line rule, distinct from Markdown's own "-" horizontal rule, so a reader never
        # mistakes this divider for document content.
        console.print(Rule(characters="═", style="dim"))
    console.print(Markdown(body, code_theme="monokai"))
    return buffer.getvalue()


def _front_matter_table(data: dict[str, str]) -> Table:
    table = Table(show_header=True, header_style="bold cyan", box=box.ROUNDED, expand=False)
    table.add_column("Field", style="cyan", no_wrap=True)
    table.add_column("Value")
    for key, value in data.items():
        table.add_row(key, value)
    return table

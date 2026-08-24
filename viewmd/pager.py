"""Decide whether to page rendered output, and do it.

VIEWMD-0072: viewmd never spawns an external pager -- no `less` default, no `$PAGER` override,
no `subprocess` call anywhere in this module. Every paged case (a single Markdown document, a
bare directory listing, a multi-file concatenation) owns the terminal directly via
`viewmd.interactive_pager`, finishing what VIEWMD-0007 started only for the single-document case.
`--no-pager`/non-terminal output is unaffected by any of this: each `display_*` function below
still just prints the plain already-rendered bytes in that case, identical to before this issue.
"""

import sys

from viewmd.render import render_directory_listing, render_markdown, render_multi_file


def should_page(no_pager_flag: bool) -> bool:
    return not no_pager_flag and sys.stdout.isatty()


def display_document(
    text: str,
    name: str,
    *,
    no_pager: bool,
    width: int,
    color: bool,
    full_front_matter: bool = False,
    toc: bool = True,
    theme: str = "dark",
) -> None:
    """Page a single Markdown document, `text` being its raw (unrendered) source -- the
    interactive pager needs that itself, to derive its plain-render twin and heading outline
    (`viewmd.interactive_pager._load`).
    """
    if not should_page(no_pager):
        print(
            render_markdown(text, width=width, color=color, full_front_matter=full_front_matter,
                            toc=toc, theme=theme),
            end="",
        )
        return

    from viewmd.interactive_pager import run

    run(text, name, width=width, color=color, full_front_matter=full_front_matter, toc=toc,
       theme=theme)


def display_directory_listing(
    dir_path: str,
    *,
    no_pager: bool,
    width: int,
    directory_width: int,
    color: bool,
    depth: int = 1,
    theme: str = "dark",
) -> None:
    """Page a bare directory listing (VIEWMD-0065, no `_Index.md` note), interactively via
    `viewmd.interactive_pager.run_directory_listing` (VIEWMD-0072) when paging applies. `depth`
    (VIEWMD-0089) is the single-path CLI's own `--depth`; multi-file concatenation has no
    equivalent parameter (see `display_multi_file`/`render_multi_file`, unaffected by this
    issue).

    Two widths (VIEWMD-0089, fixing a bug where a `.md` file clicked open from within a directory
    listing used to inherit the listing's own full-width baseline): `directory_width` is the
    listing table's own width (VIEWMD-0071's default-to-full-terminal-width value), used for both
    the non-interactive fallback print below and the listing itself in the interactive path;
    `width` is a plain document's own natural default width, threaded through to
    `run_directory_listing` for when a click opens a `.md` file rather than a subdirectory.
    `theme` (VIEWMD-0091) picks the listing table's own accent color."""
    if not should_page(no_pager):
        print(
            render_directory_listing(
                dir_path, width=directory_width, color=color, depth=depth, theme=theme
            ),
            end="",
        )
        return

    from viewmd.interactive_pager import run_directory_listing

    run_directory_listing(
        dir_path, width=width, directory_width=directory_width, color=color, depth=depth,
        theme=theme,
    )


def display_multi_file(
    entries: list[tuple[str, str | None]],
    *,
    no_pager: bool,
    width: int,
    directory_width: int,
    color: bool,
    full_front_matter: bool,
    toc: bool,
    theme: str = "dark",
) -> None:
    """Page a multi-file concatenation (two or more `path` arguments), interactively via
    `viewmd.interactive_pager.run_multi_file` (VIEWMD-0072) when paging applies. `entries` is
    `(display_path, text)` per already-resolved path -- see `viewmd.render.render_multi_file`."""
    if not should_page(no_pager):
        print(
            render_multi_file(entries, width=width, directory_width=directory_width, color=color,
                              full_front_matter=full_front_matter, toc=toc, theme=theme),
            end="",
        )
        return

    from viewmd.interactive_pager import run_multi_file

    run_multi_file(entries, width=width, directory_width=directory_width, color=color,
                   full_front_matter=full_front_matter, toc=toc, theme=theme)

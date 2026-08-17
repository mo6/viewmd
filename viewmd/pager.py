"""Decide whether to page rendered output, and do it.

`display()` (multi-file concatenations and directory listings, see `__main__.py`) is unchanged by
VIEWMD-0007: still an already-rendered ANSI string, still `less` by default, still a plain
`$PAGER` override. A single Markdown document -- the overwhelmingly common case, and the only one
with a heading outline for a ToC popup/search to act on -- goes through `display_document()`
instead, which owns viewmd's own interactive pager (`viewmd/interactive_pager.py`) by default,
still deferring to an explicit `$PAGER` override unchanged (VIEWMD-0007's Non-goals)."""

import os
import shlex
import subprocess
import sys

from viewmd.render import render_markdown

# -S (chop long lines) so mermaid diagrams wider than the terminal stay on one
# row inside less instead of soft-wrapping and destroying the 2D art
# (VIEWMD-0018). --mouse enables wheel/trackpad scrolling despite -X disabling
# the alternate screen buffer that terminals otherwise rely on for that
# (VIEWMD-0067). Override via $PAGER if soft-wrap or mouse scroll is unwanted.
DEFAULT_PAGER = ["less", "-R", "-F", "-X", "-S", "--mouse"]


def should_page(no_pager_flag: bool) -> bool:
    return not no_pager_flag and sys.stdout.isatty()


def _pager_command() -> list[str]:
    env_pager = os.environ.get("PAGER", "").strip()
    return shlex.split(env_pager) if env_pager else DEFAULT_PAGER


def display(text: str, *, no_pager: bool) -> None:
    if not should_page(no_pager):
        print(text, end="")
        return

    cmd = _pager_command()
    try:
        subprocess.run(cmd, input=text.encode(), check=False)  # noqa: S603
    except (BrokenPipeError, FileNotFoundError):
        print(text, end="")


def display_document(
    text: str,
    name: str,
    *,
    no_pager: bool,
    width: int,
    color: bool,
    full_front_matter: bool = False,
    toc: bool = True,
) -> None:
    """Page a single Markdown document, `text` being its raw (unrendered) source -- the
    interactive pager needs that itself, to derive its plain-render twin and heading outline
    (`viewmd.interactive_pager._load`), not just the one ANSI string `display()` takes.

    `--no-pager`/non-terminal output renders and prints exactly like `display()` would (requirement
    8) -- one `render_markdown` call, identical bytes either way. An explicit `$PAGER` still
    delegates to that external pager unchanged (VIEWMD-0007's Non-goals: a reader who's
    deliberately chosen a different pager shouldn't lose it). Otherwise, viewmd owns the terminal
    directly (`viewmd.interactive_pager.run`) instead of spawning `less` -- this is the one thing
    VIEWMD-0007 actually changes about the *default* (no-`$PAGER`-set) behavior.
    """
    if not should_page(no_pager):
        print(
            render_markdown(text, width=width, color=color, full_front_matter=full_front_matter,
                            toc=toc),
            end="",
        )
        return

    env_pager = os.environ.get("PAGER", "").strip()
    if env_pager:
        ansi_text = render_markdown(text, width=width, color=color,
                                    full_front_matter=full_front_matter, toc=toc)
        try:
            subprocess.run(shlex.split(env_pager), input=ansi_text.encode(), check=False)  # noqa: S603
        except (BrokenPipeError, FileNotFoundError):
            print(ansi_text, end="")
        return

    from viewmd.interactive_pager import run

    run(text, name, width=width, color=color, full_front_matter=full_front_matter, toc=toc)

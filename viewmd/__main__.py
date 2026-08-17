"""Entry point: `python -m viewmd`.

Kept thin: parses arguments and reads input, hands rendering to render.py and display to
pager.py. Errors from bad input print `viewmd: <message>` to stderr and return 1, never a raw
traceback.
"""

import argparse
import os
import shutil
import sys

from viewmd import __version__
from viewmd.config import ConfigError, coalesce, read_config

# A common prose line-length standard; the render width default, capped further by a narrower
# terminal. --width overrides it, either to an exact column count or to "full" (VIEWMD-0003).
DEFAULT_MAX_WIDTH = 100


def _width_arg(value: str) -> str:
    """argparse type for --width: the literal 'full', or a positive integer as a string.

    Kept as a string here (not converted to int) so _resolve_width can treat 'full' and a numeric
    override uniformly without argparse's type system needing a union return type.
    """
    if value == "full":
        return value
    if not value.lstrip("-").isdigit() or int(value) <= 0:
        raise argparse.ArgumentTypeError(
            f"invalid width {value!r}: must be a positive integer or 'full'"
        )
    return value


def _resolve_width(width_arg: str | None, terminal_width: int) -> int:
    if width_arg is None:
        return min(DEFAULT_MAX_WIDTH, terminal_width)
    if width_arg == "full":
        return terminal_width
    return int(width_arg)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="viewmd", description="View a Markdown file in the terminal, paged interactively."
    )
    parser.add_argument("--version", action="version", version=f"viewmd {__version__}")
    parser.add_argument("path", nargs="*", default=["-"],
                        help="Markdown file(s) to render; '-' or omitted reads stdin")
    parser.add_argument("--no-pager", action="store_true",
                        help="print to stdout, never invoke a pager")
    # default=None (not "auto") so an omitted --color can fall through to the config file
    # rather than looking identical to an explicit `--color auto` (VIEWMD-0061).
    parser.add_argument("--color", choices=["auto", "always", "never"], default=None,
                        help="when to emit ANSI color (default: auto)")
    parser.add_argument("--width", type=_width_arg, default=None,
                        help=f"render width in columns, or 'full' for the full terminal width "
                             f"(default: min({DEFAULT_MAX_WIDTH}, detected terminal width))")
    # BooleanOptionalAction (not store_true) so `--no-full-front-matter` can override a
    # config-file `full_front_matter = true`; default=None means "flag omitted."
    parser.add_argument("--full-front-matter", action=argparse.BooleanOptionalAction, default=None,
                        help="show every front-matter field, including empty ones "
                             "(default: empty fields are omitted)")
    # BooleanOptionalAction so `--no-toc` turns the default-on ToC off, and `--toc`
    # can override a config-file `toc = false` (VIEWMD-0062).
    parser.add_argument("--toc", action=argparse.BooleanOptionalAction, default=None,
                        help="render a table of contents from h1/h2/h3 headings "
                             "(default: on; omitted when the document has fewer than two)")
    parser.add_argument("--config", metavar="PATH", default=None,
                        help="read configuration from PATH instead of "
                             "$XDG_CONFIG_HOME/viewmd/config (or ~/.config/viewmd/config)")
    args = parser.parse_args(argv)
    paths = args.path

    if "-" in paths and len(paths) > 1:
        print("viewmd: cannot mix stdin ('-') with file arguments", file=sys.stderr)
        return 1

    try:
        cfg = read_config(args.config)
    except ConfigError as e:
        print(f"viewmd: {e}", file=sys.stderr)
        return 1

    color = _resolve_color(coalesce(args.color, cfg.color, "auto"))
    width = _resolve_width(coalesce(args.width, cfg.width), shutil.get_terminal_size().columns)
    full_front_matter = coalesce(args.full_front_matter, cfg.full_front_matter, False)
    toc = coalesce(args.toc, cfg.toc, True)

    # A single path renders exactly as before VIEWMD-0013 -- no heading or divider added -- so
    # existing single-file output stays byte-for-byte identical. Paged interactively (VIEWMD-0007)
    # when it resolves to one real document (a plain file, stdin, or a directory's index file,
    # VIEWMD-0065) rather than a synthetic directory-listing table, which has no single document
    # for a heading outline/search to act on.
    if len(paths) == 1:
        path = paths[0]
        try:
            resolved = _resolve_document(path)
        except OSError as e:
            print(f"viewmd: cannot read {path}: {e.strerror}", file=sys.stderr)
            return 1
        except UnicodeDecodeError as e:
            print(f"viewmd: {path}: not valid UTF-8 ({e})", file=sys.stderr)
            return 1

        if resolved is not None:
            markdown_text, name = resolved
            from viewmd.pager import display_document
            display_document(markdown_text, name, no_pager=args.no_pager, width=width,
                             color=color, full_front_matter=full_front_matter, toc=toc)
            return 0

        from viewmd.render import render_directory_listing
        ansi_text = render_directory_listing(path, width=width, color=color)
        from viewmd.pager import display
        display(ansi_text, no_pager=args.no_pager)
        return 0

    from viewmd.render import render_divider, render_file_heading

    had_error = False
    parts: list[str] = []
    for path in paths:
        try:
            ansi_text = _render_path(path, width=width, color=color,
                                     full_front_matter=full_front_matter, toc=toc)
        except OSError as e:
            print(f"viewmd: cannot read {path}: {e.strerror}", file=sys.stderr)
            had_error = True
            continue
        except UnicodeDecodeError as e:
            print(f"viewmd: {path}: not valid UTF-8 ({e})", file=sys.stderr)
            had_error = True
            continue

        if parts:
            parts.append(render_divider(width=width, color=color))
        parts.append(render_file_heading(path, width=width, color=color))
        parts.append(ansi_text)

    from viewmd.pager import display
    display("".join(parts), no_pager=args.no_pager)
    return 1 if had_error else 0


def _render_path(path: str, *, width: int, color: bool, full_front_matter: bool,
                 toc: bool) -> str:
    """Resolve `path` to its rendered ANSI text.

    A plain file (or '-' for stdin) renders as Markdown directly. A directory looks up
    `viewmd.render.INDEX_FILENAME` inside it and renders that file if present (VIEWMD-0065);
    otherwise it renders a table-of-contents listing of the directory's own entries instead of
    raising `IsADirectoryError` the way a bare `open()` would. Raises `OSError`/
    `UnicodeDecodeError` the same as a direct read, for the caller's existing error handling.
    """
    from viewmd.render import INDEX_FILENAME, render_directory_listing, render_markdown

    if path != "-" and os.path.isdir(path):
        # `INDEX_FILENAME in os.listdir(path)` rather than `os.path.isfile()` on the joined path:
        # the latter matches case-insensitively on the default macOS/Windows filesystems, but
        # requirement 2 (VIEWMD-0065) is a case-sensitive match on the exact name.
        index_path = os.path.join(path, INDEX_FILENAME)
        if INDEX_FILENAME in os.listdir(path) and os.path.isfile(index_path):
            text = _read_input(index_path)
            return render_markdown(text, width=width, color=color,
                                   full_front_matter=full_front_matter, toc=toc)
        return render_directory_listing(path, width=width, color=color)

    text = _read_input(path)
    return render_markdown(text, width=width, color=color,
                           full_front_matter=full_front_matter, toc=toc)


def _resolve_document(path: str) -> tuple[str, str] | None:
    """Returns `(source_markdown_text, display_name)` for `path` when it resolves to one real
    document -- a plain file, stdin, or a directory's index file (VIEWMD-0065) -- or `None` for a
    bare directory listing, which is a synthesized table, not a document with headings/content of
    its own for `viewmd.pager.display_document`'s interactive pager to page. Mirrors
    `_render_path`'s own resolution logic exactly, but returns the raw source text instead of an
    already-rendered string -- the interactive pager needs to derive its own plain-render twin and
    heading outline from that itself (`viewmd.interactive_pager._load`). Raises `OSError`/
    `UnicodeDecodeError` the same as a direct read, for the caller's existing error handling.
    """
    from viewmd.render import INDEX_FILENAME

    if path != "-" and os.path.isdir(path):
        index_path = os.path.join(path, INDEX_FILENAME)
        if INDEX_FILENAME in os.listdir(path) and os.path.isfile(index_path):
            return _read_input(index_path), index_path
        return None
    return _read_input(path), path


def _read_input(path: str) -> str:
    if path == "-":
        return sys.stdin.read()
    with open(path, encoding="utf-8") as f:
        return f.read()


def _resolve_color(choice: str) -> bool:
    if choice == "always":
        return True
    if choice == "never":
        return False
    # auto: NO_COLOR (https://no-color.org) wins over tty detection when set to anything non-empty.
    if os.environ.get("NO_COLOR"):
        return False
    return sys.stdout.isatty()


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        # Ctrl+C while reading stdin or paging -- exit quietly with the
        # conventional SIGINT status instead of a raw traceback.
        sys.exit(130)

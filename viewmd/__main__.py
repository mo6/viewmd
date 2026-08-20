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

# Upper bound for --depth (VIEWMD-0089 requirement 4): a directory-listing table of entries is a
# quick-orientation view of a small vault, not a general-purpose `find -maxdepth`, and an
# unreasonably large depth against a very large tree would both flood the terminal and take a
# while to walk. A depth beyond this is silently capped (with a warning) rather than rejected, so
# a config-file or muscle-memory `--depth 999` still does something useful instead of erroring.
MAX_DEPTH = 10


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


def _depth_arg(value: str) -> int:
    """argparse type for --depth: a positive integer, as an int (unlike `_width_arg`, --depth has
    no 'full'-style literal alternative to keep as a string)."""
    if not value.isdigit() or int(value) <= 0:
        raise argparse.ArgumentTypeError(f"invalid depth {value!r}: must be a positive integer")
    return int(value)


def _resolve_depth(depth: int | None, *, max_depth: int = MAX_DEPTH) -> int:
    """Resolve the effective --depth: `1` (today's original behavior) when omitted, otherwise the
    requested depth capped at `max_depth` with a warning printed to stderr (VIEWMD-0089
    requirement 4) -- never a hard error, so an over-large value still renders something."""
    if depth is None:
        return 1
    if depth > max_depth:
        print(
            f"viewmd: --depth {depth} capped to {max_depth}",
            file=sys.stderr,
        )
        return max_depth
    return depth


def _resolve_width(width_arg: str | None, terminal_width: int, *,
                   default_max_width: int = DEFAULT_MAX_WIDTH) -> int:
    if width_arg is None:
        return min(default_max_width, terminal_width)
    if width_arg == "full":
        return terminal_width
    return int(width_arg)


def build_parser() -> argparse.ArgumentParser:
    """Builds viewmd's `ArgumentParser`, the single source of truth for its CLI flag surface.

    Kept as its own function (rather than inlined in `main`) so `tools/completions.py` can
    import and introspect the exact same parser `main` parses with, generating the checked-in
    bash/zsh/fish completion scripts from it directly instead of a hand-maintained duplicate
    flag list (VIEWMD-0087).
    """
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
    parser.add_argument("--depth", type=_depth_arg, default=None, metavar="N",
                        help="for a bare directory listing, list subdirectories up to N levels "
                             f"deep, indented (default: 1, today's behavior; capped at "
                             f"{MAX_DEPTH}); has no effect on a directory with an index file, a "
                             "single document, or multi-file concatenation")
    parser.add_argument("--config", metavar="PATH", default=None,
                        help="read configuration from PATH instead of "
                             "$XDG_CONFIG_HOME/viewmd/config (or ~/.config/viewmd/config)")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
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
    terminal_width = shutil.get_terminal_size().columns
    width_arg = coalesce(args.width, cfg.width)
    width = _resolve_width(width_arg, terminal_width)
    # A bare directory listing (no --width given, VIEWMD-0071) defaults to the full terminal
    # width rather than the prose cap: it's a table of entries, not prose to keep line-length-
    # readable, and the cap only truncates columns a wide terminal has room to show. An explicit
    # --width/config width still applies exactly as it does to documents.
    directory_width = _resolve_width(width_arg, terminal_width, default_max_width=terminal_width)
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

        # --depth (VIEWMD-0089) is resolved here, not up front with the other flags: it only
        # applies to a bare directory listing (never a single document or multi-file
        # concatenation, see its own Non-goals), and `_resolve_depth` prints a capping warning to
        # stderr when over `MAX_DEPTH` -- resolving it unconditionally for every invocation would
        # print that warning even for a `--depth` value that goes on to have no effect at all.
        from viewmd.pager import display_directory_listing
        depth = _resolve_depth(coalesce(args.depth, cfg.depth))
        display_directory_listing(path, no_pager=args.no_pager, width=width,
                                  directory_width=directory_width, color=color, depth=depth)
        return 0

    had_error = False
    entries: list[tuple[str, str | None]] = []
    for path in paths:
        try:
            resolved = _resolve_document(path)
        except OSError as e:
            print(f"viewmd: cannot read {path}: {e.strerror}", file=sys.stderr)
            had_error = True
            continue
        except UnicodeDecodeError as e:
            print(f"viewmd: {path}: not valid UTF-8 ({e})", file=sys.stderr)
            had_error = True
            continue

        if resolved is not None:
            text, _name = resolved
            # `path` (the original CLI argument), not `_name` (the resolved index-file path for a
            # directory's `_Index.md` note, VIEWMD-0065) -- render_file_heading names the file
            # heading after what the reader actually typed, matching pre-VIEWMD-0072 behavior.
            entries.append((path, text))
        else:
            entries.append((path, None))

    from viewmd.pager import display_multi_file
    display_multi_file(entries, no_pager=args.no_pager, width=width,
                       directory_width=directory_width, color=color,
                       full_front_matter=full_front_matter, toc=toc)
    return 1 if had_error else 0


def _resolve_document(path: str) -> tuple[str, str] | None:
    """Returns `(source_markdown_text, display_name)` for `path` when it resolves to one real
    document -- a plain file, stdin, or a directory's index file (VIEWMD-0065) -- or `None` for a
    bare directory listing, which is a synthesized table, not a document with headings/content of
    its own for `viewmd.pager.display_document`'s interactive pager to page. Used for both the
    single-path and multi-path cases -- the multi-path loop keeps the original CLI-argument
    `path` as its own display name rather than this function's resolved index-file path (see its
    call site). Raises `OSError`/`UnicodeDecodeError` the same as a direct read, for the caller's
    existing error handling.
    """
    if path != "-" and os.path.isdir(path):
        index_path = _find_index_path(path)
        if index_path is not None:
            return _read_input(index_path), index_path
        return None
    return _read_input(path), path


def _find_index_path(dir_path: str) -> str | None:
    """Returns the path to `dir_path`'s index file -- the first of `viewmd.render.INDEX_FILENAMES`
    present, in priority order -- or `None` if it has none (VIEWMD-0065, VIEWMD-0074).

    Checks `os.listdir()` membership rather than `os.path.isfile()` on the joined path: the
    latter matches case-insensitively on the default macOS/Windows filesystems, but the match
    here must be case-sensitive and exact (VIEWMD-0065 requirement 2).
    """
    from viewmd.render import INDEX_FILENAMES

    entries = os.listdir(dir_path)
    for name in INDEX_FILENAMES:
        candidate = os.path.join(dir_path, name)
        if name in entries and os.path.isfile(candidate):
            return candidate
    return None


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

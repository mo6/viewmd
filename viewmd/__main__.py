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
        prog="viewmd", description="View a Markdown file in the terminal, paged into less."
    )
    parser.add_argument("--version", action="version", version=f"viewmd {__version__}")
    parser.add_argument("path", nargs="*", default=["-"],
                        help="Markdown file(s) to render; '-' or omitted reads stdin")
    parser.add_argument("--no-pager", action="store_true",
                        help="print to stdout, never invoke a pager")
    parser.add_argument("--color", choices=["auto", "always", "never"], default="auto",
                        help="when to emit ANSI color (default: auto)")
    parser.add_argument("--width", type=_width_arg, default=None,
                        help=f"render width in columns, or 'full' for the full terminal width "
                             f"(default: min({DEFAULT_MAX_WIDTH}, detected terminal width))")
    parser.add_argument("--full-front-matter", action="store_true",
                        help="show every front-matter field, including empty ones "
                             "(default: empty fields are omitted)")
    args = parser.parse_args(argv)
    paths = args.path

    if "-" in paths and len(paths) > 1:
        print("viewmd: cannot mix stdin ('-') with file arguments", file=sys.stderr)
        return 1

    color = _resolve_color(args.color)
    width = _resolve_width(args.width, shutil.get_terminal_size().columns)

    from viewmd.render import render_markdown

    # A single path renders exactly as before VIEWMD-0013 -- no heading or divider added -- so
    # existing single-file output stays byte-for-byte identical.
    if len(paths) == 1:
        path = paths[0]
        try:
            text = _read_input(path)
        except OSError as e:
            print(f"viewmd: cannot read {path}: {e.strerror}", file=sys.stderr)
            return 1
        except UnicodeDecodeError as e:
            print(f"viewmd: {path}: not valid UTF-8 ({e})", file=sys.stderr)
            return 1

        ansi_text = render_markdown(text, width=width, color=color,
                                    full_front_matter=args.full_front_matter)

        from viewmd.pager import display
        display(ansi_text, no_pager=args.no_pager)
        return 0

    from viewmd.render import render_divider, render_file_heading

    had_error = False
    parts: list[str] = []
    for path in paths:
        try:
            text = _read_input(path)
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
        parts.append(render_markdown(text, width=width, color=color,
                                     full_front_matter=args.full_front_matter))

    from viewmd.pager import display
    display("".join(parts), no_pager=args.no_pager)
    return 1 if had_error else 0


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

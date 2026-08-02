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


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="viewmd", description="View a Markdown file in the terminal, paged into less."
    )
    parser.add_argument("--version", action="version", version=f"viewmd {__version__}")
    parser.add_argument("path", nargs="?", default="-",
                        help="Markdown file to render; '-' or omitted reads stdin")
    parser.add_argument("--no-pager", action="store_true",
                        help="print to stdout, never invoke a pager")
    parser.add_argument("--color", choices=["auto", "always", "never"], default="auto",
                        help="when to emit ANSI color (default: auto)")
    parser.add_argument("--width", type=int, default=None,
                        help="render width in columns (default: detected terminal width)")
    args = parser.parse_args(argv)

    try:
        text = _read_input(args.path)
    except OSError as e:
        print(f"viewmd: cannot read {args.path}: {e.strerror}", file=sys.stderr)
        return 1
    except UnicodeDecodeError as e:
        print(f"viewmd: {args.path}: not valid UTF-8 ({e})", file=sys.stderr)
        return 1

    color = _resolve_color(args.color)
    width = args.width if args.width is not None else shutil.get_terminal_size().columns

    from viewmd.render import render_markdown
    ansi_text = render_markdown(text, width=width, color=color)

    from viewmd.pager import display
    display(ansi_text, no_pager=args.no_pager)
    return 0


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
    sys.exit(main())

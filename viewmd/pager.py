"""Decide whether to page rendered output, and do it."""

import os
import shlex
import subprocess
import sys

DEFAULT_PAGER = ["less", "-R", "-F", "-X"]


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

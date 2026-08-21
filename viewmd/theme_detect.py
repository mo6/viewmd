"""Detect a terminal's actual background color via an OSC 11 query (VIEWMD-0105).

Used only when `--theme auto` (directly, or via a config-file `theme = auto`) is what actually
resolves after `viewmd.config.coalesce` -- `viewmd/__main__.py`'s theme resolution calls
`detect_terminal_theme()` exactly once, only in that case, so `--theme dark`/`--theme light`/an
omitted `--theme` never touch this module at all (requirement 7: zero added latency for those).

Mechanics (design notes in `issues/archive/VIEWMD-0105-*.md`, ported from the maintainer's own
hand-verified probe script, not re-derived from scratch): write `\\x1b]11;?\\x07` (OSC 11,
"what is your background color?") to `/dev/tty` opened directly -- not `sys.stdin`, which may be
a pipe (VIEWMD-0105 requirement 3a, matching `interactive_pager.run()`'s own tty-vs-stdin
precedent) -- with the tty put in raw mode so the terminal's escape-sequence reply arrives
unmangled by line discipline, then read the reply with a short `select`-bounded timeout. A
terminal or multiplexer that never answers (tmux/screen without OSC passthrough configured is a
known real case, documented in README.md) times out rather than hanging forever. Every exit path
-- success, timeout, a malformed reply, or an `OSError` opening/reading `/dev/tty` -- restores the
tty's original termios settings before returning and falls back to `"dark"` (today's existing
default) on any failure; this function itself never raises.
"""

import os
import re
import select
import sys
import termios
import time
import tty

# A few hundred milliseconds (requirement 4): long enough for a real terminal's near-instant
# reply to arrive, short enough that a non-answering multiplexer doesn't noticeably delay startup.
_READ_TIMEOUT_SECONDS = 0.3

_OSC11_QUERY = b"\x1b]11;?\x07"

# `rgb:RRRR/GGGG/BBBB`-style reply body, 2 or 4 hex digits per channel (the two forms real
# terminals actually send -- see the dark/light examples hand-verified in the issue's Motivation).
# `.search`, not `.match`/`.fullmatch`, since the full reply also carries the leading
# `\x1b]11;` prefix and a trailing BEL/ST terminator this doesn't need to match explicitly.
_REPLY_RE = re.compile(rb"rgb:([0-9a-fA-F]{2,4})/([0-9a-fA-F]{2,4})/([0-9a-fA-F]{2,4})")

# Safety cap on how many bytes of reply to accumulate -- a real OSC 11 reply is a few dozen bytes;
# this just bounds a pathological/garbled stream rather than growing `buf` unboundedly.
_MAX_REPLY_BYTES = 256


def detect_terminal_theme() -> str:
    """Return `"light"` or `"dark"`, querying the real terminal background when possible.

    Falls back to `"dark"` (today's existing default) on any failure at all: stdout is not a
    tty, `/dev/tty` can't be opened or read (`OSError`), the terminal never answers within the
    timeout, or the reply doesn't parse -- never raises, never blocks longer than
    `_READ_TIMEOUT_SECONDS`.
    """
    # requirement 3: no interactive terminal to query at all when stdout isn't one (--no-pager,
    # piped output) -- matches the existing --color auto tty-detection precedent, and importantly
    # skips opening /dev/tty entirely rather than opening it and then failing to get a reply.
    if not sys.stdout.isatty():
        return "dark"

    try:
        tty_fd = os.open("/dev/tty", os.O_RDWR)
    except OSError:
        return "dark"

    try:
        old_settings = termios.tcgetattr(tty_fd)
    except termios.error:
        os.close(tty_fd)
        return "dark"

    try:
        tty.setraw(tty_fd)
        os.write(tty_fd, _OSC11_QUERY)
        reply = _read_reply(tty_fd)
    except (OSError, termios.error):
        # tty.setraw itself calls termios.tcsetattr under the hood, so it can raise
        # termios.error (not an OSError subclass) rather than OSError -- caught here too, so a
        # raw-mode failure falls back to "dark" exactly like a read/write OSError does, instead
        # of propagating past the termios-restore `finally` below and crashing the render.
        reply = b""
    finally:
        # Restored on every path -- success, timeout/empty reply, or the OSError above -- before
        # this function returns, per requirement 5 (a crash or early return must not leave the
        # user's shell in raw mode).
        termios.tcsetattr(tty_fd, termios.TCSADRAIN, old_settings)
        os.close(tty_fd)

    rgb = _parse_osc11_reply(reply)
    if rgb is None:
        return "dark"
    return _classify_luminance(*rgb)


def _read_reply(tty_fd: int, *, timeout: float = _READ_TIMEOUT_SECONDS) -> bytes:
    """Read the terminal's OSC 11 reply, bounded by `timeout` total (not per-chunk -- a slow
    trickle of bytes can't extend the wait past the original deadline). Stops early once a
    terminator (BEL `\\x07` or ST `\\x1b\\\\`) is seen, since a well-behaved terminal's reply ends
    there and there's nothing further worth waiting for. Returns whatever was read (possibly
    empty, e.g. on a plain timeout) -- never raises on a timeout, only lets a genuine `OSError`
    from `os.read` propagate to `detect_terminal_theme`'s own `except OSError` above.
    """
    deadline = time.monotonic() + timeout
    buf = b""
    while True:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            break
        ready, _, _ = select.select([tty_fd], [], [], remaining)
        if not ready:
            break
        chunk = os.read(tty_fd, 1024)
        if not chunk:
            break
        buf += chunk
        if b"\x07" in buf or b"\x1b\\" in buf:
            break
        if len(buf) >= _MAX_REPLY_BYTES:
            break
    return buf


def _parse_osc11_reply(reply: bytes) -> tuple[int, int, int] | None:
    """Parse an `rgb:RRRR/GGGG/BBBB`-style reply body into a normalized `(r, g, b)` 0-255 tuple,
    or `None` when `reply` doesn't contain one (empty/timeout, or a malformed/unrecognized
    response)."""
    match = _REPLY_RE.search(reply)
    if match is None:
        return None
    r, g, b = (_normalize_channel(group) for group in match.groups())
    return (r, g, b)


def _normalize_channel(hex_digits: bytes) -> int:
    """Normalize one `RRRR`/`RR`-style hex channel to 0-255, per requirement 6. A terminal
    reports each channel as however many bits its own color depth uses (commonly 8-bit `RR` or
    16-bit `RRRR`); scaling by the digit count's own max value handles both uniformly rather than
    hardcoding just the two documented-common cases."""
    text = hex_digits.decode("ascii")
    value = int(text, 16)
    max_value = (16 ** len(text)) - 1
    return round(value * 255 / max_value)


def _classify_luminance(r: int, g: int, b: int) -> str:
    """Relative luminance (`0.299r + 0.587g + 0.114b`, the same formula the maintainer's own
    verification probe used) -- above 127 reads as `"light"`, otherwise `"dark"` (requirement 6;
    the exact threshold is an implementation detail, not specified more precisely by the issue)."""
    luminance = 0.299 * r + 0.587 * g + 0.114 * b
    return "light" if luminance > 127 else "dark"

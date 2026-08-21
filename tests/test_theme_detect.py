"""Tests for viewmd/theme_detect.py (VIEWMD-0105): the OSC 11 background-color probe used only
by `--theme auto`. Covers the pure parsing/classification helpers directly, then
`detect_terminal_theme()`'s own tty-detection/timeout/termios-restore/fallback behavior via
mocks -- a real terminal round-trip (the maintainer's own hand-verified probe) is not something a
non-interactive test run can exercise; see the issue's Peer review section for what still needs a
real-terminal manual check.
"""

import termios

import pytest

from viewmd import theme_detect

# ---- _parse_osc11_reply / _normalize_channel --------------------------------------------------

def test_parse_reply_four_digit_hex_channels():
    # The maintainer's own hand-verified dark-terminal reply (issue Motivation).
    rgb = theme_detect._parse_osc11_reply(b"\x1b]11;rgb:213d/2743/33e7\x07")
    assert rgb == (33, 39, 52)


def test_parse_reply_two_digit_hex_channels():
    rgb = theme_detect._parse_osc11_reply(b"\x1b]11;rgb:ff/80/00\x07")
    assert rgb == (255, 128, 0)


def test_parse_reply_white_four_digit():
    # The maintainer's own hand-verified light-terminal reply (issue Motivation).
    rgb = theme_detect._parse_osc11_reply(b"\x1b]11;rgb:ffff/ffff/ffff\x1b\\")
    assert rgb == (255, 255, 255)


def test_parse_reply_black_two_digit():
    rgb = theme_detect._parse_osc11_reply(b"\x1b]11;rgb:00/00/00\x07")
    assert rgb == (0, 0, 0)


@pytest.mark.parametrize("reply", [
    b"",
    b"\x1b]11;not-a-color\x07",
    b"garbage",
])
def test_parse_reply_unparseable_returns_none(reply):
    assert theme_detect._parse_osc11_reply(reply) is None


# ---- _classify_luminance -----------------------------------------------------------------------

def test_classify_luminance_white_is_light():
    assert theme_detect._classify_luminance(255, 255, 255) == "light"


def test_classify_luminance_black_is_dark():
    assert theme_detect._classify_luminance(0, 0, 0) == "dark"


def test_classify_luminance_maintainer_verified_dark_example():
    # rgb:213d/2743/33e7 -> (33, 39, 52), luminance ~38.7 (issue Motivation).
    assert theme_detect._classify_luminance(33, 39, 52) == "dark"


def test_classify_luminance_boundary_at_127_is_dark():
    assert theme_detect._classify_luminance(127, 127, 127) == "dark"


def test_classify_luminance_boundary_above_127_is_light():
    assert theme_detect._classify_luminance(128, 128, 128) == "light"


# ---- detect_terminal_theme ----------------------------------------------------------------------

def test_non_tty_skips_query_entirely(monkeypatch):
    """Requirement 3: stdout not a tty falls back to dark without attempting a query at all --
    asserted here by making os.open raise if it's ever called, not just by checking the result."""
    monkeypatch.setattr(theme_detect.sys.stdout, "isatty", lambda: False)

    def _boom(*a, **k):
        raise AssertionError("/dev/tty must not be opened when stdout is not a tty")

    monkeypatch.setattr(theme_detect.os, "open", _boom)

    assert theme_detect.detect_terminal_theme() == "dark"


def test_oserror_opening_dev_tty_falls_back_to_dark(monkeypatch):
    monkeypatch.setattr(theme_detect.sys.stdout, "isatty", lambda: True)

    def _raise_oserror(*a, **k):
        raise OSError("no such device")

    monkeypatch.setattr(theme_detect.os, "open", _raise_oserror)

    assert theme_detect.detect_terminal_theme() == "dark"


class _FakeTermios:
    """Stands in for the (fd, attrs) shape termios.tcgetattr/tcsetattr pass around -- viewmd
    never inspects the structure itself, only round-trips it, so a sentinel object is enough."""


def _patch_tty_plumbing(monkeypatch, *, reply_bytes=b"", raise_on_read=None):
    """Common mock setup for detect_terminal_theme's happy/timeout/OSError paths: a fake tty fd,
    fake termios get/set (recording tcsetattr calls), a no-op tty.setraw/os.write, and select.select
    plus os.read driven by `reply_bytes`/`raise_on_read`. Returns the list tcsetattr calls land in.
    """
    monkeypatch.setattr(theme_detect.sys.stdout, "isatty", lambda: True)
    monkeypatch.setattr(theme_detect.os, "open", lambda *a, **k: 99)

    original_attrs = _FakeTermios()
    monkeypatch.setattr(theme_detect.termios, "tcgetattr", lambda fd: original_attrs)

    tcsetattr_calls = []
    monkeypatch.setattr(
        theme_detect.termios, "tcsetattr",
        lambda fd, when, attrs: tcsetattr_calls.append((fd, when, attrs)),
    )
    monkeypatch.setattr(theme_detect.tty, "setraw", lambda fd: None)
    monkeypatch.setattr(theme_detect.os, "write", lambda fd, data: len(data))
    monkeypatch.setattr(theme_detect.os, "close", lambda fd: None)

    if raise_on_read is not None:
        def _select_then_raise(*a, **k):
            raise raise_on_read
        monkeypatch.setattr(theme_detect.select, "select", _select_then_raise)
    elif reply_bytes == b"__TIMEOUT__":
        monkeypatch.setattr(theme_detect.select, "select", lambda *a, **k: ([], [], []))
    else:
        state = {"sent": False}

        def _fake_select(rlist, wlist, xlist, timeout):
            if state["sent"]:
                return ([], [], [])
            return (rlist, [], [])

        def _fake_read(fd, n):
            state["sent"] = True
            return reply_bytes

        monkeypatch.setattr(theme_detect.select, "select", _fake_select)
        monkeypatch.setattr(theme_detect.os, "read", _fake_read)

    return tcsetattr_calls, original_attrs


def test_valid_reply_resolves_to_light(monkeypatch):
    tcsetattr_calls, original_attrs = _patch_tty_plumbing(
        monkeypatch, reply_bytes=b"\x1b]11;rgb:ffff/ffff/ffff\x07"
    )

    assert theme_detect.detect_terminal_theme() == "light"
    assert tcsetattr_calls == [(99, termios.TCSADRAIN, original_attrs)]


def test_valid_reply_resolves_to_dark(monkeypatch):
    tcsetattr_calls, original_attrs = _patch_tty_plumbing(
        monkeypatch, reply_bytes=b"\x1b]11;rgb:213d/2743/33e7\x07"
    )

    assert theme_detect.detect_terminal_theme() == "dark"
    assert tcsetattr_calls == [(99, termios.TCSADRAIN, original_attrs)]


def test_timeout_falls_back_to_dark_and_restores_termios(monkeypatch):
    tcsetattr_calls, original_attrs = _patch_tty_plumbing(monkeypatch, reply_bytes=b"__TIMEOUT__")

    assert theme_detect.detect_terminal_theme() == "dark"
    assert tcsetattr_calls == [(99, termios.TCSADRAIN, original_attrs)]


def test_malformed_reply_falls_back_to_dark_and_restores_termios(monkeypatch):
    tcsetattr_calls, original_attrs = _patch_tty_plumbing(
        monkeypatch, reply_bytes=b"\x1b]11;not-a-color\x07"
    )

    assert theme_detect.detect_terminal_theme() == "dark"
    assert tcsetattr_calls == [(99, termios.TCSADRAIN, original_attrs)]


def test_oserror_during_read_falls_back_to_dark_and_restores_termios(monkeypatch):
    tcsetattr_calls, original_attrs = _patch_tty_plumbing(
        monkeypatch, raise_on_read=OSError("i/o error")
    )

    assert theme_detect.detect_terminal_theme() == "dark"
    assert tcsetattr_calls == [(99, termios.TCSADRAIN, original_attrs)]


def test_termios_error_getting_attrs_falls_back_to_dark_without_setting(monkeypatch):
    """tcgetattr itself can fail (e.g. fd isn't a real tty despite os.open succeeding) -- there
    are no original attrs to restore in that case, so tcsetattr must never be called at all."""
    monkeypatch.setattr(theme_detect.sys.stdout, "isatty", lambda: True)
    monkeypatch.setattr(theme_detect.os, "open", lambda *a, **k: 99)
    monkeypatch.setattr(theme_detect.os, "close", lambda fd: None)

    def _raise_termios_error(fd):
        raise termios.error("not a terminal")

    monkeypatch.setattr(theme_detect.termios, "tcgetattr", _raise_termios_error)

    tcsetattr_calls = []
    monkeypatch.setattr(
        theme_detect.termios, "tcsetattr",
        lambda fd, when, attrs: tcsetattr_calls.append((fd, when, attrs)),
    )

    assert theme_detect.detect_terminal_theme() == "dark"
    assert tcsetattr_calls == []


def test_termios_error_from_setraw_falls_back_to_dark_and_restores_termios(monkeypatch):
    """tty.setraw() itself calls termios.tcsetattr under the hood, so it can raise
    termios.error -- not an OSError subclass -- rather than OSError; must still fall back to
    dark and still restore the original settings, not propagate past the restore."""
    monkeypatch.setattr(theme_detect.sys.stdout, "isatty", lambda: True)
    monkeypatch.setattr(theme_detect.os, "open", lambda *a, **k: 99)
    monkeypatch.setattr(theme_detect.os, "close", lambda fd: None)

    original_attrs = _FakeTermios()
    monkeypatch.setattr(theme_detect.termios, "tcgetattr", lambda fd: original_attrs)

    tcsetattr_calls = []
    monkeypatch.setattr(
        theme_detect.termios, "tcsetattr",
        lambda fd, when, attrs: tcsetattr_calls.append((fd, when, attrs)),
    )

    def _raise_termios_error(fd):
        raise termios.error("not a terminal")

    monkeypatch.setattr(theme_detect.tty, "setraw", _raise_termios_error)

    assert theme_detect.detect_terminal_theme() == "dark"
    assert tcsetattr_calls == [(99, termios.TCSADRAIN, original_attrs)]

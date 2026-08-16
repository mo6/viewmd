import subprocess

from viewmd import pager


def test_should_page_true_when_tty_and_no_flag(monkeypatch):
    monkeypatch.setattr(pager.sys.stdout, "isatty", lambda: True)
    assert pager.should_page(no_pager_flag=False) is True


def test_should_page_false_when_no_pager_flag_set(monkeypatch):
    monkeypatch.setattr(pager.sys.stdout, "isatty", lambda: True)
    assert pager.should_page(no_pager_flag=True) is False


def test_should_page_false_when_not_a_tty(monkeypatch):
    monkeypatch.setattr(pager.sys.stdout, "isatty", lambda: False)
    assert pager.should_page(no_pager_flag=False) is False
    assert pager.should_page(no_pager_flag=True) is False


def test_display_prints_directly_when_not_paging(monkeypatch, capsys):
    monkeypatch.setattr(pager.sys.stdout, "isatty", lambda: False)
    pager.display("hello", no_pager=False)
    assert capsys.readouterr().out == "hello"


def test_default_pager_chops_long_lines():
    # VIEWMD-0018: -S so less does not soft-wrap wide mermaid rows.
    assert "-S" in pager.DEFAULT_PAGER


def test_default_pager_enables_mouse_scroll():
    # VIEWMD-0067: --mouse so wheel/trackpad scroll reaches less despite -X.
    assert "--mouse" in pager.DEFAULT_PAGER


def test_display_invokes_pager_when_paging(monkeypatch):
    monkeypatch.setattr(pager.sys.stdout, "isatty", lambda: True)
    calls = []

    def fake_run(cmd, input, check):  # noqa: A002
        calls.append((cmd, input))

    monkeypatch.setattr(subprocess, "run", fake_run)
    pager.display("hello", no_pager=False)
    assert calls == [(pager.DEFAULT_PAGER, b"hello")]


def test_display_respects_pager_env_override(monkeypatch):
    monkeypatch.setattr(pager.sys.stdout, "isatty", lambda: True)
    monkeypatch.setenv("PAGER", "cat -A")
    calls = []

    def fake_run(cmd, input, check):  # noqa: A002
        calls.append((cmd, input))

    monkeypatch.setattr(subprocess, "run", fake_run)
    pager.display("hello", no_pager=False)
    assert calls == [(["cat", "-A"], b"hello")]


def test_display_falls_back_to_print_when_pager_missing(monkeypatch, capsys):
    monkeypatch.setattr(pager.sys.stdout, "isatty", lambda: True)

    def fake_run(cmd, input, check):  # noqa: A002
        raise FileNotFoundError

    monkeypatch.setattr(subprocess, "run", fake_run)
    pager.display("hello", no_pager=False)
    assert capsys.readouterr().out == "hello"

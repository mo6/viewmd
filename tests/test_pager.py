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


def test_pager_module_never_shells_out():
    # VIEWMD-0072: viewmd never spawns an external pager -- no `subprocess` call anywhere in this
    # module (source-level check, since a call could otherwise hide behind a local import) and no
    # `$PAGER` environment variable read.
    import inspect

    source = inspect.getsource(pager)
    assert "import subprocess" not in source
    assert "subprocess.run" not in source
    assert "environ" not in source


# --- display_document (VIEWMD-0007) ---------------------------------------------------------


def test_display_document_prints_directly_when_not_paging(monkeypatch, capsys):
    from viewmd.render import render_markdown

    monkeypatch.setattr(pager.sys.stdout, "isatty", lambda: False)
    text = "# Hello\n\nbody\n"
    pager.display_document(text, "file.md", no_pager=False, width=80, color=False)
    out = capsys.readouterr().out
    assert out == render_markdown(text, width=80, color=False)


def test_display_document_prints_directly_when_no_pager_flag_set(monkeypatch, capsys):
    from viewmd.render import render_markdown

    monkeypatch.setattr(pager.sys.stdout, "isatty", lambda: True)
    text = "# Hello\n\nbody\n"
    pager.display_document(text, "file.md", no_pager=True, width=80, color=False)
    out = capsys.readouterr().out
    assert out == render_markdown(text, width=80, color=False)


def test_display_document_ignores_pager_env_var(monkeypatch):
    # VIEWMD-0072: an explicit $PAGER no longer changes anything -- always the internal pager.
    monkeypatch.setattr(pager.sys.stdout, "isatty", lambda: True)
    monkeypatch.setenv("PAGER", "cat -A")
    calls = []

    def fake_run(text, name, *, width, color, full_front_matter, toc, theme):
        calls.append((text, name, width, color, full_front_matter, toc, theme))

    monkeypatch.setattr("viewmd.interactive_pager.run", fake_run)
    pager.display_document("# Hi\n", "file.md", no_pager=False, width=80, color=True)
    assert calls == [("# Hi\n", "file.md", 80, True, False, True, "dark")]


def test_display_document_uses_interactive_pager_by_default(monkeypatch):
    monkeypatch.setattr(pager.sys.stdout, "isatty", lambda: True)
    monkeypatch.delenv("PAGER", raising=False)
    calls = []

    def fake_run(text, name, *, width, color, full_front_matter, toc, theme):
        calls.append((text, name, width, color, full_front_matter, toc, theme))

    monkeypatch.setattr("viewmd.interactive_pager.run", fake_run)
    pager.display_document(
        "# Hi\n", "file.md", no_pager=False, width=80, color=True,
        full_front_matter=True, toc=False, theme="light",
    )
    assert calls == [("# Hi\n", "file.md", 80, True, True, False, "light")]


# --- display_directory_listing (VIEWMD-0072) ------------------------------------------------


def test_display_directory_listing_prints_directly_when_not_paging(monkeypatch, capsys, tmp_path):
    from viewmd.render import render_directory_listing

    (tmp_path / "a.md").write_text("# A\n")
    monkeypatch.setattr(pager.sys.stdout, "isatty", lambda: False)
    # `directory_width` (60) is what the non-interactive fallback prints at -- `width` (80, the
    # document default) is unused on this path, deliberately different here to prove that
    # (VIEWMD-0089).
    pager.display_directory_listing(
        str(tmp_path), no_pager=False, width=80, directory_width=60, color=False
    )
    out = capsys.readouterr().out
    assert out == render_directory_listing(str(tmp_path), width=60, color=False)


def test_display_directory_listing_uses_interactive_pager_when_paging(monkeypatch, tmp_path):
    monkeypatch.setattr(pager.sys.stdout, "isatty", lambda: True)
    calls = []

    def fake_run(dir_path, *, width, directory_width, color, depth, theme):
        calls.append((dir_path, width, directory_width, color, depth, theme))

    monkeypatch.setattr("viewmd.interactive_pager.run_directory_listing", fake_run)
    pager.display_directory_listing(
        str(tmp_path), no_pager=False, width=80, directory_width=60, color=True
    )
    assert calls == [(str(tmp_path), 80, 60, True, 1, "dark")]


# --- display_multi_file (VIEWMD-0072) --------------------------------------------------------


def test_display_multi_file_prints_directly_when_not_paging(monkeypatch, capsys):
    from viewmd.render import render_multi_file

    monkeypatch.setattr(pager.sys.stdout, "isatty", lambda: False)
    entries = [("a.md", "# A\n"), ("b.md", "# B\n")]
    pager.display_multi_file(entries, no_pager=False, width=80, directory_width=80, color=False,
                             full_front_matter=False, toc=True)
    out = capsys.readouterr().out
    assert out == render_multi_file(entries, width=80, directory_width=80, color=False,
                                    full_front_matter=False, toc=True)


def test_display_multi_file_uses_interactive_pager_when_paging(monkeypatch):
    monkeypatch.setattr(pager.sys.stdout, "isatty", lambda: True)
    calls = []

    def fake_run(entries, *, width, directory_width, color, full_front_matter, toc, theme):
        calls.append((entries, width, directory_width, color, full_front_matter, toc, theme))

    monkeypatch.setattr("viewmd.interactive_pager.run_multi_file", fake_run)
    entries = [("a.md", "# A\n"), ("sub", None)]
    pager.display_multi_file(entries, no_pager=False, width=80, directory_width=120, color=True,
                             full_front_matter=True, toc=False, theme="light")
    assert calls == [(entries, 80, 120, True, True, False, "light")]

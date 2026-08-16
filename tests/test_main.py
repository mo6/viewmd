import argparse
import io

import pytest

from viewmd.__main__ import DEFAULT_MAX_WIDTH, _resolve_width, _width_arg, main


def test_resolve_width_defaults_to_100_when_terminal_is_wider():
    assert _resolve_width(None, terminal_width=200) == DEFAULT_MAX_WIDTH


def test_resolve_width_defaults_to_terminal_width_when_narrower_than_100():
    assert _resolve_width(None, terminal_width=60) == 60


def test_resolve_width_explicit_number_overrides_the_100_cap():
    assert _resolve_width("60", terminal_width=200) == 60
    assert _resolve_width("150", terminal_width=80) == 150


def test_resolve_width_full_uses_terminal_width_uncapped():
    assert _resolve_width("full", terminal_width=200) == 200
    assert _resolve_width("full", terminal_width=60) == 60


def test_width_arg_accepts_full():
    assert _width_arg("full") == "full"


def test_width_arg_accepts_positive_integer_string():
    assert _width_arg("42") == "42"


@pytest.mark.parametrize("value", ["0", "-5", "banana", ""])
def test_width_arg_rejects_invalid_values(value):
    with pytest.raises(argparse.ArgumentTypeError):
        _width_arg(value)


def test_single_file_output_is_unchanged_by_multi_file_support(tmp_path):
    path = tmp_path / "one.md"
    path.write_text("# Hello\n\nbody text\n")

    rc = main(["--no-pager", "--color", "never", "--width", "80", str(path)])

    assert rc == 0


def test_single_file_stdout_matches_direct_render(tmp_path, capsys):
    from viewmd.render import render_markdown

    path = tmp_path / "one.md"
    text = "# Hello\n\nbody text\n"
    path.write_text(text)

    main(["--no-pager", "--color", "never", "--width", "80", str(path)])
    out = capsys.readouterr().out

    assert out == render_markdown(text, width=80, color=False)


def test_no_color_env_var_matches_color_never_for_a_pie_chart(tmp_path, capsys, monkeypatch):
    # VIEWMD-0043 requirement 3/acceptance: NO_COLOR must reach Mermaid
    # rendering itself (bar-chart fallback, no circular pie), the same as an
    # explicit --color never, end to end through main().
    path = tmp_path / "pie.md"
    path.write_text('```mermaid\npie\n    "A" : 1\n    "B" : 1\n```\n')

    monkeypatch.setenv("NO_COLOR", "1")
    main(["--no-pager", "--color", "auto", "--width", "80", str(path)])
    out_no_color_env = capsys.readouterr().out

    monkeypatch.delenv("NO_COLOR")
    main(["--no-pager", "--color", "never", "--width", "80", str(path)])
    out_color_never = capsys.readouterr().out

    assert out_no_color_env == out_color_never
    assert "\x1b[38;2;" not in out_no_color_env


def test_multiple_files_render_in_order_with_heading_and_divider(tmp_path, capsys, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "a.md").write_text("# First\n\nfirst body\n")
    (tmp_path / "b.md").write_text("# Second\n\nsecond body\n")

    rc = main(["--no-pager", "--color", "never", "--width", "80", "a.md", "b.md"])
    out = capsys.readouterr().out

    assert rc == 0
    assert "a.md" in out
    assert "b.md" in out
    assert out.index("First") < out.index("b.md") < out.index("Second")
    assert "═" in out  # the reused front-matter divider style separates the two files


def test_no_args_reads_stdin(monkeypatch, capsys):
    from viewmd.render import render_markdown

    text = "# Hello\n\nbody text\n"
    monkeypatch.setattr("sys.stdin", io.StringIO(text))

    main(["--no-pager", "--color", "never", "--width", "80"])
    out = capsys.readouterr().out

    assert out == render_markdown(text, width=80, color=False)


def test_mixing_stdin_with_a_file_path_is_rejected(tmp_path, capsys):
    path = tmp_path / "one.md"
    path.write_text("# Hello\n")

    rc = main(["-", str(path)])

    assert rc == 1
    assert "cannot mix stdin" in capsys.readouterr().err


def test_one_bad_file_among_several_still_renders_the_rest(tmp_path, capsys, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "good.md").write_text("# Good\n\nbody\n")

    rc = main(["--no-pager", "--color", "never", "--width", "80", "good.md", "missing.md"])
    captured = capsys.readouterr()

    assert rc == 1
    assert "Good" in captured.out
    assert "viewmd: cannot read missing.md" in captured.err


def test_directory_with_index_file_renders_the_index(tmp_path, capsys):
    from viewmd.render import render_markdown

    (tmp_path / "_Index.md").write_text("# Landing\n\nbody text\n")

    rc = main(["--no-pager", "--color", "never", "--width", "80", str(tmp_path)])
    out = capsys.readouterr().out

    assert rc == 0
    assert out == render_markdown("# Landing\n\nbody text\n", width=80, color=False)


def test_directory_without_index_file_renders_a_listing(tmp_path, capsys):
    (tmp_path / "b.md").write_text("# Second\n\nbody\n")
    (tmp_path / "a.md").write_text("---\ntitle: First Note\n---\n\nbody\n")
    (tmp_path / "notes.txt").write_text("not markdown\n")
    (tmp_path / "sub").mkdir()

    rc = main(["--no-pager", "--color", "never", "--width", "80", str(tmp_path)])
    out = capsys.readouterr().out

    assert rc == 0
    assert "a.md" in out
    assert "First Note" in out
    assert "b.md" in out
    assert "Second" in out
    assert "sub" in out
    assert "notes.txt" not in out
    # subdirectories listed before files
    assert out.index("sub") < out.index("a.md")


def test_directory_listing_does_not_recurse_into_subdirectories(tmp_path, capsys):
    sub = tmp_path / "sub"
    sub.mkdir()
    (sub / "nested.md").write_text("# Nested\n")

    rc = main(["--no-pager", "--color", "never", "--width", "80", str(tmp_path)])
    out = capsys.readouterr().out

    assert rc == 0
    assert "nested.md" not in out


def test_unreadable_directory_errors_gracefully(tmp_path, capsys, monkeypatch):
    def _boom(path):
        raise PermissionError(13, "Permission denied")

    monkeypatch.setattr("os.listdir", _boom)

    rc = main(["--no-pager", "--color", "never", "--width", "80", str(tmp_path)])
    captured = capsys.readouterr()

    assert rc == 1
    assert f"viewmd: cannot read {tmp_path}" in captured.err


def test_lowercase_index_filename_does_not_match_the_exact_case_index(tmp_path, capsys):
    # A same-named-but-wrong-case file must not be treated as the index note, even on a
    # case-insensitive filesystem (macOS default) where os.path.isfile() alone can't tell them
    # apart -- it must fall through to the directory listing instead.
    (tmp_path / "_index.md").write_text("# Wrong Case\n")

    rc = main(["--no-pager", "--color", "never", "--width", "80", str(tmp_path)])
    out = capsys.readouterr().out

    assert rc == 0
    # Falls through to the directory listing (a table row naming the file), rather than being
    # rendered as the index note's own page content.
    assert "_index.md" in out
    assert "╭" in out


def test_multi_path_mode_handles_a_directory_among_files(tmp_path, capsys):
    (tmp_path / "one.md").write_text("# One\n\nbody\n")
    sub = tmp_path / "sub"
    sub.mkdir()
    (sub / "_Index.md").write_text("# Sub Landing\n")

    rc = main(["--no-pager", "--color", "never", "--width", "80",
               str(tmp_path / "one.md"), str(sub)])
    out = capsys.readouterr().out

    assert rc == 0
    assert "One" in out
    assert "Sub Landing" in out

"""Tests for viewmd's own interactive pager (VIEWMD-0007).

Covers every pure helper function directly -- the raw-terminal event loop itself (`run`) isn't
unit-testable without a real tty, so these lock down the logic it's built from instead, including
regressions found and fixed while this was developed as `poc/pager/pager_poc.py`.
"""

import pathlib

import pytest

from viewmd import interactive_pager as ip

_KW = {"full_front_matter": False, "toc": False}

_DOC = """\
---
title: Test doc
---

# Title

## Alpha

alpha body text

## Beta

beta body text, with a [[wikilink]] in it

## Gamma

gamma body text
"""


def test_strip_ansi_removes_color_and_hyperlinks():
    colored = "\x1b[1mbold\x1b[0m \x1b]8;id=1;http://x\x1b\\link\x1b]8;;\x1b\\ plain"
    assert ip._strip_ansi(colored) == "bold link plain"


# --- _highlight_matches -----------------------------------------------------------------------


def test_highlight_matches_wraps_every_occurrence_case_insensitively():
    line = "The The the"
    out = ip._highlight_matches(line, "the")
    assert out is not None
    assert ip._strip_ansi(out) == line
    assert out.count(ip._SEARCH_HIGHLIGHT_BG) == 3


def test_highlight_matches_returns_none_for_no_match():
    assert ip._highlight_matches("hello world", "xyz") is None


def test_highlight_matches_returns_none_for_empty_query():
    assert ip._highlight_matches("hello world", "") is None


# --- _load / _locate_headings -------------------------------------------------------------------


def test_load_locates_every_heading_at_the_correct_row():
    colored, plain, headings = ip._load(_DOC, 80, color_kwargs=_KW)
    assert [h.text for h in headings] == ["Title", "Alpha", "Beta", "Gamma"]
    for h in headings:
        assert ip._strip_ansi(plain[h.row]).strip() == h.text
        assert ip._strip_ansi(colored[h.row]).strip() == h.text


def test_load_colored_and_plain_agree_in_length_for_ordinary_markdown():
    colored, plain, _ = ip._load(_DOC, 80, color_kwargs=_KW)
    assert len(colored) == len(plain)


def test_nearest_heading_index_picks_the_section_currently_in_view():
    _, _, headings = ip._load(_DOC, 80, color_kwargs=_KW)
    beta_row = next(h.row for h in headings if h.text == "Beta")
    assert ip._nearest_heading_index(headings, top=beta_row + 2) == 2
    assert ip._nearest_heading_index(headings, top=0) == 0


def test_nearest_heading_index_empty_headings_is_zero():
    assert ip._nearest_heading_index([], top=5) == 0


# --- _popup_box --------------------------------------------------------------------------------


def _headings(n):
    return [ip.HeadingLoc(text=f"Heading {i}", level=2, row=i * 10) for i in range(n)]


def test_popup_box_marks_the_selected_row():
    headings = _headings(3)
    box, scroll = ip._popup_box(headings, selected=1, term_w=60, avail_h=20)
    content = box[1:-1]
    assert "▸" in ip._strip_ansi(content[1])
    assert ip._POPUP_SELECTED_BG in content[1]
    assert "▸" not in ip._strip_ansi(content[0])
    assert scroll == 0


def test_popup_box_scrolls_and_shows_indicators_when_too_tall():
    headings = _headings(20)
    avail_h = 8
    max_rows = max(3, avail_h - 2)
    box, scroll = ip._popup_box(headings, selected=10, term_w=60, avail_h=avail_h)
    content = box[1:-1]
    assert len(content) <= max_rows
    joined = "".join(content)
    assert "▲" in joined
    assert "▼" in joined
    assert scroll > 0


def test_popup_box_no_indicators_when_everything_fits():
    headings = _headings(3)
    box, scroll = ip._popup_box(headings, selected=0, term_w=60, avail_h=40)
    joined = "".join(box)
    assert "▲" not in joined
    assert "▼" not in joined
    assert scroll == 0


# --- _overlay ------------------------------------------------------------------------------------


def test_overlay_leaves_untouched_rows_exactly_as_given():
    body = [f"row {i}" for i in range(10)]
    plain = list(body)
    popup = ["┌──┐", "│ok│", "└──┘"]
    out = ip._overlay(body, plain, popup, term_w=20)
    assert out[0] == body[0]
    assert out[-1] == body[-1]


def test_overlay_no_popup_returns_body_unchanged():
    body = ["a", "b"]
    assert ip._overlay(body, body, [], term_w=20) is body


def test_overlay_does_not_pad_past_real_content():
    # Regression: an earlier version padded touched rows all the way to term_w with literal
    # spaces, painting over the terminal's own background where an erase should have been used.
    body = ["short"] * 5
    plain = list(body)
    popup = ["┌──┐", "│ok│", "└──┘"]
    out = ip._overlay(body, plain, popup, term_w=100)
    box_top = (len(body) - len(popup)) // 2
    row = out[box_top]
    left = (100 - 4) // 2
    tail = ip._strip_ansi(row)[left + 4 :]
    assert tail == plain[box_top][left + 4 :]


# --- _ansi_slice / _crop_row -----------------------------------------------------------------


def test_ansi_slice_plain_text():
    assert ip._ansi_slice("0123456789", 3, 4) == "3456"


def test_ansi_slice_full_width_fast_path_returns_original():
    line = "\x1b[1mhello\x1b[0m"
    assert ip._ansi_slice(line, 0, 100) == line


def test_ansi_slice_never_changes_visible_text_mid_span():
    highlighted = ip._highlight_matches("hello wonderful world", "wonderful")
    assert highlighted is not None
    sliced = ip._ansi_slice(highlighted, 8, 6)
    assert ip._strip_ansi(sliced) == "hello wonderful world"[8:14]
    assert ip._SEARCH_HIGHLIGHT_BG in sliced


def test_ansi_slice_past_end_returns_empty():
    assert ip._ansi_slice("0123456789", 20, 5) == ""


def test_crop_row_no_markers_when_everything_fits():
    row = "short line"
    assert ip._crop_row(row, len(row), left_col=0, width=80) == row


def test_crop_row_right_marker_when_content_extends_past_view():
    row = "x" * 300
    out = ip._crop_row(row, len(row), left_col=0, width=80)
    assert len(ip._strip_ansi(out)) == 80
    assert "‹" not in out
    assert "›" in out


def test_crop_row_left_marker_once_scrolled():
    row = "x" * 300
    out = ip._crop_row(row, len(row), left_col=100, width=80)
    assert len(ip._strip_ansi(out)) == 80
    assert "‹" in out
    assert "›" in out


def test_crop_row_no_right_marker_at_the_true_end():
    row = "x" * 300
    out = ip._crop_row(row, len(row), left_col=220, width=80)
    assert "›" not in out
    assert "‹" in out


def test_crop_row_call_site_uses_the_rows_own_length_not_a_mismatched_twin():
    # Regression: an earlier version decided the right marker using a *different* render's
    # length (some Mermaid diagram types legitimately render different widths with color on vs
    # off, VIEWMD-0043 -- kanban's per-column background fill is a real example) instead of the
    # row actually being displayed, making the marker disappear too early or persist too long.
    # `_crop_row` itself just trusts whatever `plain_len` it's given; this locks down that
    # `draw()`'s call site (mirrored here) passes the row's *own* length, not `plain_lines`'.
    doc = (
        "```mermaid\nkanban\n  Todo\n    a[first]\n    b[second]\n  Done\n    c[third]\n```\n"
    )
    colored, plain, _ = ip._load(doc, 40, color_kwargs=_KW)
    divergent = [
        i for i in range(len(colored)) if len(ip._strip_ansi(colored[i])) != len(plain[i])
    ]
    assert divergent, "fixture assumption broken: expected a color/plain width mismatch"
    i = divergent[0]
    row = colored[i]
    own_len = len(ip._strip_ansi(row))
    mismatched_len = len(plain[i])
    assert mismatched_len != own_len
    correct = ip._crop_row(row, own_len, left_col=max(0, own_len - 10), width=80)
    wrong = ip._crop_row(row, mismatched_len, left_col=max(0, own_len - 10), width=80)
    assert "›" not in correct
    assert "›" in wrong


# --- scrollbar column (VIEWMD-0079) -------------------------------------------------------------


def test_scrollbar_reserved_zero_when_document_fits():
    assert ip._scrollbar_reserved(total_lines=20, body_h=20) == 0
    assert ip._scrollbar_reserved(total_lines=5, body_h=20) == 0


def test_scrollbar_reserved_when_document_overflows():
    assert ip._scrollbar_reserved(total_lines=100, body_h=20) == ip._SCROLLBAR_RESERVED_W
    assert ip._SCROLLBAR_RESERVED_W == 2


def test_scrollbar_thumb_range_at_top():
    start, end = ip._scrollbar_thumb_range(total_lines=100, body_h=20, top=0)
    assert start == 0
    assert end > start


def test_scrollbar_thumb_range_at_bottom():
    max_top = 100 - 20
    start, end = ip._scrollbar_thumb_range(total_lines=100, body_h=20, top=max_top)
    assert end == 20


def test_scrollbar_thumb_range_proportional_midway():
    # Viewing half the document (50/100 rows visible) should occupy roughly half the column.
    start, end = ip._scrollbar_thumb_range(total_lines=100, body_h=50, top=25)
    assert end - start >= 20  # not the whole column, but a substantial chunk
    assert 0 < start < end < 50


def test_scrollbar_thumb_range_never_exceeds_body_h():
    start, end = ip._scrollbar_thumb_range(total_lines=21, body_h=20, top=0)
    assert 0 <= start < end <= 20


def test_scrollbar_prefix_colored_marks_thumb_and_track_distinctly():
    prefix = ip._scrollbar_prefix(total_lines=100, body_h=10, top=0, colored=True)
    assert len(prefix) == 10
    thumb_start, thumb_end = ip._scrollbar_thumb_range(100, 10, 0)
    for i, cell in enumerate(prefix):
        is_thumb = thumb_start <= i < thumb_end
        glyph = ip._SCROLLBAR_THUMB_GLYPH if is_thumb else ip._SCROLLBAR_TRACK_GLYPH
        assert glyph in cell
        assert "\x1b[" in cell  # colored


def test_scrollbar_prefix_plain_has_no_color_but_keeps_glyphs():
    prefix = ip._scrollbar_prefix(total_lines=100, body_h=10, top=0, colored=False)
    assert len(prefix) == 10
    for cell in prefix:
        assert "\x1b[" not in cell
        assert ip._SCROLLBAR_THUMB_GLYPH in cell or ip._SCROLLBAR_TRACK_GLYPH in cell


# --- _link_at / _resolve_link_target / _content_col (VIEWMD-0076) ------------------------------


def _first_colored_line(text: str, width: int = 80) -> str:
    return ip._load(text, width, color_kwargs=_KW)[0][0]


def _col_of(colored_line: str, substring: str) -> int:
    """Display column of `substring`'s first character in `colored_line` -- walks the same
    tokenizer `_link_at` does rather than trusting `str.index` on raw (escape-laden) text."""
    target = substring[0]
    col = 0
    for tok in ip._ANSI_TOKEN_RE.findall(colored_line):
        if tok.startswith("\x1b"):
            continue
        if tok == target:
            return col
        col += ip._char_width(tok)
    raise AssertionError(f"{substring!r} not found in {colored_line!r}")


def test_link_at_resolves_href_at_a_column_inside_the_link():
    line = _first_colored_line("[a link](B.md) after")
    col = _col_of(line, "a link")
    assert ip._link_at(line, col) == "B.md"


def test_link_at_returns_none_just_past_the_link():
    line = _first_colored_line("[a link](B.md) zzz")
    end_col = _col_of(line, "zzz")
    assert ip._link_at(line, end_col) is None


def test_link_at_returns_none_for_plain_text_with_no_link():
    line = _first_colored_line("just plain text, no links here")
    assert ip._link_at(line, 0) is None


def test_link_at_decodes_a_wikilink_href():
    line = _first_colored_line("[[Target Note]]")
    col = _col_of(line, "Target")
    assert ip._link_at(line, col) == "wikilink:Target Note"


def test_link_at_decodes_a_toc_anchor_href():
    # VIEWMD-0077: the static ToC block's own entries carry a `viewmd-toc:<rank>:<heading text>`
    # href (`viewmd/render.py`'s `_toc_lines()`) -- `_link_at` decodes it the same as any other
    # href, scheme-agnostic; the interactive pager's click dispatch is what treats this scheme
    # specially (resolved by heading text + rank into `top`, never through `_resolve_link_target`).
    kw = {**_KW, "toc": True}
    colored, _plain, _headings = ip._load("# Title\n\n## Section\n", 80, color_kwargs=kw)
    toc_line = next(line for line in colored if "Section" in ip._strip_ansi(line))
    col = _col_of(toc_line, "Section")
    assert ip._link_at(toc_line, col) == f"{ip._TOC_ANCHOR_SCHEME}0:Section"


def test_link_at_decodes_a_toc_anchor_href_with_a_percent_looking_heading():
    # Regression (found in review): _link_at() already fully unquotes an href once -- a click
    # handler that unquotes it a *second* time would corrupt a heading whose text happens to
    # contain a literal '%'-looking substring (e.g. quote()-ing "%41" produces "%2541", and a
    # correct single decode gives back "%41", not a further-decoded "A").
    kw = {**_KW, "toc": True}
    heading_text = "Item %41 Spec"
    colored, _plain, _headings = ip._load(f"# Title\n\n## {heading_text}\n", 80, color_kwargs=kw)
    toc_line = next(line for line in colored if "Item" in ip._strip_ansi(line))
    col = _col_of(toc_line, "Item")
    assert ip._link_at(toc_line, col) == f"{ip._TOC_ANCHOR_SCHEME}0:{heading_text}"


def test_resolve_link_target_wikilink_direct_and_recursive(tmp_path):
    (tmp_path / "B.md").write_text("# B\n")
    assert ip._resolve_link_target("wikilink:B", str(tmp_path)) == str(tmp_path / "B.md")
    sub = tmp_path / "sub"
    sub.mkdir()
    (sub / "Nested.md").write_text("# Nested\n")
    assert ip._resolve_link_target("wikilink:Nested", str(tmp_path)) == str(sub / "Nested.md")
    assert ip._resolve_link_target("wikilink:NoSuchDoc", str(tmp_path)) is None


def test_resolve_link_target_relative_markdown_link(tmp_path):
    (tmp_path / "B.md").write_text("# B\n")
    assert ip._resolve_link_target("B.md", str(tmp_path)) == str(tmp_path / "B.md")
    assert ip._resolve_link_target("missing.md", str(tmp_path)) is None


def test_resolve_link_target_rejects_non_md_and_external(tmp_path):
    (tmp_path / "image.png").write_bytes(b"")
    assert ip._resolve_link_target("image.png", str(tmp_path)) is None
    assert ip._resolve_link_target("https://example.com/x", str(tmp_path)) is None
    assert ip._resolve_link_target("mailto:a@b.com", str(tmp_path)) is None


def test_resolve_link_target_rejects_absolute_href(tmp_path):
    # An absolute href isn't "relative to current_dir" -- MUST NOT resolve outside the current
    # document's own directory tree just because a real .md file happens to exist at that
    # absolute path elsewhere on disk (found in review: os.path.join silently discards
    # current_dir for an absolute second argument).
    outside = tmp_path.parent / "outside.md"
    outside.write_text("# Outside\n")
    try:
        assert ip._resolve_link_target(str(outside), str(tmp_path)) is None
    finally:
        outside.unlink()


# --- _resolve_dir_target / directory-listing subdirectory click nav (VIEWMD-0081) --------------


def test_link_at_decodes_a_dir_anchor_href(tmp_path):
    from viewmd.render import render_directory_listing

    (tmp_path / "sub").mkdir()
    colored = render_directory_listing(str(tmp_path), width=80, color=True)
    line = next(line for line in colored.split("\n") if "sub" in ip._strip_ansi(line))
    col = _col_of(line, "sub")
    assert ip._link_at(line, col) == f"{ip._DIR_ANCHOR_SCHEME}sub"


def test_resolve_dir_target_resolves_an_existing_subdirectory(tmp_path):
    sub = tmp_path / "sub"
    sub.mkdir()
    assert ip._resolve_dir_target(f"{ip._DIR_ANCHOR_SCHEME}sub", str(tmp_path)) == str(sub)


def test_resolve_dir_target_rejects_a_missing_directory(tmp_path):
    assert ip._resolve_dir_target(f"{ip._DIR_ANCHOR_SCHEME}missing", str(tmp_path)) is None


def test_resolve_dir_target_rejects_a_path_that_is_a_file_not_a_directory(tmp_path):
    (tmp_path / "a.md").write_text("# A\n")
    assert ip._resolve_dir_target(f"{ip._DIR_ANCHOR_SCHEME}a.md", str(tmp_path)) is None


def test_run_directory_listing_wires_doc_dir_and_subdirectory_open_path(monkeypatch, tmp_path):
    # VIEWMD-0081: `run_directory_listing()` now passes `doc_dir`/`open_path` to `_run()` (just
    # like `run()` does for a `.md` file) so a click on a subdirectory row can navigate into it --
    # this exercises that wiring directly, at the level `_run`'s own click-to-follow logic (itself
    # untested end-to-end, see VIEWMD-0076's tests above) is invoked at, without needing a real
    # tty/event loop.
    sub = tmp_path / "sub"
    sub.mkdir()
    (sub / "nested.md").write_text("# Nested\n")

    captured = {}

    def fake_run(loader, display_name, *, width, fallback, doc_dir=None, open_path=None):
        captured["doc_dir"] = doc_dir
        captured["open_path"] = open_path

    monkeypatch.setattr(ip, "_run", fake_run)
    ip.run_directory_listing(str(tmp_path), width=80, color=False)

    assert captured["doc_dir"] == str(tmp_path)
    new_loader, new_display_name, new_doc_dir = captured["open_path"](str(sub))
    assert new_display_name == "sub/"
    assert new_doc_dir == str(sub)
    colored, _plain, headings = new_loader(80)
    assert any("nested.md" in ip._strip_ansi(line) for line in colored)
    assert headings == []


def test_content_col_maps_through_no_scroll():
    # No truncation markers reserved -- screen column is content column, unchanged.
    assert ip._content_col(plain_len=40, left_col=0, width=80, screen_col=5) == 5


def test_content_col_none_on_left_truncation_marker():
    assert ip._content_col(plain_len=200, left_col=10, width=80, screen_col=0) is None
    assert ip._content_col(plain_len=200, left_col=10, width=80, screen_col=1) == 10


def test_content_col_none_on_right_truncation_marker():
    # plain_len > left_col + width -- a right marker is reserved at the last screen column.
    assert ip._content_col(plain_len=200, left_col=0, width=80, screen_col=79) is None
    assert ip._content_col(plain_len=200, left_col=0, width=80, screen_col=78) == 78


# --- _popup_origin / _popup_hit (VIEWMD-0076) ---------------------------------------------------


def _box(n_content_rows: int, width: int = 10) -> list[str]:
    top = "┌" + "─" * width + "┐"
    bottom = "└" + "─" * width + "┘"
    return [top] + [f"│{'x' * width}│" for _ in range(n_content_rows)] + [bottom]


def test_popup_hit_content_row_inside_box():
    popup = _box(3)
    top, left = ip._popup_origin(popup, body_h=20, term_w=40)
    assert ip._popup_hit(popup, body_h=20, term_w=40, col0=left, row0=top + 2) == 1


def test_popup_hit_none_on_border_row():
    popup = _box(3)
    top, left = ip._popup_origin(popup, body_h=20, term_w=40)
    assert ip._popup_hit(popup, body_h=20, term_w=40, col0=left, row0=top) is None
    assert ip._popup_hit(popup, body_h=20, term_w=40, col0=left, row0=top + 4) is None


def test_popup_hit_none_outside_box_columns():
    popup = _box(3)
    top, left = ip._popup_origin(popup, body_h=20, term_w=40)
    assert ip._popup_hit(popup, body_h=20, term_w=40, col0=0, row0=top + 1) is None


def test_popup_hit_none_for_empty_popup():
    assert ip._popup_hit([], body_h=20, term_w=40, col0=5, row0=5) is None


# --- _read_event ---------------------------------------------------------------------------------


def _pipe_with(data: bytes) -> int:
    r, w = __import__("os").pipe()
    __import__("os").write(w, data)
    __import__("os").close(w)
    return r


def test_read_event_plain_key():
    fd = _pipe_with(b"a")
    assert ip._read_event(fd) == ip.Event("key", "a")


def test_read_event_backspace_variants():
    for data in (b"\x7f", b"\x08"):
        fd = _pipe_with(data)
        assert ip._read_event(fd) == ip.Event("key", "backspace")


def test_read_event_arrow_keys():
    cases = {b"\x1b[A": "up", b"\x1b[B": "down", b"\x1b[C": "right", b"\x1b[D": "left"}
    for data, value in cases.items():
        fd = _pipe_with(data)
        assert ip._read_event(fd) == ip.Event("key", value)


def test_read_event_bare_esc():
    fd = _pipe_with(b"\x1b")
    assert ip._read_event(fd) == ip.Event("key", "esc")


def test_read_event_sgr_mouse_wheel():
    fd = _pipe_with(b"\x1b[<64;10;5M")
    assert ip._read_event(fd) == ip.Event("wheel_up")
    fd = _pipe_with(b"\x1b[<65;10;5M")
    assert ip._read_event(fd) == ip.Event("wheel_down")


def test_read_event_sgr_mouse_horizontal_wheel():
    fd = _pipe_with(b"\x1b[<66;10;5M")
    assert ip._read_event(fd) == ip.Event("wheel_left")
    fd = _pipe_with(b"\x1b[<67;10;5M")
    assert ip._read_event(fd) == ip.Event("wheel_right")


def test_read_event_sgr_mouse_shift_wheel_falls_back_to_horizontal():
    # Terminals with no native horizontal-wheel report (e.g. macOS Terminal.app) send Shift +
    # vertical wheel instead (SGR adds 4 for a held Shift: 64+4=68, 65+4=69) -- the same
    # shift-scrolls-horizontally convention other GUI apps fall back to.
    fd = _pipe_with(b"\x1b[<68;10;5M")
    assert ip._read_event(fd) == ip.Event("wheel_left")
    fd = _pipe_with(b"\x1b[<69;10;5M")
    assert ip._read_event(fd) == ip.Event("wheel_right")


def test_read_event_sgr_mouse_click_press():
    fd = _pipe_with(b"\x1b[<0;15;7M")
    assert ip._read_event(fd) == ip.Event("click", col=15, row=7)


def test_read_event_sgr_mouse_click_release_is_ignored():
    # The release ('m', not 'M') isn't a click -- VIEWMD-0076 only acts on the press.
    fd = _pipe_with(b"\x1b[<0;15;7m")
    ev = ip._read_event(fd)
    assert ev.kind != "click"


def test_read_event_sgr_mouse_modifier_click_is_ignored():
    # A modifier-click (Ctrl/Alt/Shift + left button) is out of scope (VIEWMD-0076 Non-goals) --
    # SGR encodes those as `btn` values other than the bare 0 a plain left-click press reports.
    fd = _pipe_with(b"\x1b[<4;15;7M")  # Shift + left-click
    ev = ip._read_event(fd)
    assert ev.kind != "click"


# --- _mode_line ------------------------------------------------------------------------------


def test_mode_line_shows_top_bot_and_percent():
    assert "Top" in ip._mode_line("f.md", 100, 0, 10, term_w=80)
    assert "Bot" in ip._mode_line("f.md", 100, 90, 100, term_w=80)
    assert "50%" in ip._mode_line("f.md", 100, 40, 50, term_w=80)


def test_mode_line_shows_col_marker_when_scrolled_horizontally():
    line = ip._mode_line("f.md", 100, 0, 10, term_w=80, left_col=42)
    assert "col 43" in line


def test_mode_line_no_col_marker_at_left_col_zero():
    assert "col" not in ip._mode_line("f.md", 100, 0, 10, term_w=80, left_col=0)


def test_mode_line_always_exactly_term_w_wide():
    for term_w in (20, 60, 200):
        line = ip._mode_line("f.md", 100, 0, 10, term_w=term_w, section="A Section")
        assert len(ip._strip_ansi(line)) == term_w or len(line) == term_w


def test_mode_line_truncates_a_too_long_section_with_ellipsis():
    long_heading = "A" * 500
    line = ip._mode_line("f.md", 100, 0, 10, term_w=60, section=long_heading)
    assert len(line) == 60
    assert long_heading not in line
    assert "…" in line


def test_mode_line_drops_section_when_no_room_at_all():
    long_heading = "A" * 500
    line = ip._mode_line("f.md", 100, 0, 10, term_w=20, section=long_heading)
    assert len(line) == 20


# --- _keybind_help / _pad_ansi --------------------------------------------------------------


def test_keybind_help_fits_comfortably_and_stays_colored():
    for popup_open in (False, True):
        line, _spans = ip._keybind_help(popup_open, "full width", True)
        assert len(ip._strip_ansi(line)) <= 90
        assert ip._KEYCAP_BG in line


def test_keybind_help_omits_width_toggle_and_highlight_hints_when_not_applicable():
    line, _spans = ip._keybind_help(False, None, False)
    assert "full width" not in ip._strip_ansi(line)
    assert "clear hl" not in ip._strip_ansi(line)


def test_keybind_help_omits_contents_hint_without_headings():
    # VIEWMD-0072: a directory listing/multi-file view has no heading outline, so 't' is inert --
    # not advertised in the echo-area default hint.
    line, _spans = ip._keybind_help(False, None, False, has_headings=False)
    assert "contents" not in ip._strip_ansi(line)


def test_keybind_help_shows_contents_hint_with_headings_by_default():
    line, _spans = ip._keybind_help(False, None, False)
    assert "contents" in ip._strip_ansi(line)


def test_keybind_help_omits_prev_file_hint_before_any_navigation():
    line, _spans = ip._keybind_help(False, None, False)
    assert "prev file" not in ip._strip_ansi(line)


def test_keybind_help_shows_prev_file_hint_once_has_back_is_true():
    # VIEWMD-0076: 'B' is only advertised once there's actually something to go back to.
    line, _spans = ip._keybind_help(False, None, False, has_back=True)
    assert "prev file" in ip._strip_ansi(line)


# --- _keybind_help spans / _chip_at (VIEWMD-0078) -------------------------------------------


def test_keybind_help_every_chip_has_a_resolvable_span():
    # Requirement 2/acceptance: every chip `_keybind_help()` can render, in both layouts, has a
    # span that covers at least one column and doesn't overlap its neighbors.
    for popup_open in (False, True):
        for width_toggle, highlight_active, has_headings, has_back in (
            (None, False, True, False),
            ("full width", True, True, True),
            (None, False, False, False),
        ):
            _text, spans = ip._keybind_help(
                popup_open,
                width_toggle,
                highlight_active,
                has_headings=has_headings,
                has_back=has_back,
            )
            assert spans
            prev_end = 0
            for start, end, _invoke in spans:
                assert start >= prev_end
                assert end > start
                prev_end = end


def test_keybind_help_base_layout_chip_invokes_match_their_key():
    _text, spans = ip._keybind_help(
        False, "full width", True, has_headings=True, has_back=True
    )
    invokes = {inv.value: inv for _s, _e, inv in spans if inv is not None}
    assert invokes["/"] == ip.Event("key", "/")
    assert invokes["t"] == ip.Event("key", "t")
    assert invokes["B"] == ip.Event("key", "B")
    assert invokes["w"] == ip.Event("key", "w")
    assert invokes["esc"] == ip.Event("key", "esc")
    assert invokes["?"] == ip.Event("key", "?")
    assert invokes["q"] == ip.Event("key", "q")
    # "scroll" (up/down,wheel) has no single unambiguous direction, same as its `_HELP_GROUPS`
    # row -- its span is the first one and carries no invoke.
    assert spans[0][2] is None


def test_keybind_help_popup_layout_chips_have_no_ambiguous_invoke():
    # Non-goal: the popup-open echo hint's move/jump/cancel chips share the same "no single
    # unambiguous action" rule as their `_HELP_GROUPS` counterparts -- only the trailing `q`
    # chip (always appended, popup or not) carries an invoke; the main loop never reaches the
    # echo-row click handler while `popup_open` is true anyway (it has its own click handling
    # for the ToC selection instead), so none of these chips are actually clickable in practice.
    _text, spans = ip._keybind_help(True)
    assert [invoke for _start, _end, invoke in spans[:-1]] == [None, None, None]
    assert spans[-1][2] == ip.Event("key", "q")


def test_chip_at_resolves_column_to_the_right_chip():
    text, spans = ip._keybind_help(False, None, False, has_headings=True)
    plain = ip._strip_ansi(text)
    t_col = plain.index("t contents")
    assert ip._chip_at(spans, t_col) == ip.Event("key", "t")
    q_col = plain.rindex("q quit")
    assert ip._chip_at(spans, q_col) == ip.Event("key", "q")


def test_chip_at_returns_none_between_chips_and_out_of_range():
    text, spans = ip._keybind_help(False, None, False, has_headings=True)
    plain = ip._strip_ansi(text)
    assert ip._chip_at(spans, -1) is None
    assert ip._chip_at(spans, len(plain) + 5) is None
    # The two literal spaces joining every pair of chips fall in no span.
    gap_col = spans[0][1]
    assert plain[gap_col] == " "
    assert ip._chip_at(spans, gap_col) is None


def test_pad_ansi_pads_with_plain_trailing_spaces():
    colored = ip._keycap("q")
    padded = ip._pad_ansi(colored, 20)
    assert len(padded) == len(colored) + (20 - len(ip._strip_ansi(colored)))
    assert padded.endswith(" ")


def test_pad_ansi_falls_back_to_plain_text_when_truncating():
    colored = ip._keycap("q") + " quit"
    truncated = ip._pad_ansi(colored, 3)
    assert truncated == ip._strip_ansi(colored)[:3]


# --- _help_box -----------------------------------------------------------------------------------


def test_help_box_contains_every_group_and_key():
    box, invokes = ip._help_box(term_w=100, avail_h=40)
    text = "\n".join(ip._strip_ansi(row) for row in box)
    for group_name, entries in ip._HELP_GROUPS:
        assert group_name in text
        for key, _, _ in entries:
            assert key in text
    assert len(invokes) == len(box) - 2


def test_help_box_never_exceeds_the_given_width():
    box, _invokes = ip._help_box(term_w=100, avail_h=40)
    assert all(len(ip._strip_ansi(row)) <= 100 for row in box)


def test_help_box_has_a_blank_row_above_every_header_but_the_first():
    box, _invokes = ip._help_box(term_w=100, avail_h=40)
    for i, (group_name, _) in enumerate(ip._HELP_GROUPS):
        header_i = next(j for j, row in enumerate(box) if group_name in row)
        prev_inner = ip._strip_ansi(box[header_i - 1]).strip("│").strip()
        if i > 0:
            assert prev_inner == ""


def test_help_box_headers_and_keys_are_styled():
    box, _invokes = ip._help_box(term_w=100, avail_h=40)
    header_hits = sum(row.count(ip._HELP_HEADER_STYLE) for row in box)
    key_hits = sum(row.count(ip._HELP_KEY_STYLE) for row in box)
    assert header_hits == len(ip._HELP_GROUPS)
    assert key_hits == sum(len(entries) for _, entries in ip._HELP_GROUPS)


def test_help_box_invokes_align_with_entries_that_have_one_unambiguous_action():
    box, invokes = ip._help_box(term_w=100, avail_h=40)
    non_none = [inv for inv in invokes if inv is not None]
    total_entries_with_invoke = sum(
        1 for _, entries in ip._HELP_GROUPS for _, _, inv in entries if inv is not None
    )
    assert len(non_none) == total_entries_with_invoke
    assert all(isinstance(inv, ip.Event) for inv in non_none)


def test_help_box_scrolls_with_indicators_when_too_tall():
    full, _full_invokes = ip._help_box(term_w=100, avail_h=40)
    short, short_invokes = ip._help_box(term_w=100, avail_h=12, scroll=0)
    assert len(short) < len(full)
    assert len(short_invokes) == len(short) - 2
    assert "▼" in "".join(short)
    assert "▲" not in "".join(short)
    end, _end_invokes = ip._help_box(term_w=100, avail_h=12, scroll=1000)
    assert "▲" in "".join(end)
    assert "▼" not in "".join(end)


def test_help_box_never_fills_the_full_body_edge_to_edge():
    # Regression: the popup must always leave at least one row of real document visible above
    # and below it -- callers pass `avail_h = max(3, body_h - 2)`, not the full body height.
    full, _full_invokes = ip._help_box(term_w=100, avail_h=40)
    body_h = len(full)
    body_rows = [f"document line {i}" for i in range(body_h)]
    capped, _capped_invokes = ip._help_box(term_w=100, avail_h=max(3, body_h - 2))
    overlaid = ip._overlay(body_rows, body_rows, capped, term_w=100)
    assert "┌" not in ip._strip_ansi(overlaid[0])
    assert "└" not in ip._strip_ansi(overlaid[-1])


# --- _search ---------------------------------------------------------------------------------


def test_search_finds_next_match_forward():
    lines = ["alpha", "beta", "gamma", "beta again"]
    assert ip._search(lines, "beta", start_after=0) == 1


def test_search_wraps_around_to_the_top():
    lines = ["alpha", "beta", "gamma"]
    assert ip._search(lines, "alpha", start_after=1) == 0


def test_search_case_insensitive():
    lines = ["Hello World"]
    assert ip._search(lines, "hello", start_after=-1) == 0


def test_search_returns_none_when_not_found():
    assert ip._search(["a", "b"], "zzz", start_after=-1) is None


def test_search_empty_query_returns_none():
    assert ip._search(["a", "b"], "", start_after=-1) is None


# --- mouse toggle constants -----------------------------------------------------------------


def test_mouse_on_off_are_a_real_enable_disable_pair():
    assert ip._MOUSE_ON != ip._MOUSE_OFF
    assert "1000h" in ip._MOUSE_ON
    assert "1000l" in ip._MOUSE_OFF


# --- wide characters (VIEWMD-0070) ------------------------------------------------------------

# Rich's own placeholder glyph for an unrenderable image (`![alt](src)`) -- the exact character
# that surfaced this bug live, real double-width content rather than a synthetic fixture.
_WIDE = "🌆"


def test_display_width_counts_a_wide_character_as_two():
    assert ip._display_width(_WIDE) == 2
    assert ip._display_width("a") == 1
    assert ip._char_width(_WIDE) == 2


def test_wc_ljust_pads_by_display_width_not_character_count():
    padded = ip._wc_ljust(f"{_WIDE} demo", 10)
    assert ip._display_width(padded) == 10
    assert len(padded) < 10  # fewer characters than columns, since the emoji is 2 columns/1 char


def test_ansi_slice_wide_character_fully_inside_window():
    line = f"ab{_WIDE}cd"
    out = ip._ansi_slice(line, 0, 6)
    assert out == line
    assert ip._display_width(out) == 6


def test_ansi_slice_pads_a_wide_character_straddling_the_right_edge():
    line = f"ab{_WIDE}cd"  # columns: a=0 b=1 [wide]=2-3 c=4 d=5
    out = ip._ansi_slice(line, 0, 3)  # window [0, 3) cuts the wide char in half
    assert ip._display_width(out) == 3
    assert out == "ab "  # half the glyph can't render -- padded with a space instead


def test_ansi_slice_pads_a_wide_character_straddling_the_left_edge():
    line = f"ab{_WIDE}cd"
    out = ip._ansi_slice(line, 3, 3)  # window starts inside the wide char's own column span
    assert ip._display_width(out) == 3
    assert out == " cd"


def test_crop_row_total_width_unaffected_by_a_wide_character():
    row = f"{_WIDE} " + "x" * 100
    plain_len = ip._display_width(row)
    for left_col in (0, 1, 2, 50):
        out = ip._crop_row(row, plain_len, left_col=left_col, width=20)
        assert ip._display_width(ip._strip_ansi(out)) == 20


def test_overlay_stays_column_aligned_around_a_wide_character():
    # Regression: README.md's own "🌆 viewmd demo" image-placeholder line threw off the help
    # popup's left border in a real terminal -- character-index splicing landed one column short
    # of where display-column splicing should have cut.
    body = [f"{_WIDE} viewmd demo" + " " * 88] * 5  # a 100-col-wide row with a wide char at col 0
    plain = list(body)
    popup = ["┌────┐", "│ ok │", "└────┘"]
    out = ip._overlay(body, plain, popup, term_w=100)
    popup_w = max(ip._display_width(row) for row in popup)
    left = max(0, (100 - popup_w) // 2)
    box_top = (len(body) - len(popup)) // 2
    row = ip._strip_ansi(out[box_top])
    # The popup's own left border must land at display column `left`, not character index
    # `left` -- with a width-2 character at column 0, those differ by one.
    assert ip._display_width(row[: row.index("┌")]) == left
    assert ip._display_width(row) == 100


def test_popup_box_sizes_itself_for_a_heading_containing_a_wide_character():
    headings = [ip.HeadingLoc(text=f"{_WIDE} Section", level=2, row=0)]
    box, _scroll = ip._popup_box(headings, selected=0, term_w=60, avail_h=20)
    widths = {ip._display_width(ip._strip_ansi(row)) for row in box}
    assert len(widths) == 1  # every row, borders included, is exactly the same display width


def test_mode_line_section_with_a_wide_character_stays_exactly_term_w():
    for term_w in (20, 40, 80):
        line = ip._mode_line("f.md", 100, 0, 10, term_w=term_w, section=f"{_WIDE} Intro")
        assert ip._display_width(line) == term_w


# --- run(): non-terminal fallback -------------------------------------------------------------


def test_run_falls_back_to_plain_print_without_a_controlling_terminal(monkeypatch, capsys):
    from viewmd.render import render_markdown

    def fake_open(path, flags):
        raise OSError("no controlling terminal")

    monkeypatch.setattr(ip.os, "open", fake_open)
    text = "# Hello\n\nbody\n"
    ip.run(text, "file.md", width=80, color=False)
    out = capsys.readouterr().out
    assert out == render_markdown(text, width=80, color=False)


def test_run_reads_input_from_dev_tty_not_stdin(monkeypatch):
    # VIEWMD-0007: input piped via stdin (`cat file.md | viewmd -`) must not break keyboard
    # control -- the interactive loop reads from /dev/tty explicitly, never `sys.stdin`, since
    # stdin may be an already-drained pipe with nothing left to read.
    opened = []
    real_open = ip.os.open

    def fake_open(path, flags):
        opened.append(path)
        if path == "/dev/tty":
            raise OSError("no /dev/tty available in this test sandbox")
        return real_open(path, flags)

    monkeypatch.setattr(ip.os, "open", fake_open)
    ip.run("# Hello\n", "-", width=80, color=False)
    assert opened == ["/dev/tty"]


# --- run_directory_listing()/run_multi_file(): non-terminal fallback (VIEWMD-0072) ------------


def test_run_directory_listing_falls_back_to_plain_print(monkeypatch, capsys, tmp_path):
    from viewmd.render import render_directory_listing

    (tmp_path / "a.md").write_text("# A\n")

    def fake_open(path, flags):
        raise OSError("no controlling terminal")

    monkeypatch.setattr(ip.os, "open", fake_open)
    ip.run_directory_listing(str(tmp_path), width=80, color=False)
    out = capsys.readouterr().out
    assert out == render_directory_listing(str(tmp_path), width=80, color=False)


def test_run_multi_file_falls_back_to_plain_print(monkeypatch, capsys):
    from viewmd.render import render_multi_file

    def fake_open(path, flags):
        raise OSError("no controlling terminal")

    monkeypatch.setattr(ip.os, "open", fake_open)
    entries = [("a.md", "# A\n"), ("b.md", "# B\n")]
    ip.run_multi_file(entries, width=80, directory_width=80, color=False,
                      full_front_matter=False, toc=True)
    out = capsys.readouterr().out
    assert out == render_multi_file(entries, width=80, directory_width=80, color=False,
                                    full_front_matter=False, toc=True)


if __name__ == "__main__":
    pytest.main([str(pathlib.Path(__file__))])

"""Tests for Obsidian/GitHub-style admonition callouts (VIEWMD-0059)."""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from wcwidth import wcswidth

from viewmd.render import parse_admonition_marker, render_markdown

FIXTURES = Path(__file__).parent / "fixtures" / "admonition"
CANONICAL = ("NOTE", "TIP", "IMPORTANT", "WARNING", "CAUTION")
ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")

# Pre-VIEWMD-0059 output of a plain blockquote at width=80, color=False -- the
# callout override must not change a non-admonition quote's rendering at all.
PLAIN_BLOCKQUOTE_MD = "> a quoted line\n"
PLAIN_BLOCKQUOTE_NO_COLOR = (
    "\n▌ a quoted line                                                               \n"
)


def strip_ansi(text: str) -> str:
    return ANSI_RE.sub("", text)


def display_width(s: str) -> int:
    width = wcswidth(s)
    return width if width >= 0 else len(s)


@pytest.mark.parametrize(
    "text,token,remainder",
    [
        ("[!NOTE] body", "NOTE", "body"),
        ("[!note] body", "note", "body"),
        ("[!Note] body", "Note", "body"),
        ("[!TIP] x", "TIP", "x"),
        ("[!IMPORTANT] x", "IMPORTANT", "x"),
        ("[!WARNING] x", "WARNING", "x"),
        ("[!CAUTION] x", "CAUTION", "x"),
        ("[!HINT] alias", "HINT", "alias"),
        ("[!success] ok", "success", "ok"),
        ("[!NOTE]- folded", "NOTE", "folded"),
        ("[!NOTE]+ folded", "NOTE", "folded"),
        ("[!NOTE]", "NOTE", ""),
    ],
)
def test_parse_admonition_marker_accepts_well_formed_types(text, token, remainder):
    parsed = parse_admonition_marker(text)
    assert parsed is not None
    assert parsed == (token, remainder)


@pytest.mark.parametrize(
    "text",
    [
        "[!]",
        "[!] body",
        "[!NOTE",
        "[! NOTE]",
        "a quoted line",
        "[NOTE]",
        " [!NOTE] leading space",
    ],
)
def test_parse_admonition_marker_rejects_malformed_lookalikes(text):
    assert parse_admonition_marker(text) is None


def test_plain_blockquote_rendering_is_unchanged():
    assert render_markdown(PLAIN_BLOCKQUOTE_MD, width=80, color=False) == (
        PLAIN_BLOCKQUOTE_NO_COLOR
    )


def test_malformed_marker_falls_back_to_plain_blockquote():
    empty = render_markdown("> [!]\n> body\n", width=80, color=False)
    unterminated = render_markdown("> [!NOTE\n> body\n", width=80, color=False)
    assert empty == (
        "\n▌ [!] body                                                                    \n"
    )
    assert unterminated == (
        "\n▌ [!NOTE body                                                                 \n"
    )
    assert "╭" not in empty
    assert "╭" not in unterminated


@pytest.mark.parametrize(
    "name",
    ["note", "tip", "important", "warning", "caution", "hint", "multipara"],
)
def test_callout_matches_fixture(name):
    md = (FIXTURES / f"{name}.md").read_text()
    expected = (FIXTURES / f"{name}.out").read_text()
    assert render_markdown(md, width=60, color=False) == expected


_CANONICAL_ICONS = {
    "NOTE": "📝",
    "TIP": "💡",
    "IMPORTANT": "❗",
    "CAUTION": "🛑",
}


def test_warning_header_uses_hand_adjusted_double_space():
    # ⚠️ (U+26A0+U+FE0F) renders a column wider than wcswidth reports in
    # several terminals; the issue's mockup hand-adjusts for it with a
    # second space before the label, unlike every other icon (VIEWMD-0059).
    header = render_markdown("> [!WARNING]\n> body\n", width=60, color=False).splitlines()[1]
    assert "⚠️  WARNING" in header
    for kind in ("NOTE", "TIP", "IMPORTANT", "CAUTION"):
        md = f"> [!{kind}]\n> body\n"
        other_header = render_markdown(md, width=60, color=False).splitlines()[1]
        icon = _CANONICAL_ICONS[kind]
        assert f"{icon}  " not in other_header


@pytest.mark.parametrize("kind", CANONICAL)
def test_header_and_body_borders_share_display_width(kind):
    md = f"> [!{kind}]\n> body text here\n"
    lines = [
        ln
        for ln in strip_ansi(render_markdown(md, width=60, color=False)).splitlines()
        if ln.strip()
    ]
    widths = {display_width(ln) for ln in lines}
    assert widths == {60}


@pytest.mark.parametrize("kind", CANONICAL)
def test_canonical_callout_is_case_insensitive(kind):
    bodies = [
        strip_ansi(render_markdown(f"> [!{variant}]\n> body\n", width=60, color=False))
        for variant in (kind, kind.lower(), kind.title())
    ]
    assert bodies[0] == bodies[1] == bodies[2]
    assert kind in bodies[0]
    assert f"[!{kind}]" not in bodies[0]


@pytest.mark.parametrize("kind", CANONICAL)
def test_canonical_callout_color_matches_plain_glyphs(kind):
    md = f"> [!{kind}]\n> body text here\n"
    plain = render_markdown(md, width=60, color=False)
    colored = render_markdown(md, width=60, color=True)
    assert ANSI_RE.search(colored) is not None
    assert ANSI_RE.search(plain) is None
    assert strip_ansi(colored) == plain


def test_generic_callout_has_no_type_color():
    md = (FIXTURES / "hint.md").read_text()
    plain = render_markdown(md, width=60, color=False)
    colored = render_markdown(md, width=60, color=True)
    assert colored == plain


def test_card_border_fills_the_console_render_width():
    md = (FIXTURES / "note.md").read_text()
    narrow = strip_ansi(render_markdown(md, width=60, color=False))
    wide = strip_ansi(render_markdown(md, width=80, color=False))
    assert narrow != wide
    assert max(display_width(ln) for ln in narrow.splitlines() if ln.strip()) == 60
    assert max(display_width(ln) for ln in wide.splitlines() if ln.strip()) == 80


def test_card_border_fills_width_when_color_is_enabled():
    # Regression shape of VIEWMD-0043: color=True used to make Console.size
    # ignore the explicit width on a dumb TERM, so --width had no effect.
    md = (FIXTURES / "note.md").read_text()
    narrow = strip_ansi(render_markdown(md, width=60, color=True))
    wide = strip_ansi(render_markdown(md, width=80, color=True))
    assert narrow != wide
    assert max(display_width(ln) for ln in narrow.splitlines() if ln.strip()) == 60
    assert max(display_width(ln) for ln in wide.splitlines() if ln.strip()) == 80


def test_multipara_body_reflows_each_paragraph_independently():
    out = (FIXTURES / "multipara.out").read_text()
    lines = [ln for ln in out.splitlines() if ln.strip()]
    body = [ln for ln in lines if ln.startswith("│")]
    assert any("First paragraph" in ln for ln in body)
    assert any("Second paragraph stays separate" in ln for ln in body)
    # The second paragraph starts on its own row, not glued onto the first
    # paragraph's last wrapped line.
    second = next(ln for ln in body if "Second paragraph stays separate" in ln)
    assert second.startswith("│ Second paragraph stays separate")
    first_tail = next(ln for ln in body if "inside the card." in ln)
    assert "Second paragraph" not in first_tail

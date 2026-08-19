#!/usr/bin/env python3
"""Proof of concept for VIEWMD-0076's biggest open architecture question: can `_run()`
(`viewmd/interactive_pager.py`), built around one `loader(w)` closure captured once at call time,
be extended so a click on a link can swap the pager to a *different* document mid-session, with a
back-stack to return to where the reader came from -- without `_run()`'s own ~400-line scroll/
draw/event loop needing to be duplicated or rewritten from scratch?

Not part of the shipped `viewmd` package -- imports the real helpers from `viewmd.interactive_pager`
(`_load`, `HeadingLoc`, `_ANSI_TOKEN_RE`/`_OSC8_CLOSE`, `_display_width`) and `viewmd.render`
rather than re-deriving them, and answers three narrower mechanical questions non-interactively
(no real terminal needed, matching this project's `--self-check` convention):

    1. Click hit-testing: given a rendered line and a terminal column, which link (if any) does
       the column land on, and what's its href? (`_link_at`, reusing the same OSC8 tokenizer walk
       `_ansi_slice` already does for horizontal-scroll cropping.)
    2. Href resolution: given a clicked link's href (a `wikilink:Target` or an ordinary relative
       Markdown link) and the currently-open file's directory, does it resolve to an existing
       local `.md` file, or is it a no-op (external URL, missing file, wrong extension)?
       (`resolve_link_target`.)
    3. The frame-swap itself: can `_run()`'s per-document mutable state (lines/headings/loader/
       display_name/top/left_col/...) be pulled into one mutable `_Frame`, replaced in place on
       `navigate()`, and restored from a back-stack on `go_back()`, without the surrounding
       scroll/draw/event loop needing to know or care that a swap happened? (`_Frame`, `_Session`.)

Run the self-check:

    python3 poc/pager/click_nav_poc.py --self-check

`main()`'s interactive path is a deliberately thin demo, not a real click-driven pager -- it opens
a starting file, and 'n' simulates "navigate to whatever this document's first local .md link
resolves to" (no real mouse click decoding here, that part is mechanically identical to
VIEWMD-0075's wheel-button parsing and isn't the open question this POC exists to de-risk), 'b'
goes back, 'q' quits. Useful for eyeballing that frame-swap doesn't corrupt scroll state, not a
preview of the real UI.
"""

from __future__ import annotations

import os
import re
import sys
import urllib.parse
from dataclasses import dataclass, field

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from viewmd.interactive_pager import (  # noqa: E402
    _ANSI_TOKEN_RE,
    _OSC8_CLOSE,
    HeadingLoc,
    _char_width,
    _load,
)

# ---------------------------------------------------------------------------
# 1. Click hit-testing: which link (if any) covers a given display column?
# ---------------------------------------------------------------------------

_OSC8_OPEN_RE = re.compile(r"\x1b\]8;[^;]*;(.*)\x1b\\$")


def _link_at(colored_line: str, col: int) -> str | None:
    """The href of whatever OSC8-wrapped link span covers display column `col` of
    `colored_line`, or `None` if that column isn't inside a link at all.

    Walks the same token stream `_ansi_slice` (`viewmd/interactive_pager.py:346-389`) already
    walks for horizontal-scroll cropping -- SGR/OSC8 escapes and single visible characters -- so a
    real click handler can reuse `_ANSI_TOKEN_RE`/`_OSC8_CLOSE` as-is rather than a second parser.
    """
    active_link: str | None = None
    c = 0
    for tok in _ANSI_TOKEN_RE.findall(colored_line):
        if tok.startswith("\x1b]"):
            if tok == _OSC8_CLOSE:
                active_link = None
            else:
                m = _OSC8_OPEN_RE.match(tok)
                active_link = urllib.parse.unquote(m.group(1)) if m else None
            continue
        if tok.startswith("\x1b["):
            continue
        w = _char_width(tok)
        if c <= col < c + w:
            return active_link
        c += w
    return None


# ---------------------------------------------------------------------------
# 2. Href resolution: wikilink or relative Markdown link -> existing local .md path, or None
# ---------------------------------------------------------------------------

_EXTERNAL_SCHEME_RE = re.compile(r"^[a-zA-Z][a-zA-Z0-9+.-]*:(?!/[^/])")


def resolve_link_target(href: str, current_dir: str) -> str | None:
    """Resolve a clicked link's href to an existing local `.md` file's path, or `None` if it
    isn't one (an external URL/scheme, a missing file, or a non-`.md` target) -- requirements 3
    and 5 of VIEWMD-0076.

    A `wikilink:Target` href (`viewmd/wikilinks.py`'s rewrite) resolves the way Obsidian does for
    a flat vault: `Target.md` directly in `current_dir` first, falling back to a recursive search
    under `current_dir` if not found there. An ordinary link's href is resolved as a filesystem
    path relative to `current_dir` directly, no search.
    """
    if href.startswith("wikilink:"):
        target = href[len("wikilink:") :]
        direct = os.path.join(current_dir, f"{target}.md")
        if os.path.isfile(direct):
            return direct
        for root, _dirs, files in os.walk(current_dir):
            if f"{target}.md" in files:
                return os.path.join(root, f"{target}.md")
        return None
    if href.startswith(("http://", "https://", "mailto:")) or (
        _EXTERNAL_SCHEME_RE.match(href) and "://" in href
    ):
        return None
    candidate = os.path.normpath(os.path.join(current_dir, href))
    if os.path.isfile(candidate) and candidate.lower().endswith(".md"):
        return candidate
    return None


# ---------------------------------------------------------------------------
# 3. The frame-swap: _run()'s per-document state, pulled into one mutable object
# ---------------------------------------------------------------------------


@dataclass
class _Frame:
    """Everything `_run()` (`viewmd/interactive_pager.py:837`) currently holds as loose local
    variables tied to *one* document -- exactly the state a real click-navigate needs to replace
    in place, and exactly the state a back-stack entry needs to snapshot to restore later."""

    path: str
    lines: list[str]
    plain_lines: list[str]
    headings: list[HeadingLoc]
    top: int = 0
    left_col: int = 0


def _frame_for(path: str, width: int) -> _Frame:
    with open(path, encoding="utf-8") as f:
        text = f.read()
    lines, plain_lines, headings = _load(text, width, color_kwargs={})
    return _Frame(path=path, lines=lines, plain_lines=plain_lines, headings=headings)


@dataclass
class _Session:
    """The proposed shape for `_run()`'s own state once it supports navigation: today's single
    set of loose locals (`lines`, `plain_lines`, `headings`, `top`, `left_col`, ...) becomes
    `self.frame`, swapped in place by `navigate()`/`go_back()`; the surrounding scroll/draw/event
    loop keeps reading `self.frame.lines[self.frame.top:...]` etc. exactly as it reads the loose
    locals today -- no change to the loop's own shape, only to where its state lives. `_stack`
    holds the frames navigated *away* from, most recent last, so `go_back()` is a plain pop."""

    width: int
    frame: _Frame
    _stack: list[_Frame] = field(default_factory=list)

    def navigate(self, href: str) -> bool:
        target = resolve_link_target(href, os.path.dirname(self.frame.path) or ".")
        if target is None:
            return False
        self._stack.append(self.frame)
        self.frame = _frame_for(target, self.width)
        return True

    def go_back(self) -> bool:
        if not self._stack:
            return False
        self.frame = self._stack.pop()
        return True


# ---------------------------------------------------------------------------
# Self-check
# ---------------------------------------------------------------------------


def self_check() -> None:
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        a_path = os.path.join(tmp, "A.md")
        b_path = os.path.join(tmp, "B.md")
        with open(a_path, "w", encoding="utf-8") as f:
            f.write(
                "# Doc A\n\n"
                + "\n".join(f"padding line {i}" for i in range(30))
                + "\n\nSee [[B]] and [a relative link](B.md) and [external](https://example.com/x).\n"
            )
        with open(b_path, "w", encoding="utf-8") as f:
            f.write("# Doc B\n\nBody of B.\n")

        # 1. Click hit-testing: a link's own text resolves; text immediately outside it doesn't.
        colored = _load("[a link](B.md) after", 80, color_kwargs={})[0][0]
        if "\x1b]8;" not in colored:
            raise SystemExit(f"self-check: no OSC8 link rendered at all: {colored!r}")
        # Find the display column of the first visible char of "a link" by re-walking with the
        # same tokenizer _link_at uses, rather than assuming `str.index` on the raw ANSI text
        # lines up with display columns (it doesn't, once escapes are involved).
        col = 0
        found_link_col = None
        for tok in _ANSI_TOKEN_RE.findall(colored):
            if tok.startswith("\x1b"):
                continue
            if found_link_col is None and tok == "a":
                found_link_col = col
            col += _char_width(tok)
        if found_link_col is None:
            raise SystemExit("self-check: fixture text 'a link' not found")
        href = _link_at(colored, found_link_col)
        if href != "B.md":
            raise SystemExit(f"self-check: click on link text resolved to {href!r}, want B.md")
        after_href = _link_at(colored, col)  # one past the link's own last character
        if after_href is not None:
            raise SystemExit(f"self-check: click just past the link still hit {after_href!r}")

        # 2. Href resolution: wikilink, relative link, external, missing, non-md all correct.
        checks = [
            (resolve_link_target("wikilink:B", tmp), b_path, "wikilink"),
            (resolve_link_target("B.md", tmp), b_path, "relative link"),
            (resolve_link_target("https://example.com/x", tmp), None, "external URL"),
            (resolve_link_target("mailto:a@b.com", tmp), None, "mailto"),
            (resolve_link_target("wikilink:NoSuchDoc", tmp), None, "missing wikilink target"),
            (resolve_link_target("missing.md", tmp), None, "missing relative target"),
        ]
        img_path = os.path.join(tmp, "image.png")
        open(img_path, "w").close()
        checks.append((resolve_link_target("image.png", tmp), None, "non-.md target"))
        # wikilink recursive fallback: Nested.md lives in a subdirectory, target has no extension.
        sub = os.path.join(tmp, "sub")
        os.makedirs(sub)
        nested_path = os.path.join(sub, "Nested.md")
        with open(nested_path, "w", encoding="utf-8") as f:
            f.write("# Nested\n")
        checks.append((resolve_link_target("wikilink:Nested", tmp), nested_path, "nested wikilink"))
        for got, want, label in checks:
            if got != want:
                raise SystemExit(f"self-check: {label} resolved to {got!r}, want {want!r}")

        # 3. Frame-swap: navigate from A to B, confirm content actually switched, confirm
        # go_back() restores A's own prior scroll position exactly, not just "some" A frame.
        session = _Session(width=80, frame=_frame_for(a_path, 80))
        if session.frame.headings[0].text != "Doc A":
            raise SystemExit("self-check: starting frame isn't Doc A")
        session.frame.top = 17  # simulate the reader having scrolled into the padding lines
        if not session.navigate("B.md"):
            raise SystemExit("self-check: navigate() failed to resolve B.md from A's own directory")
        if session.frame.path != b_path or session.frame.headings[0].text != "Doc B":
            raise SystemExit("self-check: navigate() didn't actually switch to Doc B")
        if session.frame.top != 0:
            raise SystemExit("self-check: new frame didn't start at the top")
        if not session.go_back():
            raise SystemExit("self-check: go_back() found nothing on the stack")
        if session.frame.path != a_path:
            raise SystemExit("self-check: go_back() landed on the wrong file")
        if session.frame.top != 17:
            raise SystemExit("self-check: go_back() lost the reader's scroll position")
        if session.go_back():
            raise SystemExit("self-check: go_back() past the bottom of the stack should be a no-op")

        # External/missing links must not push anything onto the stack at all.
        before = len(session._stack)
        if session.navigate("https://example.com/x") or session.navigate("nonexistent.md"):
            raise SystemExit("self-check: a no-op href still reported a successful navigate")
        if len(session._stack) != before:
            raise SystemExit("self-check: a no-op navigate still pushed a frame")

    print("self-check: ok")


def main(argv: list[str]) -> None:
    if "--self-check" in argv:
        self_check()
        return
    if len(argv) < 2:
        raise SystemExit("usage: click_nav_poc.py <start.md> [--self-check]")
    session = _Session(width=100, frame=_frame_for(argv[1], 100))
    print(f"loaded {session.frame.path} ({len(session.frame.headings)} headings)")
    print("'n' <href>  navigate  |  'b'  back  |  'q'  quit")
    while True:
        cmd = input("> ").strip()
        if cmd == "q":
            break
        if cmd == "b":
            print("back" if session.go_back() else "nothing to go back to")
        elif cmd.startswith("n "):
            href = cmd[2:].strip()
            print(f"navigated to {session.frame.path}" if session.navigate(href) else "no-op")
        print(f"now: {session.frame.path}  top={session.frame.top}  stack={len(session._stack)}")


if __name__ == "__main__":
    main(sys.argv)

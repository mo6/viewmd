# PLAN — design rationale

Why viewmd is built the way it is, so a future issue proposing a change has something concrete to argue against instead of re-deriving these calls from scratch.

## Rendering: Rich's `Markdown`, not a hand-rolled renderer

`rich.markdown.Markdown` (built on `markdown-it-py`) already covers the feature set this tool needs: headers, emphasis/strikethrough, lists, blockquotes, GFM tables, fenced code blocks with Pygments syntax highlighting, horizontal rules, and OSC-8 terminal hyperlinks. Writing a Markdown-to-ANSI renderer from scratch would mean re-solving problems (CommonMark edge cases, table column width, code-block theming) that Rich has already solved and that are not the point of this tool. viewmd's own code stays a thin CLI wrapper: read text in, hand it to Rich, get ANSI out, decide whether to page it.

## Color and width: forced, not left to Rich's own tty detection

Rich's `Console` auto-disables color when its output isn't a tty — which is always true here, since viewmd always writes to an in-memory buffer (`render.py` never touches real stdout) and a real terminal's colors come from deliberately forcing them on. `render_markdown()` takes an explicit `color: bool` and `width: int` rather than letting Rich infer them, so the render step is pure and testable, and so `--color=always` can produce colored output even when the final destination is a pipe (verification step 6 in the issue).

## Paging: own the terminal ourselves, not `rich.console.Console.pager()` or `$PAGER`

Rich ships a `Console.pager()` context manager, but it pages unconditionally and doesn't give control over the tty-detection policy this tool wants (page only when *our* stdout is a terminal, honor `--no-pager`). `pager.py` implements that policy directly: `should_page()` is `sys.stdout.isatty() and not no_pager_flag`. Every paged case -- a single Markdown document (`display_document()`), a bare directory listing (`display_directory_listing()`), a multi-file concatenation (`display_multi_file()`) -- dispatches to `interactive_pager.py`'s owned scrolling loop (`run()`/`run_directory_listing()`/`run_multi_file()`) when paging applies, or prints the already-rendered ANSI text directly otherwise. VIEWMD-0007 first built this for the single-document case only, spawning `$PAGER` (default `less -R -F -X --mouse`) as a subprocess for the other two, the way `git`'s pager decision works, and still honoring an explicit `$PAGER` override for every case; VIEWMD-0072 finished the migration -- viewmd never shells out to an external pager at all now, `$PAGER` is not read anywhere, and there is no `subprocess` call left in `pager.py` -- see the next section for the underlying architecture all three entry points share.

## Interactive pager: own the terminal directly, never an external pager (VIEWMD-0007, VIEWMD-0072)

A popup that interrupts scrolling to overlay a table of contents, then hands control back to exactly where it was, isn't reachable while `less` (or any external `$PAGER`) owns the whole terminal as an opaque subprocess -- viewmd would have no way to draw anything on top of `less`'s own screen, or to know what `less` is currently showing. `interactive_pager.py` instead reads raw terminal input directly (`termios`/`tty`, cbreak mode, the alternate screen buffer) and draws every redraw itself, using only the project's existing dependencies (`rich`, stdlib -- no `curses`, no `prompt_toolkit`). This was de-risked first as `poc/pager/pager_poc.py`, a throwaway script built specifically to answer whether that shape was mechanically achievable before committing to it for real (see VIEWMD-0007's own design notes for why a proof-of-concept, not just a design doc, was the right call for a decision this architecturally significant); the shipped module is a direct port of what that POC validated, not a rewrite from a blank page.

Curses is ruled out, not merely unused. The pager's source of truth is already Rich's ANSI (256-color SGR, OSC-8 hyperlinks), which `draw()` reprints as whole-viewport strings after a cursor-home, and xterm mouse (including any-motion tracking) is spoken directly. Curses wants a cell grid and color pairs, so adopting it would mean re-interpreting those escapes into a second, lossier model rather than dumping them, without even buying native Windows support -- Python's `curses` is still Unix-shaped, and `termios` / `/dev/tty` / `SIGWINCH` would remain. A later issue proposing curses needs a reason that outweighs keeping one ANSI source of truth, not the assumption that a TUI belongs in curses.

VIEWMD-0007 only wired this up for a single Markdown document -- a directory listing and a multi-file concatenation kept spawning `less`/`$PAGER`, since neither has the single document's raw Markdown source `_load()` needs to build a heading outline from. VIEWMD-0072 generalizes the loop: `run()`/`run_directory_listing()`/`run_multi_file()` all share one internal `_run()` engine, parameterized by a `loader(width) -> (colored_lines, plain_lines, headings)` callback instead of a hardcoded Markdown re-parse, so a directory listing (`render_directory_listing`) and a multi-file concatenation (`render_multi_file`) can each supply their own re-render-at-width function in place of `_load`. Neither has a heading outline to build a table-of-contents popup from, so `headings` is always `[]` for them -- the popup key (`t`) becomes inert and is dropped from the echo-area's default keybinding hint whenever `headings` is empty, rather than opening on an empty box. This is what let VIEWMD-0072 drop the external-pager code path (`subprocess`, `$PAGER`) from `pager.py` entirely, not just for the single-document case.

Reads keyboard/mouse input from `/dev/tty`, never `sys.stdin` directly -- the document's raw Markdown source may have been read from a pipe (`cat file.md | viewmd -`), in which case stdin is already fully drained and disconnected from the keyboard by the time the pager starts. This is the same reason external pagers like `less` reopen the controlling terminal for their own input rather than trusting their own stdin; the POC never needed this fix because it was only ever exercised with a file-path argument, never piped stdin, so the gap didn't surface until the real integration.

Two renders (`color=True` and `color=False`) of the same document are kept side by side (`interactive_pager._load`) rather than deriving one from the other by stripping ANSI codes: `_overlay` (the popup-compositing step) and `_crop_row` (the horizontal-scroll truncation-marker step) both need to splice new content into an existing rendered row without slicing through a live color/hyperlink span, which is unsafe in general (a span cut mid-way either leaks its color past where it should stop or loses it entirely with no code left to restore it) -- rebuilding the touched row from its plain twin sidesteps that as a matter of course. The two renders are *not* guaranteed to agree character-for-character, though: `render_markdown` threads `color` into Mermaid's own preprocessing (VIEWMD-0043), and a diagram type is free to size itself differently depending on it -- the kanban renderer's per-column background fill is a real example. Code that needs "how wide is this specific row" has to measure the row actually being displayed, never assume the plain twin's length describes it (this was a real bug during the POC's own development, now covered by a regression test).

## Front matter: a hand-written flat parser, not a YAML dependency

Front matter (`--- ... ---`) is a fixed, narrow shape in practice — flat `key: value` pairs and
`[a, b]`-style lists, the same shape `tools/issues.py` already parses by hand for this project's
own issue files. `viewmd/frontmatter.py` mirrors that parser rather than adding a YAML dependency
to correctly handle nested maps, multi-line scalars, and anchors that this tool has no need to
render as a table anyway (a table wants flat rows, not nested structure). A value that doesn't
fit the flat shape renders as its raw string rather than failing.

## Wikilinks: a text-level rewrite into ordinary Markdown links, not a custom inline rule

`rich.markdown.Markdown.__init__` builds its `MarkdownIt` parser internally with no public
extension point, so adding a real `[[wikilink]]` inline rule would mean subclassing undocumented
internals across Rich versions. `viewmd/wikilinks.py` instead rewrites `[[Target]]` /
`[[Target|Display]]` into an ordinary Markdown link (`[Display](wikilink:Target)`) as a
text-level preprocessing pass, before the body reaches Rich at all — so it picks up Rich's
existing `markdown.link_url` highlight for free, with no new style to define or keep in sync.
The `wikilink:` scheme is inert (never expected to be opened). The pass tracks fenced-code-block
state (tolerant of leading indentation, so a fence nested under a list item still counts) and
skips single-backtick inline code spans, so wikilink-shaped text inside real code (e.g. a Lua
long-bracket string literal `[[...]]`) is left untouched.

## Config file: a flat key=value file, not TOML

viewmd reads `$XDG_CONFIG_HOME/viewmd/config` (falling back to `~/.config/viewmd/config`) as a hand-rolled `key = value` file rather than TOML or YAML. `tomllib` is stdlib only from Python 3.11 and this package still supports 3.10, so TOML would mean a new runtime dependency (`tomli`) just to parse a handful of keys; YAML would be the same cost for no benefit over a format whose entire grammar is "one key, one equals, one value." `configparser` INI was the other stdlib option, but it requires a `[section]` header even for a single flat set of keys, which is ceremony a small file doesn't earn. Unknown keys are ignored so a future key (pager preferences, a ToC depth option) can appear in an already-written file without this parser changing. CLI flags override the file; the file overrides built-in defaults; a missing file is the built-in-defaults case, not an error. `VIEWMD_NO_CONFIG` and `--config PATH` exist so tests and CI never pick up a developer's own file.

## Table of contents: the same parse as the body, not a second one

The ToC (VIEWMD-0062) is built from `ViewmdMarkdown.parsed` -- the markdown-it token stream Rich already produced to render the body -- rather than a second `MarkdownIt().parse(body)` just for headings. Two independent parses of the same source can disagree (a preprocessor, a plugin, or a future Rich change that enables extra rules would only affect one of them); walking the tokens the body render will actually consume is what keeps the outline honest. A leading h1 is the document title, not a ToC row: it is sliced out of that same token stream and rendered once above the outline (the rest of the stream continues below), so it is not duplicated as a flush-left ToC line and not repeated below, and so a reference-style link in the title still resolves against a `[label]: url` defined later in the document. h1/h2/h3 only, in document order, with no attempt to "fix" irregular nesting (an `h3` before any `h1` is indented two steps, not promoted). Depth is not a user option: the ToC starts at three levels and steps down to h1–h2, then h1-only, when a deeper outline would exceed 20 entries, so a long document's ToC stays an at-a-glance outline rather than a second copy of the body. Every remaining h1 is kept even past that cap -- dropping the document's top-level titles would make the outline less useful than a slightly-too-long one. Entries reuse Rich's `markdown.h1`/`h2`/`h3` styles so they match the body's heading weight and color, but stay left-aligned with indent -- the body's centered h1 layout would make a ToC unreadable.

## Out of scope

- **Image-to-ASCII conversion.** `![alt](image.png)` renders as Rich's default (a link/alt-text placeholder), not an ASCII-art rendering of the image itself. Decided explicitly when scoping VIEWMD-0001: ASCII art support means *fenced code blocks render verbatim*, not image conversion. Revisit only if a real need for viewing image-heavy Markdown shows up.
- **HTML rendering.** Raw HTML embedded in a `.md` file is not interpreted; Rich's Markdown renderer already passes it through as literal text, which is the right behavior for a terminal tool.
- **Non-GFM Markdown extensions** (footnotes, definition lists, custom containers, etc.). Not supported beyond what `markdown-it-py`'s GFM-compatible core plus Rich's table extension already parse. Add support only against a real `.md` file that needs it, not speculatively.

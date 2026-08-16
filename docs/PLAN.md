# PLAN — design rationale

Why viewmd is built the way it is, so a future issue proposing a change has something concrete to argue against instead of re-deriving these calls from scratch.

## Rendering: Rich's `Markdown`, not a hand-rolled renderer

`rich.markdown.Markdown` (built on `markdown-it-py`) already covers the feature set this tool needs: headers, emphasis/strikethrough, lists, blockquotes, GFM tables, fenced code blocks with Pygments syntax highlighting, horizontal rules, and OSC-8 terminal hyperlinks. Writing a Markdown-to-ANSI renderer from scratch would mean re-solving problems (CommonMark edge cases, table column width, code-block theming) that Rich has already solved and that are not the point of this tool. viewmd's own code stays a thin CLI wrapper: read text in, hand it to Rich, get ANSI out, decide whether to page it.

## Color and width: forced, not left to Rich's own tty detection

Rich's `Console` auto-disables color when its output isn't a tty — which is always true here, since viewmd always writes to an in-memory buffer (`render.py` never touches real stdout) and a real terminal's colors come from deliberately forcing them on. `render_markdown()` takes an explicit `color: bool` and `width: int` rather than letting Rich infer them, so the render step is pure and testable, and so `--color=always` can produce colored output even when the final destination is a pipe (verification step 6 in the issue).

## Paging: spawn `$PAGER` ourselves, not `rich.console.Console.pager()`

Rich ships a `Console.pager()` context manager, but it pages unconditionally and doesn't give control over the tty-detection policy this tool wants (page only when *our* stdout is a terminal, honor `--no-pager`, honor a user's `$PAGER` override). `pager.py` implements that policy directly: `should_page()` is `sys.stdout.isatty() and not no_pager_flag`, and `display()` spawns `$PAGER` (default `less -R -F -X`) as a subprocess, feeding it the already-rendered ANSI text. This mirrors how `git`'s pager decision works, which is the behavior being copied (auto-page like `git log`/`bat`).

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

The ToC (VIEWMD-0062) is built from `ViewmdMarkdown.parsed` -- the markdown-it token stream Rich already produced to render the body -- rather than a second `MarkdownIt().parse(body)` just for headings. Two independent parses of the same source can disagree (a preprocessor, a plugin, or a future Rich change that enables extra rules would only affect one of them); walking the tokens the body render will actually consume is what keeps the outline honest. A leading h1 is the document title, not a ToC row: it is split out of that same source (markdown-it's `token.map` line span) and rendered once above the outline, so it is not duplicated as a flush-left ToC line and not repeated below. h1/h2/h3 only, in document order, with no attempt to "fix" irregular nesting (an `h3` before any `h1` is indented two steps, not promoted). Depth is not a user option: the ToC starts at three levels and steps down to h1–h2, then h1-only, when a deeper outline would exceed 20 entries, so a long document's ToC stays an at-a-glance outline rather than a second copy of the body. Every remaining h1 is kept even past that cap -- dropping the document's top-level titles would make the outline less useful than a slightly-too-long one. Entries reuse Rich's `markdown.h1`/`h2`/`h3` styles so they match the body's heading weight and color, but stay left-aligned with indent -- the body's centered h1 layout would make a ToC unreadable.

## Out of scope

- **Image-to-ASCII conversion.** `![alt](image.png)` renders as Rich's default (a link/alt-text placeholder), not an ASCII-art rendering of the image itself. Decided explicitly when scoping VIEWMD-0001: ASCII art support means *fenced code blocks render verbatim*, not image conversion. Revisit only if a real need for viewing image-heavy Markdown shows up.
- **HTML rendering.** Raw HTML embedded in a `.md` file is not interpreted; Rich's Markdown renderer already passes it through as literal text, which is the right behavior for a terminal tool.
- **Non-GFM Markdown extensions** (footnotes, definition lists, custom containers, etc.). Not supported beyond what `markdown-it-py`'s GFM-compatible core plus Rich's table extension already parse. Add support only against a real `.md` file that needs it, not speculatively.

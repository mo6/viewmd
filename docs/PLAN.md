# PLAN — design rationale

Why viewmd is built the way it is, so a future issue proposing a change has something concrete to argue against instead of re-deriving these calls from scratch.

## Rendering: Rich's `Markdown`, not a hand-rolled renderer

`rich.markdown.Markdown` (built on `markdown-it-py`) already covers the feature set this tool needs: headers, emphasis/strikethrough, lists, blockquotes, GFM tables, fenced code blocks with Pygments syntax highlighting, horizontal rules, and OSC-8 terminal hyperlinks. Writing a Markdown-to-ANSI renderer from scratch would mean re-solving problems (CommonMark edge cases, table column width, code-block theming) that Rich has already solved and that are not the point of this tool. viewmd's own code stays a thin CLI wrapper: read text in, hand it to Rich, get ANSI out, decide whether to page it.

## Color and width: forced, not left to Rich's own tty detection

Rich's `Console` auto-disables color when its output isn't a tty — which is always true here, since viewmd always writes to an in-memory buffer (`render.py` never touches real stdout) and a real terminal's colors come from deliberately forcing them on. `render_markdown()` takes an explicit `color: bool` and `width: int` rather than letting Rich infer them, so the render step is pure and testable, and so `--color=always` can produce colored output even when the final destination is a pipe (verification step 6 in the issue).

## Paging: spawn `$PAGER` ourselves, not `rich.console.Console.pager()`

Rich ships a `Console.pager()` context manager, but it pages unconditionally and doesn't give control over the tty-detection policy this tool wants (page only when *our* stdout is a terminal, honor `--no-pager`, honor a user's `$PAGER` override). `pager.py` implements that policy directly: `should_page()` is `sys.stdout.isatty() and not no_pager_flag`, and `display()` spawns `$PAGER` (default `less -R -F -X`) as a subprocess, feeding it the already-rendered ANSI text. This mirrors how `git`'s pager decision works, which is the behavior being copied (auto-page like `git log`/`bat`).

## Out of scope

- **Image-to-ASCII conversion.** `![alt](image.png)` renders as Rich's default (a link/alt-text placeholder), not an ASCII-art rendering of the image itself. Decided explicitly when scoping VIEWMD-0001: ASCII art support means *fenced code blocks render verbatim*, not image conversion. Revisit only if a real need for viewing image-heavy Markdown shows up.
- **HTML rendering.** Raw HTML embedded in a `.md` file is not interpreted; Rich's Markdown renderer already passes it through as literal text, which is the right behavior for a terminal tool.
- **Non-GFM Markdown extensions** (footnotes, definition lists, custom containers, etc.). Not supported beyond what `markdown-it-py`'s GFM-compatible core plus Rich's table extension already parse. Add support only against a real `.md` file that needs it, not speculatively.

---
id: VIEWMD-0072
title: Internal interactive pager for directory listings and multi-file views; drop external pager entirely
status: in-progress
area: [cli, render]
effort: high
created: 2026-08-17
updated: 2026-08-17
accepted_by: George Moses
accepted_at: 2026-08-17
commits: []
related: [VIEWMD-0007, VIEWMD-0071]
supersedes: []
changelog:
reason:
---

# Internal interactive pager for directory listings and multi-file views; drop external pager entirely

## Summary

VIEWMD-0007 gave a single Markdown document (a file, stdin, or a directory's `_Index.md` note) an
owned, in-process interactive pager, but explicitly kept spawning `less` (or an explicit `$PAGER`
override) as a subprocess for the two other paged cases: a bare directory listing and a multi-file
concatenation (`viewmd a.md b.md`) -- both still go through `viewmd/pager.py`'s `display()`. This
issue closes that gap: both cases move to the internal pager too, and viewmd drops its dependency
on an external pager binary entirely -- no `less` default, no `$PAGER` override, no
`subprocess`-based pager code path left at all.

## Motivation / problem

Reported directly by the maintainer after landing VIEWMD-0071: viewing a directory still visibly
shells out to `less`, which is surprising given viewmd already owns an interactive pager for the
single-document case, and is an unwanted external runtime dependency besides (a machine without
`less` on `$PATH`, or a `$PAGER` pointing at something incompatible with viewmd's own `-R`/`-F`/`-X`
assumptions, degrades or breaks paging today). Folding directory listings and multi-file views into
the same internal pager removes both problems in one pass, and finishes the migration VIEWMD-0007
started.

## Requirements

1. MUST: a bare directory listing (no `_Index.md` note, VIEWMD-0065), when paging applies
   (`sys.stdout.isatty()` and not `--no-pager`), pages interactively via viewmd's own pager
   instead of spawning `less`/`$PAGER`.
2. MUST: a multi-file view (`viewmd a.md b.md ...`, two or more `path` arguments), when paging
   applies, pages interactively via viewmd's own pager instead of spawning `less`/`$PAGER`.
3. MUST: viewmd never spawns an external pager process under any circumstance -- delete
   `viewmd/pager.py`'s `subprocess`-based code path (`DEFAULT_PAGER`, `_pager_command()`, the
   `subprocess.run` call in `display()`, and `display_document()`'s `$PAGER`-override branch) and
   stop reading the `$PAGER` environment variable anywhere. An explicit `$PAGER` set in the
   environment is silently ignored, not honored and not an error.
4. MUST NOT change `--no-pager` or non-tty (piped/redirected) output for any of the three paged
   cases (single document, directory listing, multi-file) -- each still prints the exact same
   already-rendered bytes it does today.
5. MUST: `viewmd/interactive_pager.py`'s core scrolling loop (mouse-wheel scroll, resize handling,
   forward search, horizontal scroll, width toggle, help screen) works for content with no heading
   outline (a directory listing, a multi-file concatenation) -- the ToC popup key becomes a no-op
   (or is omitted from the help/echo-area keybinding summary) rather than opening a popup with
   nothing in it, when there are no headings to show.
6. MUST: the width toggle (`w`) and a terminal resize while active still re-render at the new width
   for a directory listing or multi-file view, the same as they do for a single document today --
   this requires generalizing the pager's current "reload at width W" hook (today hardcoded to
   re-parsing one Markdown source, `_load(text, width, ...)`) to work for a directory-listing
   re-render and a multi-file concatenation re-render too, not just a single document's.
7. SHOULD: the mode line's per-position "section" indicator (today the nearest heading's text)
   shows something reasonable for a directory listing/multi-file view given they have no headings
   -- e.g. omitted entirely, or (multi-file) the current file's name -- rather than always blank
   or stale.
8. MUST: `README.md`, `docs/PLAN.md`, and `docs/SECURITY.md` updated to describe the new state:
   no external pager dependency, `$PAGER` no longer read or honored anywhere.
9. MUST: the now-dead `S603` ruff-security-lint suppression and its `docs/SECURITY.md` table entries
   for the pager subprocess are removed along with the code they were guarding.

## Non-goals

- No table-of-contents-style popup for a directory listing or multi-file view -- neither has a
  natural per-entry/per-file heading structure to build one from; a future issue's territory if
  ever wanted.
- No per-file jump/navigation keybinding within a multi-file view beyond continuous scrolling --
  matches today's `less`-delegated behavior (README already documents "no per-file navigation,
  it's one long scroll").
- Not touching VIEWMD-0007 v2 (link navigation) or any of its other still-deferred scope.

## Design notes / links

Builds directly on [VIEWMD-0007](VIEWMD-0007-link-navigation.md) (the interactive pager itself) and
[VIEWMD-0071](VIEWMD-0071-directory-listing-full-width-default.md) (directory-listing width
default, landed just before this was reported). The core refactor is turning
`interactive_pager.run()`'s hardcoded `_load(text, width, color_kwargs=...)` reload into a
pluggable "render at width W" hook so a directory listing and a multi-file concatenation can each
supply their own renderer (`render_directory_listing`/a new multi-file-concat renderer) instead of
Markdown source text, while the rest of the loop (scrolling, mouse, resize, search, width toggle,
help) stays shared. `docs/SECURITY.md`'s pager-subprocess row and `S603` note
(`viewmd/pager.py`) go away entirely once there is no subprocess call left to guard.

## Acceptance / verification

- `./run-tests.sh` green (pytest, ruff -- including confirming no live `S603` suppression remains
  for a deleted code path, pip-audit, `issues --check`).
- New/updated tests in `tests/test_pager.py`/`tests/test_interactive_pager.py`/`tests/test_main.py`:
  a directory listing and a multi-file view each dispatch to the internal pager (not a subprocess)
  when paging applies; `--no-pager`/non-tty output for both is byte-identical to before this issue;
  `$PAGER` being set has no effect on any paged output; the ToC-popup key is inert (or omitted from
  the keybinding summary) when there are no headings; the width toggle/resize re-render path works
  for a directory listing and a multi-file view.
- Manual terminal verification (not mockable, matching VIEWMD-0007's own acceptance criteria):
  viewing a directory and viewing multiple files both page interactively with mouse-wheel scroll,
  search, and resize working, and no `less` process is spawned (`ps`/`pgrep less` while paging, or
  simply having no `less` on `$PATH` at all and confirming viewmd still works).
- `grep -rn "PAGER\|subprocess" viewmd/pager.py` turns up nothing pager-subprocess-related once
  done.

## Peer review

- **Claude Sonnet 5** (agent, implementer's own pass), 2026-08-17: Implemented. Core refactor:
  `interactive_pager.py`'s scrolling loop was split into a shared `_run(loader, display_name, *,
  width, fallback)` engine plus three thin public entry points -- `run()` (single document,
  unchanged behavior), `run_directory_listing()` (VIEWMD-0065's table view), and
  `run_multi_file()` (two-or-more `path` arguments). `loader(w)` replaces every hardcoded
  `_load(text, w, ...)` call site (initial load, resize-while-full-width reload, width-toggle
  reload); `render.py` gained `render_multi_file()` as the single source of truth for multi-file
  concatenation rendering, reused by both the `--no-pager` plain-print path and the pager's
  width-toggle reload, so nothing re-reads from disk on a toggle. Requirement 5 (inert ToC popup
  without headings): `t` is now gated on `if headings:` and `_keybind_help` gained a
  `has_headings` flag that drops the `t: contents` hint from the echo area when there's no
  outline, mirroring the existing `width_toggle`/`highlight_active` omission pattern. Requirement
  7 (SHOULD): satisfied via the explicitly-allowed "omitted entirely" option -- the mode line's
  `section` field stays derived from `headings` (empty for both new cases), while the mode line's
  own `name` field shows the directory path or "`N files`" instead. `pager.py` was rewritten with
  no `subprocess`/`shlex`/`$PAGER` code at all -- `display_document`/`display_directory_listing`/
  `display_multi_file` each either print plainly (non-tty/`--no-pager`) or dispatch straight to
  the matching `interactive_pager` entry point. `pyproject.toml`'s now-dead `S603` per-file-ignore
  for `viewmd/pager.py` and the matching `docs/SECURITY.md` table rows/prose were removed.
  `README.md`/`docs/PLAN.md`/`docs/SECURITY.md`/`docs/example.md` updated to drop every remaining
  `less`/`$PAGER` mention (the "no per-file navigation" note moved from the multi-file paragraph
  into the Interactive pager section, since it's now a pager-loop property, not a rendering one).
  `./run-tests.sh` green (1024 tests, ruff, pip-audit, issues index) -- new/updated coverage in
  `tests/test_pager.py` (all three `display_*` dispatch functions, plus a source-level assertion
  that `pager.py` never imports `subprocess` or reads `$PAGER`), `tests/test_interactive_pager.py`
  (`run_directory_listing`/`run_multi_file`'s non-tty fallback paths, `_keybind_help`'s
  `has_headings` gating), and `tests/test_main.py` (directory listing and multi-file each
  dispatching to `viewmd.interactive_pager.run_directory_listing`/`run_multi_file` when
  `sys.stdout.isatty()` is patched True and `--no-pager` is omitted).
  Manual terminal verification (`pty.fork()`-based smoke test, since this sandbox has no real
  terminal): confirmed for both a directory listing and a multi-file view -- the alternate-screen/
  mouse-capture entry sequence appears (`\x1b[?1049h...\x1b[?1000h\x1b[?1006h`), `pgrep -P <pid>`
  finds zero child processes (no `less` spawned), the mode line shows the expected name (`dir/` /
  `N files`) and line count, the echo-area default hint omits the `t: contents` binding (headings
  are empty), and `q` cleanly exits (mouse-off/cursor-visible/alt-screen-exit sequence). Did not
  independently verify actual mouse-wheel scroll events, a live terminal resize, or the width
  toggle against a real terminal emulator (the pty harness can send keystrokes but not synthesize
  xterm SGR mouse reports or `SIGWINCH`) -- these reuse the exact same code paths VIEWMD-0007
  already shipped and smoke-tested for the single-document case, just reached through a different
  `loader`, so risk is judged low, but a maintainer smoke test of scroll/resize/width-toggle on a
  real directory listing and multi-file view is still worth doing before considering this fully
  verified, matching VIEWMD-0007's own acceptance criteria's treatment of "not mockable" behavior.
- **George Moses** (maintainer), 2026-08-17: signed off; commit and close out.

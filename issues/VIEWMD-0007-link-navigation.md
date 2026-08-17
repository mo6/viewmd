---
id: VIEWMD-0007
title: Navigate a document interactively -- a ToC popup for v1, link navigation for v2
status: in-progress
area: [cli, render]
effort: high
created: 2026-08-02
updated: 2026-08-17
accepted_by: George Moses
accepted_at: 2026-08-17
commits: []
related: [VIEWMD-0006, VIEWMD-0061, VIEWMD-0062, VIEWMD-0067]
supersedes: []
changelog:
reason:
---

# Navigate a document interactively -- a ToC popup for v1, link navigation for v2

## Summary

Diverging from GNU Info's node-based pager model (see the Info research note below, kept for its v2 relevance): v1 keeps viewmd's Markdown output scrolling continuously, the way `less` scrolls plain text today -- no nodes, no per-node header line, no menu-vs-cross-reference distinction. Scoped down to a plain-scroll-plus-popup version on 2026-08-16, then widened again on 2026-08-17 (see the v1/v2 split below) once a proof-of-concept built to de-risk the popup's own architecture question turned out to answer several smaller, adjacent ones too: v1 now also adopts Info's two-line mode-line/echo-area status split (reversing the original 2026-08-16 decision against it), an Info-style forward search with match highlighting, horizontal scrolling with truncation indicators for Mermaid/code content wider than the terminal, a render-width toggle, a mouse-capture toggle so the reader can still select text natively, direct terminal-resize handling, and a discoverable help screen. The core interactive feature is still the on-demand table-of-contents popup: press a key at any scroll position, see the document's heading outline (the same `h1`-`h3` structure [VIEWMD-0062](VIEWMD-0062-table-of-contents.md) already renders statically at the top of the document) overlaid on screen, pick an entry, and jump straight to it. Following links interactively -- next/prev link, follow a link's target, back-history -- remains explicitly deferred to v2.

## Motivation / problem

Flagged by the maintainer as a future direction, alongside VIEWMD-0006 (link highlighting): once links are visually distinct, the natural next step is being able to act on them -- especially for `[[wikilink]]`-heavy note collections (Obsidian vaults) and this project's own `issues/*.md`, which cross-reference each other constantly (`[[DELVE-0046]]`, `[related](VIEWMD-0004-...md)`, etc.) with no way today to follow a reference without leaving viewmd. That's still the long-term motivation (v2, below). The more immediate gap the maintainer identified while narrowing v1's scope (2026-08-16): once VIEWMD-0062 gives a document a static ToC at the very top of its output, a reader scrolled deep into a long document (this project's own `README.md`, `docs/PLAN.md`) has no way back to a specific *other* section without paging all the way back to the top and re-reading the ToC there -- a popup reachable from anywhere in the scroll fixes exactly that, without needing link-following machinery at all.

## v1 / v2 split (decided 2026-08-16, widened 2026-08-17)

- **v1 (this issue's scope):** viewmd owns an interactive scrolling loop directly (raw terminal input, no external `less`/`$PAGER`-by-default delegation, see Design notes) providing: continuous line-based scrolling with mouse-wheel support; a two-line Info-style mode-line/echo-area status split; an on-demand ToC popup; forward search with match highlighting; horizontal scrolling with truncation indicators; a render-width toggle; a mouse-capture toggle; direct terminal-resize handling; and a help screen (see Requirements). Still no node concept, no `Next`/`Prev`/`Up`, no menu-vs-cross-reference distinction, no link focus/follow -- those remain Info vocabulary this issue doesn't adopt, or v2's territory. An explicit `$PAGER` override still delegates to that external pager unchanged, matching today's behavior, since a reader who's deliberately chosen a different pager shouldn't lose it.
- **v2 (future, its own scoping pass once v1 has shipped and been used for a while):** link navigation -- jump to the next/previous link, follow a link's target (another local `.md` file, or a heading within the current one), and go back. Requirements deliberately not written yet, same reasoning the original (pre-split) version of this issue gave for deferring the whole thing.

## Requirements

1. MUST scroll rendered Markdown output continuously, line-based, matching `less`'s own scrolling behavior -- not paginated by document node/section the way Info is.
2. MUST support mouse-wheel/trackpad scrolling, moving the view the same way it does in `less` (with `--mouse`, [VIEWMD-0067](VIEWMD-0067-less-pager-mouse-scroll.md)) -- since v1 stops delegating to an external `less` process by default (see Design notes below), this behavior has to be implemented directly in viewmd's own scrolling loop rather than inherited for free; it does not happen automatically just because v1's scrolling *feels* like `less`.
3. MUST show a two-line status split at the bottom of the screen: a mode line (filename, line count, and scroll position) and, below it, an echo area (a context-sensitive keybinding summary by default, replaced by search prompts/messages while active) -- adopting Info's own mode-line/echo-area shape (see the Info research note below), reversing the narrower 2026-08-16 decision against it.
4. MUST provide an on-demand ToC popup, opened by a dedicated key, that overlays the document's heading outline (the same `h1`-`h3` structure and indentation [VIEWMD-0062](VIEWMD-0062-table-of-contents.md) extracts and renders statically) on top of the current scroll view, scrollable if the outline is taller than the screen, and never spanning the full screen height edge-to-edge (at least one row of the document stays visible above and below it).
5. MUST let the reader move a selection within the popup (e.g. arrow keys, mouse wheel per requirement 2, or vim-style `j`/`k`) and confirm it (e.g. Enter), and on confirmation scroll the underlying view to that heading's position and close the popup.
6. MUST let the reader dismiss the popup without jumping (e.g. Esc, or the same key that opened it) and return to exactly the scroll position the popup was opened from.
7. MUST make the popup available regardless of current scroll position -- including when VIEWMD-0062's static ToC at the top of the document is itself off-screen.
8. MUST NOT change any `--no-pager` or non-terminal (piped/redirected) output -- the popup, like the pager itself, is a terminal-interactive-only feature.
9. MUST NOT implement link navigation (jump to next/prev link, follow a link's target, back-history) -- explicitly v2, see Non-goals.
10. MUST support a forward text search (Info's own `/`/`s`, prompted in the echo area), highlighting every match on a currently visible line -- not only the line jumped to -- until explicitly cleared, with a way to repeat the last search without retyping it.
11. MUST support horizontal scrolling for a rendered line wider than the terminal (a Mermaid diagram or fenced code block, VIEWMD-0018/0019), with a visible indicator when a line is truncated to the left and/or right of the current view, rather than either wrapping onto extra terminal rows or silently hiding the rest with no indication more exists.
12. MUST support toggling between the configured/`--width` render and the full terminal width at runtime, without restarting viewmd.
13. MUST support toggling mouse capture off so the reader can fall back to the terminal's own native text selection (a plain click-drag), since enabling mouse-wheel support (requirement 2) is what captures every mouse event, selection included, in the first place.
14. MUST redraw at a new size when the terminal is resized (`SIGWINCH`), without requiring the reader to press a key first.
15. MUST provide a discoverable, on-demand help screen listing every keybinding this issue introduces.

## Non-goals

- Everything from the Info research note below that v1 still doesn't adopt: a per-node header line, `Next`/`Prev`/`Up`, the menu-vs-cross-reference distinction, `g`/`t`/`d` node-jump commands, node-scoped search -- viewmd has no node concept for any of these to attach to, and none of it is needed for a document-scoped (not node-scoped) pager.
- Interactive link following (v2, see the v1/v2 split above) -- jumping to a link, following its target, and a back-history stack are all out of scope for this issue's v1.
- A configurable popup keybinding, popup style, or ToC depth beyond what [VIEWMD-0062](VIEWMD-0062-table-of-contents.md) itself already extracts (`h1`-`h3`) -- v1 reuses that issue's outline as-is, and every other keybinding in this issue is likewise fixed, not user-configurable.
- Mouse click-to-confirm a ToC popup selection, or click-to-follow anything -- the popup is keyboard/wheel-driven only (requirement 5); pointer interaction beyond scrolling is v2 territory at the earliest, once link-following exists to click on.
- Replacing an explicit `$PAGER` override -- that still delegates to the external pager unchanged (see the v1/v2 split above); only the *default*, no-`$PAGER`-set behavior changes.

## Design notes / links

Builds on [VIEWMD-0006](VIEWMD-0006-wikilink-highlighting.md)'s link highlighting for v2 (not v1, which has no link interaction) and directly on [VIEWMD-0062](VIEWMD-0062-table-of-contents.md)'s heading-outline extraction for v1's popup content -- **VIEWMD-0062 is now a blocking dependency of this issue's v1**, not just a prerequisite of convenience as originally filed below, since the popup has nothing to show without that issue's outline data structure existing first (VIEWMD-0062 has since shipped, see below). Also interacts with [docs/PLAN.md](../docs/PLAN.md)'s pager design: `viewmd/pager.py` spawns `$PAGER` as an external subprocess today, handing the terminal over entirely once `less` starts -- a popup that can interrupt scrolling to overlay content and later hand control back is not reachable that way. v1 likely needs viewmd to own a minimal interactive scrolling loop itself (raw terminal input, feeding pre-rendered screenfuls, `less`-equivalent scroll keys, including mouse-wheel handling per requirement 2) rather than delegating to an external `$PAGER` process, even though v1's scrolling behavior otherwise deliberately mimics `less` rather than reinventing it -- this is the single biggest architectural change v1 introduces relative to today's pager, and worth its own design note (and a proof-of-concept, matching this project's usual practice for a UI/architecture-shape decision) once this issue is actually scoped for building. [VIEWMD-0067](VIEWMD-0067-less-pager-mouse-scroll.md) fixes mouse-wheel scrolling for *today's* `less`-delegated pager in the meantime -- a separate, narrower fix that stands on its own regardless of when this issue's v1 is built, but whose `--mouse` flag becomes moot once v1 stops delegating to external `less` at all.

**Proof-of-concept (2026-08-16, expanded through 2026-08-17):** [`poc/pager/pager_poc.py`](../poc/pager/pager_poc.py) de-risks the architecture-shape question raised above -- whether viewmd can own an interactive scrolling loop directly, using only the project's existing dependencies (`rich`, stdlib -- no `curses`, no `prompt_toolkit`), rather than delegating the whole terminal to an external `less` subprocess the way `viewmd/pager.py` does today -- and has since grown well past that original question into a fuller exploration of what an owned loop could look like, useful context for this issue's eventual v1 scoping pass even though most of what follows goes beyond what the Requirements/Non-goals above currently call for. What it implements now: mouse-wheel scrolling via xterm SGR reporting, with a dedicated key (`m`) to toggle mouse capture off so a click-drag falls back to the terminal's own native text selection (most terminals also support a modifier-drag bypass -- Option on macOS, Shift elsewhere -- without needing to toggle anything); a ToC popup matching requirements 4-6 (open/select/confirm/cancel, pre-selecting the heading nearest the current scroll position, scrollable with `▲`/`▼` indicators when the outline doesn't fit the screen, and always leaving at least one row of real document visible above/below it rather than filling the screen edge-to-edge); Info-style forward search (prefilled with the last query so Enter alone repeats it, a dedicated repeat key with no prompt, and every match on a visible line highlighted -- not just the one jumped to -- until explicitly cleared); horizontal scrolling with `‹`/`›` truncation-edge markers for a fenced-code or Mermaid line wider than the terminal (VIEWMD-0018/0019); a width toggle (`w`) between the configured/`--width` render and the full terminal width; direct `SIGWINCH` handling (via `signal.set_wakeup_fd`, the same self-pipe idea `less`'s own resize handling is built on) that redraws at a new terminal size immediately rather than waiting for the next keypress; and a `?` help screen listing every binding in a colored, scrollable table. It also explored the two-line Info-style mode-line/echo-area split this issue's requirement 3 originally ruled OUT of v1 -- built so the maintainer could compare both shapes before deciding, which is exactly what happened: requirement 3 above now adopts it, reversing the original 2026-08-16 call. Confirmed the whole approach is mechanically viable with what viewmd already depends on; the POC script itself still doesn't implement any of this issue's requirements as shippable behavior (no `--no-pager`/config wiring, not reachable from the real `viewmd` CLI, no automated tests beyond its own `--self-check`) and remains outside the shipped package -- the real implementation now lives in `viewmd/pager.py` and friends, ported from and tested against the same mechanics this POC validated. Run `python3 poc/pager/pager_poc.py [file.md] [--width N]` for the interactive loop (`?` shows the full keybinding reference once running), or `python3 poc/pager/pager_poc.py --self-check` for a non-interactive sanity check of the rendering/outline/overlay/scroll machinery.

**Split into preparation issues (2026-08-16):** rather than scoping this whole issue in one pass, two smaller, independently-useful pieces were filed and built ahead of it: [VIEWMD-0061](VIEWMD-0061-global-config-file.md) (a user-global config file -- this issue's own future interactive-pager preferences will want somewhere to live too, and VIEWMD-0062 needs a `toc` on/off key; **implemented**) and [VIEWMD-0062](VIEWMD-0062-table-of-contents.md) (a static table of contents from `h1`-`h3` headings -- the closest thing a non-interactive renderer can produce to Info's `* Menu:` concept below, and a real feature on its own regardless of whether/when this issue itself is ever scoped and built; **implemented** -- the blocking-dependency note above is now satisfied).

### Research: GNU Info's pager model (v2 background, not v1)

Investigated `info(1)` (the stand-alone GNU Info reader, `info --version` distinct from the Emacs Info mode it also ships) as the closest existing prior art for "a pager whose unit of navigation is document structure and links, not just lines" -- originally the model this issue's summary invoked wholesale; per the v1/v2 split above, v1 deliberately does *not* adopt Info's node/menu/mode-line model (plain `less`-style scrolling instead), so this research is kept as background for v2's eventual scoping, not requirements v1 draws from. Findings, translated into terms a future v2 scoping pass can build requirements from:

- **Nodes, not just scroll position.** Info splits a document into named *nodes* (`Top`, a
  chapter, a subsection...); each node carries a fixed header line at the very top of the screen:
  `File: emacs.info,  Node: Copying,  Next: Distrib,  Prev: Top,  Up: Top`. `Next`/`Prev` are
  *sibling* nodes at the same structural level (not adjacent lines of text), `Up` is the parent.
  Scrolling (`SPC`/`DEL`, i.e. Space/Backspace) moves within a node's text; running off the end of
  a node auto-advances to `Next` rather than stopping, so paging through feels continuous even
  though it's crossing structural boundaries. viewmd's closest analogue to a "node" is a Markdown
  heading's section; `Next`/`Prev`/`Up` would be sibling/parent headings rather than sibling files.
- **Two distinct link types, not one.** Info separates *menu items* (`* Item name: Target-node.`,
  or `* Item name::` when the label and target match) -- lines living inside a `* Menu:` block,
  effectively a node's table of contents to its children -- from *cross-references* (`*Note Target
  node::` or `*Note Label: Target node.`) -- inline links appearing anywhere in body text, more
  like a footnote/see-also. Both render distinctly (menu items get a `*` bullet with a fixed
  position; xrefs are inline) and both are separately keyboard-addressable (`m` prompts for a menu
  item by name with completion; `f` prompts for a cross-reference by name). viewmd's Markdown
  equivalents aren't a clean 1:1 -- a Markdown list of links reads like a menu, an inline
  `[text](target)` or `[[wikilink]]` reads like an xref -- worth keeping as two concepts rather than
  collapsing every link into one kind when this gets scoped.
- **Link traversal is keyboard-driven, not pointer-driven.** `TAB` moves focus to the next
  link/menu-item in the current node (`M-TAB` for previous); `RET` (Enter) follows whichever link
  currently has focus; digit keys `1`-`9` jump straight to the Nth menu item without needing `TAB`
  first. Separately, `n`/`p`/`u` move between nodes directly (ignoring links entirely -- pure
  structural next/prev/up), and `l` ("last") pops a visited-node history stack, i.e. *back*, distinct
  from `Prev` (`l` is "where I was", `Prev` is "the sibling before this one" -- they usually differ
  after following a link). `g` prompts to jump straight to a node by name; `t` jumps to the file's
  `Top` node; `d` jumps to the top-level directory node (the "home" node when Info is showing more
  than one file/manual).
- **A two-line status area at the bottom, split by purpose.** The second-to-last screen row is the
  *mode line* -- a single reverse-video (highlighted) status line, machine-formatted, always
  present, showing current position: `-----Info: (emacs.info)Copying, 40 lines --Top-------------`
  (file/node name, node's line count, and a scroll-position indicator that reads `--Top--` at the
  node's start, a percentage like `--33%--` while scrolled through the middle, and `--Bot--` at the
  end). The very last row is the *echo area* -- normally blank, used only transiently for command
  prompts (`Search: `, `Goto node: `) and one-line result/error messages (`No more nodes within this
  document.`), then reverts to blank. Keeping these separate means routine position feedback (mode
  line) is never overwritten by prompt/message text (echo area) or vice versa.
- **Search is node-then-document scoped.** `s` (or `/`) searches forward from point; the classic
  stand-alone reader's incremental variant is Emacs Info's `M-s`, not stand-alone `s`, which prompts
  in the echo area and jumps on Enter. A search crossing a node boundary is explicit ("Search
  failed" / auto-continuing into the next node), not silent -- worth a similar explicit signal if
  viewmd's own search (already pager-adjacent territory, see `viewmd/pager.py`) grows node-awareness.
- **A built-in, discoverable help layer.** `?` shows a one-screen command summary (not a man page);
  `h` launches an interactive tutorial node. Both are themselves just... nodes, navigated the same
  way as document content -- there's no separate "help mode," which keeps the keybinding surface
  small and self-consistent.

Most of the above is still not a v1 requirement (see Requirements, above) -- vocabulary reserved for v2's own future scoping pass -- with one exception: the mode-line/echo-area split (requirement 3) is now adopted, not deferred; the rest (nodes, `Next`/`Prev`/`Up`, the menu-vs-cross-reference distinction, `g`/`t`/`d` node commands, node-scoped search) stays out of scope, since viewmd still has no node concept for any of it to attach to.

### Mockup: v1 -- plain scrolling, plus the ToC popup

Illustrative only -- the exact popup key, its border style, and selection-highlight styling are all implementation decisions for the eventual scoping pass, not settled by this mockup. Shown rendering this very issue file, mid-scroll (partway through the "Requirements" section), the way `viewmd VIEWMD-0007-link-navigation.md` would look today plus this issue's own popup addition.

Ordinary scrolling -- no viewmd-specific chrome, just the rendered body and whatever status line the terminal/pager already shows (here, `less`'s own default filename+percentage line, unchanged by this issue per requirement 3):

```
  1. MUST scroll rendered Markdown output continuously, line-based, matching
     less's own scrolling behavior -- not paginated by document node/section
     the way Info is.
  2. MUST NOT implement Info's per-node header line, Next/Prev/Up navigation,
     or a two-line mode-line/echo-area split -- v1 has no node concept;
     ordinary scroll-position feedback (e.g. less's own filename/percentage
     line) is enough.
  3. MUST provide an on-demand ToC popup, opened by a dedicated key, that
     overlays the document's heading outline (the same h1-h3 structure and
     indentation VIEWMD-0062 extracts and renders statically) on top of the
     current scroll view.
  4. MUST let the reader move a selection within the popup (e.g. arrow keys)
     and confirm it (e.g. Enter), and on confirmation scroll the underlying
     view to that heading's position and close the popup.

VIEWMD-0007-link-navigation.md (61%)
```

Pressing the popup key overlays the same VIEWMD-0062 heading outline the document already renders at its own top, without losing the current scroll position underneath it -- here with "Design notes / links" currently selected (`▸`), ready to jump on `Enter`:

```
  1. MUST scroll rendered Markdown output continuously, line-based, matching
     less's own scrolling behavior -- not paginated by document node/section
  ┌─ Table of contents ──────────────────────────────────────────────┐
  │ Summary                                                          │
  │ Motivation / problem                                             │
  │ v1 / v2 split (decided 2026-08-16)                               │
  │ Requirements                                                     │
  │ Non-goals                                                        │
  │▸Design notes / links                                             │
  │ Acceptance / verification                                        │
  │ Peer review                                                      │
  │                                                                  │
  │ [↑/↓] move   [Enter] jump   [Esc] cancel                         │
  └──────────────────────────────────────────────────────────────────┘
VIEWMD-0007-link-navigation.md (61%)
```

Confirming the "Design notes / links" entry scrolls straight to that section and closes the popup, landing exactly the way `less`'s own `/Design notes` search-and-jump would, just without needing to know or type the heading text:

```
  ## Design notes / links

  Builds on VIEWMD-0006's link highlighting for v2 (not v1, which has no
  link interaction) and directly on VIEWMD-0062's heading-outline
  extraction for v1's popup content -- VIEWMD-0062 is now a blocking
  dependency of this issue's v1, not just a prerequisite of convenience as
  originally filed below, since the popup has nothing to show without that
  issue's outline data structure existing first.

VIEWMD-0007-link-navigation.md (78%)
```

## Acceptance / verification

- `./run-tests.sh` green (pytest, ruff, `tools/issues.py --check`), including new/updated tests in `tests/test_pager.py` for: `--no-pager` and non-tty output completely unaffected and byte-identical to before this issue (requirement 8); the mode-line/echo-area content at a few scroll positions (requirement 3); the ToC popup's outline matching `heading_outline()`, opening from any scroll position, and selection/confirm/cancel each landing on or returning to the correct position (requirements 4-7); search jumping to and highlighting every match on a visible line, and the highlight clearing (requirement 10); horizontal-scroll truncation markers appearing/disappearing at the right boundaries (requirement 11); the width and mouse-capture toggles actually changing state (requirements 12-13); and an explicit `$PAGER` override still taking the external-subprocess path unchanged (Non-goals).
- Manual terminal verification (not mockable): mouse-wheel scroll and horizontal scroll actually move the view in a real terminal; a resize while running redraws at the new size without a keypress (requirement 14); `?` opens a working, scrollable help screen (requirement 15); toggling mouse capture off actually lets a click-drag select text natively (requirement 13).
- `docs/PLAN.md` and any pager-related section of `README.md` updated to describe the new default (owned interactive loop, `$PAGER` override still respected) instead of the old default (always delegating to `less`).

## Peer review

Not applicable; not yet built.

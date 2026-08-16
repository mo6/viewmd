---
id: VIEWMD-0007
title: Navigate a document interactively -- a ToC popup for v1, link navigation for v2
status: proposed
area: [cli, render]
effort: high
created: 2026-08-02
updated: 2026-08-16
accepted_by:
accepted_at:
commits: []
related: [VIEWMD-0006, VIEWMD-0061, VIEWMD-0062]
supersedes: []
changelog:
reason:
---

# Navigate a document interactively -- a ToC popup for v1, link navigation for v2

## Summary

Diverging from GNU Info's node-based pager model (see the Info research note below, kept for its v2 relevance): v1 keeps viewmd's Markdown output scrolling continuously, the way `less` scrolls plain text today -- no nodes, no per-section header line, no mode-line/echo-area split. The one interactive feature v1 adds on top of that plain scrolling is an on-demand table-of-contents popup: press a key at any scroll position, see the document's heading outline (the same `h1`-`h3` structure [VIEWMD-0062](VIEWMD-0062-table-of-contents.md) already renders statically at the top of the document) overlaid on screen, pick an entry, and jump straight to it. Following links interactively -- next/prev link, follow a link's target, back-history -- is explicitly deferred to v2; v1 is scroll-like-`less` plus jump-to-heading, nothing more.

## Motivation / problem

Flagged by the maintainer as a future direction, alongside VIEWMD-0006 (link highlighting): once links are visually distinct, the natural next step is being able to act on them -- especially for `[[wikilink]]`-heavy note collections (Obsidian vaults) and this project's own `issues/*.md`, which cross-reference each other constantly (`[[DELVE-0046]]`, `[related](VIEWMD-0004-...md)`, etc.) with no way today to follow a reference without leaving viewmd. That's still the long-term motivation (v2, below). The more immediate gap the maintainer identified while narrowing v1's scope (2026-08-16): once VIEWMD-0062 gives a document a static ToC at the very top of its output, a reader scrolled deep into a long document (this project's own `README.md`, `docs/PLAN.md`) has no way back to a specific *other* section without paging all the way back to the top and re-reading the ToC there -- a popup reachable from anywhere in the scroll fixes exactly that, without needing link-following machinery at all.

## v1 / v2 split (decided 2026-08-16)

- **v1 (this issue's initial scope):** plain continuous scrolling, matching `less`'s own behavior, plus one addition -- an on-demand ToC popup (see Requirements). No node concept, no `Next`/`Prev`/`Up`, no menu-vs-cross-reference distinction, no mode-line/echo-area split, no link focus/follow. The Info research note below remains useful vocabulary for v2, not something v1 implements.
- **v2 (future, its own scoping pass once v1 has shipped and been used for a while):** link navigation -- jump to the next/previous link, follow a link's target (another local `.md` file, or a heading within the current one), and go back. Requirements deliberately not written yet, same reasoning the original (pre-split) version of this issue gave for deferring the whole thing.

## Requirements

1. MUST scroll rendered Markdown output continuously, line-based, matching `less`'s own scrolling behavior -- not paginated by document node/section the way Info is.
2. MUST NOT implement Info's per-node header line, `Next`/`Prev`/`Up` navigation, or a two-line mode-line/echo-area split -- v1 has no node concept; ordinary scroll-position feedback (e.g. `less`'s own filename/percentage line) is enough.
3. MUST provide an on-demand ToC popup, opened by a dedicated key, that overlays the document's heading outline (the same `h1`-`h3` structure and indentation [VIEWMD-0062](VIEWMD-0062-table-of-contents.md) extracts and renders statically) on top of the current scroll view.
4. MUST let the reader move a selection within the popup (e.g. arrow keys) and confirm it (e.g. Enter), and on confirmation scroll the underlying view to that heading's position and close the popup.
5. MUST let the reader dismiss the popup without jumping (e.g. Esc, or the same key that opened it) and return to exactly the scroll position the popup was opened from.
6. MUST make the popup available regardless of current scroll position -- including when VIEWMD-0062's static ToC at the top of the document is itself off-screen.
7. MUST NOT change any `--no-pager` or non-terminal (piped/redirected) output -- the popup, like the pager itself, is a terminal-interactive-only feature.
8. MUST NOT implement link navigation (jump to next/prev link, follow a link's target, back-history) -- explicitly v2, see Non-goals.

## Non-goals

- Everything from the Info research note below beyond the ToC popup itself: a per-node header line, `Next`/`Prev`/`Up`, the menu-vs-cross-reference distinction, the mode-line/echo-area split, `g`/`t`/`d` node-jump commands, node-scoped search -- deferred; most are unlikely to be needed at all once v1's simpler scroll-plus-popup model has been used for a while, but not ruled out permanently.
- Interactive link following (v2, see the v1/v2 split above) -- jumping to a link, following its target, and a back-history stack are all out of scope for this issue's v1.
- A configurable popup keybinding, popup style, or ToC depth beyond what [VIEWMD-0062](VIEWMD-0062-table-of-contents.md) itself already extracts (`h1`-`h3`) -- v1 reuses that issue's outline as-is.

## Design notes / links

Builds on [VIEWMD-0006](VIEWMD-0006-wikilink-highlighting.md)'s link highlighting for v2 (not v1, which has no link interaction) and directly on [VIEWMD-0062](VIEWMD-0062-table-of-contents.md)'s heading-outline extraction for v1's popup content -- **VIEWMD-0062 is now a blocking dependency of this issue's v1**, not just a prerequisite of convenience as originally filed below, since the popup has nothing to show without that issue's outline data structure existing first. Also interacts with [docs/PLAN.md](../docs/PLAN.md)'s pager design: `viewmd/pager.py` spawns `$PAGER` as an external subprocess today, handing the terminal over entirely once `less` starts -- a popup that can interrupt scrolling to overlay content and later hand control back is not reachable that way. v1 likely needs viewmd to own a minimal interactive scrolling loop itself (raw terminal input, feeding pre-rendered screenfuls, `less`-equivalent scroll keys) rather than delegating to an external `$PAGER` process, even though v1's scrolling behavior otherwise deliberately mimics `less` rather than reinventing it -- this is the single biggest architectural change v1 introduces relative to today's pager, and worth its own design note (and a proof-of-concept, matching this project's usual practice for a UI/architecture-shape decision) once this issue is actually scoped for building.

**Split into preparation issues (2026-08-16):** rather than scoping this whole issue in one pass, two smaller, independently-useful pieces were filed and built ahead of it: [VIEWMD-0061](VIEWMD-0061-global-config-file.md) (a user-global config file -- this issue's own future interactive-pager preferences will want somewhere to live too, and VIEWMD-0062 needs a `toc` on/off key; **implemented**) and [VIEWMD-0062](VIEWMD-0062-table-of-contents.md) (a static table of contents from `h1`-`h3` headings -- the closest thing a non-interactive renderer can produce to Info's `* Menu:` concept below, and a real feature on its own regardless of whether/when this issue itself is ever scoped and built; **still proposed, not yet built** -- see the blocking-dependency note above).

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

None of the above is a v1 requirement (see Requirements, above) -- it's vocabulary reserved for v2's own future scoping pass, once v1 (plain scrolling plus the ToC popup) has shipped and been used for a while.

### Mockup: v1 -- plain scrolling, plus the ToC popup

Illustrative only -- the exact popup key, its border style, and selection-highlight styling are all implementation decisions for the eventual scoping pass, not settled by this mockup. Shown rendering this very issue file, mid-scroll (partway through the "Requirements" section), the way `viewmd VIEWMD-0007-link-navigation.md` would look today plus this issue's own popup addition.

Ordinary scrolling -- no viewmd-specific chrome, just the rendered body and whatever status line the terminal/pager already shows (here, `less`'s own default filename+percentage line, unchanged by this issue per requirement 2):

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

To be defined when this issue is actually scoped for v1 building -- but per the v1/v2 split above, acceptance criteria will need to cover at minimum: plain scroll behavior unchanged from `less` (requirement 1), the popup opening from any scroll position and rendering the same outline VIEWMD-0062 produces (requirements 3, 6), selection/confirm/cancel each returning to the correct scroll position (requirements 4-5), and `--no-pager`/piped output completely unaffected (requirement 7).

## Peer review

Not applicable; not yet built.

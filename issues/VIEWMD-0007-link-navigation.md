---
id: VIEWMD-0007
title: Navigate through a document via its links, making viewmd a Markdown-aware less
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

# Navigate through a document via its links, making viewmd a Markdown-aware less

## Summary

Beyond just paging text, viewmd should let a reader move between a document's links
interactively -- jump to the next/previous link, follow a link's target (another local `.md`
file, or a heading within the current one), and go back -- the way `less` lets you search and
jump, but aware of Markdown structure rather than plain text. This turns viewmd from a
render-and-page tool into something closer to a Markdown-native `less`.

## Motivation / problem

Flagged by the maintainer as a future direction, alongside VIEWMD-0006 (link highlighting):
once links are visually distinct, the natural next step is being able to act on them --
especially for `[[wikilink]]`-heavy note collections (Obsidian vaults) and this project's own
`issues/*.md`, which cross-reference each other constantly (`[[DELVE-0046]]`,
`[related](VIEWMD-0004-...md)`, etc.) with no way today to follow a reference without leaving
viewmd.

## Motivation for filing now without building

This is a large, interactive-mode feature (own keybindings, its own navigation/history state, a
different relationship with the pager than today's "render once, hand off to `less`" model) --
a poor fit to scope or estimate accurately until VIEWMD-0006 (link highlighting) has shipped and
been used for a while. Filed now, `status: proposed`, so the idea and its context aren't lost;
not yet accepted or estimated (`effort: high` is a rough placeholder, not a real estimate).

## Requirements

Deliberately not written yet. Drafting real MUST/SHOULD requirements (interactive keybindings,
how "following" a link to another file works relative to `--no-pager`/piping, how `less`
integration changes when viewmd itself needs to own keypresses instead of delegating to `less`)
needs its own scoping pass before this is ready for the Definition of Ready gate.

## Non-goals

To be defined when this issue is actually scoped.

## Design notes / links

Builds on [VIEWMD-0006](VIEWMD-0006-wikilink-highlighting.md)'s link highlighting -- navigation
needs highlighted, addressable links to jump between first. Also interacts with
[docs/PLAN.md](../docs/PLAN.md)'s pager design (`viewmd/pager.py` spawns `$PAGER` as an
external subprocess today; owning navigation likely means viewmd driving its own interactive
display instead of handing off to `less`, a meaningfully different architecture worth its own
design note when this is scoped).

**Split into preparation issues (2026-08-16):** rather than scoping this whole issue in one pass,
two smaller, independently-useful pieces are filed and built ahead of it:
[VIEWMD-0061](VIEWMD-0061-global-config-file.md) (a user-global config file -- this issue's own
future interactive-pager preferences will want somewhere to live too, and VIEWMD-0062 needs a
`toc` on/off key) and [VIEWMD-0062](VIEWMD-0062-table-of-contents.md) (a static table of contents
from `h1`-`h3` headings -- the closest thing a non-interactive renderer can produce to Info's
`* Menu:` concept below, and a real feature on its own regardless of whether/when this issue itself
is ever scoped and built). Neither is required to land before the other; both are prerequisites of
convenience and shared concepts for this issue, not blocking dependencies of it.

### Research: GNU Info's pager model, as a basis for viewmd's own

Investigated `info(1)` (the stand-alone GNU Info reader, `info --version` distinct from the Emacs
Info mode it also ships) as the closest existing prior art for "a pager whose unit of navigation is
document structure and links, not just lines" -- the model this issue's summary explicitly invokes.
Findings, translated into terms this issue can build requirements from later:

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

None of the above is proposed as a requirement yet (see Requirements, above -- still deliberately
unwritten); it's the vocabulary a future scoping pass can draw MUST/SHOULD language from once
VIEWMD-0006 has shipped.

### Mockup: viewmd as an Info-style pager

Illustrative only -- exact keybindings, header-line fields, and status-line contents are all
implementation decisions for the eventual scoping pass, not settled by this mockup. Shown against
`issues/README.md`-style content, since that's the project's own link-dense document.

Overall screen layout, viewing a node (a `##` section) partway down, with two links visible in the
body and the second one (`[[VIEWMD-0006]]`) currently focused (shown reverse-video, `< >`):

```
viewmd  README.md  Node: Link navigation  Next: Search  Prev: Wikilinks  Up: Features
────────────────────────────────────────────────────────────────────────────────────
  Beyond just paging text, viewmd should let a reader move between a document's
  links interactively -- jump to the next/previous link, follow a link's target
  (another local .md file, or a heading within the current one), and go back --
  the way less lets you search and jump, but aware of Markdown structure rather
  than plain text.

  Flagged by the maintainer as a future direction, alongside [VIEWMD-0006] (link
  highlighting): once links are visually distinct, the natural next step is
  being able to act on them -- especially for [[wikilink]]-heavy note
  collections (Obsidian vaults) and this project's own <[[VIEWMD-0006]]>, which
  cross-reference each other constantly.

  * Menu:
  * Requirements::           Not yet written -- needs its own scoping pass.
  * Design notes: Design notes / links.
  * Acceptance::             To be defined when this issue is scoped.

────────────────────────────────────────────────────────────────────────────────────
 viewmd: README.md  Node: Link navigation, 34 lines  --42%--  2 links, 1 menu item
 [Tab] next link  [Enter] follow  [n/p/u] node  [l] back  [/] search  [?] help  [q] quit
```

Layout notes:

- Row 1: header line -- source file, current node's title, and its `Next`/`Prev`/`Up` neighbors
  (sibling/parent headings), always present regardless of scroll position within the node.
- Middle: the node's rendered Markdown body, scrolled like today's `less` behavior. Inline links
  (`[VIEWMD-0006]`, `[[wikilink]]`) render with VIEWMD-0006's link highlighting; the one currently
  focused for keyboard traversal is additionally reverse-video (`<[[VIEWMD-0006]]>` above). A
  trailing `* Menu:` block -- viewmd's analogue of Info's menu, e.g. synthesized from a section's
  own subheadings or an explicit list of links -- is visually distinct from inline cross-references.
- Second-to-last row: the *mode/status line* (reverse video, always present) -- echoes the header
  line's file/node identity plus a scroll-position indicator (`--Top--` / `--42%--` / `--Bot--`,
  Info's own convention) and a link/menu count for the current node, so "how many things can I Tab
  through from here" is answerable without hunting through the body text.
- Last row: the *echo area* -- blank during normal reading; a keybinding hint by default (as
  mocked above) or a live command prompt (`Goto node: `, `Search: `) while a command is being
  entered, and one-line result/error feedback (`No more links in this node.`) afterward. Keeping
  it separate from the mode line above means a transient prompt/message never overwrites the
  persistent position indicator, matching Info's own separation.

Mockup of the echo area mid-command, e.g. after pressing `g` (goto node):

```
────────────────────────────────────────────────────────────────────────────────────
 viewmd: README.md  Node: Link navigation, 34 lines  --42%--  2 links, 1 menu item
 Goto node: _
```

And after following a cross-file link (`[[VIEWMD-0006]]`) into another document, showing the
history stack now has an entry to `l` (back) to:

```
viewmd  VIEWMD-0006-wikilink-highlighting.md  Node: Top  Next: (none)  Prev: (none)  Up: (none)
────────────────────────────────────────────────────────────────────────────────────
  ...

────────────────────────────────────────────────────────────────────────────────────
 viewmd: VIEWMD-0006-wikilink-highlighting.md  Node: Top, 58 lines  --Top--  1 link
 [l] back to README.md#link-navigation  [Tab] next link  [n/p/u] node  [?] help  [q] quit
```

## Acceptance / verification

To be defined when this issue is actually scoped.

## Peer review

Not applicable; not yet built.

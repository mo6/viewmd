---
id: VIEWMD-0007
title: Navigate through a document via its links, making viewmd a Markdown-aware less
status: proposed
area: [cli, render]
effort: high
created: 2026-08-02
updated: 2026-08-02
accepted_by:
accepted_at:
commits: []
related: [VIEWMD-0006]
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

## Acceptance / verification

To be defined when this issue is actually scoped.

## Peer review

Not applicable; not yet built.

---
id: VIEWMD-0091
title: Add a light/dark theme setting for admonition, table, and heading colors
status: proposed
area: [render, config, cli]
effort:
created: 2026-08-19
updated: 2026-08-19
accepted_by:
accepted_at:
commits: []
related: []
supersedes: []
changelog:
reason:
---

# Add a light/dark theme setting for admonition, table, and heading colors

## Summary

Add a `--theme {dark,light}` flag (and matching `theme` config-file key), defaulting to `dark` (today's existing, unlabeled palette), that selects between two built-in color palettes for the pieces of rendering that currently hardcode colors tuned for a dark terminal background — admonition callout borders/icons (`viewmd/render.py`'s `ViewmdBlockQuote`/`_AdmonitionKind`), the front-matter table, and any other fixed-color styling not already driven by per-diagram `classDef`/color logic.

## Motivation / problem

viewmd's admonition and table colors were evidently chosen against a dark background (unverified against a light one) with no way to override them; a user on a light terminal theme gets whatever contrast results, good or bad, with no escape hatch. Mermaid pie/quadrant charts already branch their palette on color-capability detection (`--color`/`NO_COLOR`/tty), establishing the precedent that viewmd's rendering can be palette-aware — this extends that same idea to a light/dark axis instead of only an on/off one.

## Requirements

1. MUST add `--theme {dark,light}` (default `dark`, i.e. today's existing colors, so this is purely additive — no behavior change for anyone who doesn't pass the flag).
2. MUST add a matching `theme` key to `viewmd/config.py`'s `Config`/`parse_config`, following the same `coalesce(CLI, config, default)` precedence as `--width`/`--color`.
3. MUST apply the `light` theme to at least: admonition callout colors (`_AdmonitionKind` definitions), the front-matter table's styling, and the table-of-contents' heading colors — the specific palette values are an implementation/design decision, not specified numerically here, but MUST be visually verified for adequate contrast on a light background (manual check, screenshot in the PR/issue discussion).
4. MUST NOT change Mermaid diagram coloring, which already has its own color-capability-driven logic (pie/quadrant truecolor fills) — those are out of scope for this issue unless a follow-up decides to unify the two systems.
5. MUST NOT attempt to auto-detect the terminal's actual background color (no OSC 11 query or similar) — explicit `--theme`/config only, since terminal background detection is unreliable across emulators and out of scope here.

## Non-goals

- No fully user-customizable/arbitrary color palette (no `--theme-file`) — two built-in named themes only.
- No auto-detection of light vs. dark terminal background.

## Design notes / links

Precedent: `viewmd/render.py`'s pie-chart rendering already branches its palette on color-capability (truecolor circle vs. monochrome bar) — this issue is the same kind of decision applied to a light/dark axis for the non-Mermaid rendering surfaces.

## Acceptance / verification

New tests in `tests/test_render.py` pinning `--theme light` output for an admonition block and the front-matter table against fixtures, alongside existing `--theme dark`(default)-equivalent fixtures unchanged. `./run-tests.sh` green.

## Peer review


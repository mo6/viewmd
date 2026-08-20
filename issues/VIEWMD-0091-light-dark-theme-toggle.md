---
id: VIEWMD-0091
title: Add a light/dark theme setting for admonition, table, and heading colors
status: in-progress
area: [render, config, cli]
effort: medium
created: 2026-08-19
updated: 2026-08-20
accepted_by: George Moses <gmo6nl@gmail.com>
accepted_at: 2026-08-20
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

- (agent, implementer self-review, not a substitute for an independent pass per AGENTS.md) `--theme {dark,light}` added to `build_parser()`, `Config`/`parse_config` (`theme` key, `THEME_CHOICES`), coalesced `coalesce(args.theme, cfg.theme, "dark")` exactly like `--width`/`--color`. Verified byte-for-byte that an omitted `--theme` (and `--theme dark` explicitly) reproduce pre-change output exactly (diffed against the prior commit's rendering for an admonition+front-matter+ToC doc; the only diff was the OSC8 hyperlink's random `id=`, unrelated to color). Verified CLI overrides config (`--theme dark` over a `theme = light` config file) and config applies when CLI omits the flag, both by diffing full end-to-end `python -m viewmd` output. Light palette sourced from GitHub Primer's own *light*-theme alert tokens (NOTE `#0969da`, TIP `#1a7f37`, IMPORTANT `#8250df`, WARNING `#9a6700`, CAUTION `#cf222e`) — the natural counterpart to the dark palette's already-documented Primer dark-theme source, not an arbitrary independent pick; front-matter table and ToC h2/h3 reuse the NOTE/IMPORTANT blues/purples for one consistent accent rather than inventing new colors. Confirmed `--theme` is plumbed through every render entry point that needed it (`render_markdown`, `render_front_matter_block`, `render_multi_file`, `display_document`/`display_multi_file`, `run`/`run_multi_file` and their `color_kwargs` closures used for link-follow/resize reloads) — caught by running the full suite, which failed three `fake_run` test doubles in `tests/test_main.py`/`tests/test_pager.py` for a missing `theme` kwarg until fixed, a real (if mechanical) plumbing gap the type checker wouldn't have caught since Python doesn't enforce it.
- Known scope narrowing, intentional per the issue: body Markdown headings (not just the ToC's own entries) keep their original color in both themes — only the ToC line's own style is retargeted, since requirement 3 named "the ToC's heading colors" specifically, not body headings; `test_toc_heading_color_differs_between_dark_and_light_theme` asserts this distinction explicitly (dark-magenta only inside `viewmd-toc:`-linked lines, not the later body heading lines reusing the same text). Directory-listing tables and a `.md` file opened by clicking through a directory listing (`run_directory_listing`'s own `open_path`) are not theme-aware, matching that entry point's pre-existing pattern of already omitting `full_front_matter`/`toc` too — not a new regression, but worth the maintainer's awareness if a light-themed directory browse ever becomes a real use case.
- Not independently verified: the light palette's actual on-screen contrast in a real light-background terminal (Primer's own tokens are documented ~4.5:1+ against white, but that is a source-material claim, not something checked against an actual terminal emulator here) — the issue's own acceptance criteria calls for a manual/screenshot check, which a non-interactive agent cannot perform; flagged to the maintainer as still outstanding before merge.

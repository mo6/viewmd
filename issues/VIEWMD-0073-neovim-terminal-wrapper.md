---
id: VIEWMD-0073
title: Neovim terminal-buffer wrapper command for viewmd
status: proposed
area: [docs, cli]
effort:
created: 2026-08-17
updated: 2026-08-17
accepted_by:
accepted_at:
commits: []
related: []
supersedes: []
changelog:
reason:
---

# Neovim terminal-buffer wrapper command for viewmd

## Summary

Ship a small standalone Neovim plugin (`viewmd.nvim`, its own repo, not code inside this
package) that adds a `:Viewmd` command opening the current Markdown buffer's rendered ANSI
output — headings, tables, Mermaid diagrams, everything viewmd already renders — in a Neovim
`:terminal` split. This is the "thin wrapper" integration: no new rendering logic, just invoking
the existing `viewmd` CLI and letting Neovim's terminal buffer interpret the ANSI it already
emits.

## Motivation / problem

viewmd already produces plain ANSI on stdout via `--no-pager --color always` (`viewmd/pager.py`,
`viewmd/__main__.py`), which is exactly the input Neovim's `:terminal` buffers are built to
display — they interpret SGR color codes natively. There is currently no way to preview a
Markdown file's full viewmd rendering (in particular its Mermaid diagram support, which most
editor Markdown previews lack entirely) without leaving the editor for a separate terminal pane.
A thin wrapper closes that gap with a small, self-contained plugin rather than new rendering code
in viewmd itself.

## Requirements

1. MUST live in its own repository (`viewmd.nvim` or similar), not inside `viewmd/` — this issue
   only tracks what viewmd itself needs to expose/guarantee for such a plugin to work; it does
   not add a plugin to this package.
2. MUST document, in this repo, the exact invocation a Neovim (or other editor) integration
   should use: `viewmd --no-pager --color always --width <N> <path>`, and confirm this remains a
   stable, non-interactive, pipe-safe entry point (no pager, no prompts, exits after one render).
3. MUST confirm `--width` accepts a caller-supplied column count (already true per
   `viewmd/__main__.py`'s `_resolve_width`) so a wrapper can pass the host window's width and get
   correctly wrapped tables/diagrams rather than relying on terminal auto-detection.
4. SHOULD document, for `viewmd.nvim`'s own README (not this repo), the intended UX: a `:Viewmd`
   command that opens a vertical/horizontal split, runs `termopen()` (or `jobstart`/`:term`) with
   the command from (2), sized to the split's width, and re-runs on `VimResized` for that window.
5. MUST NOT add any Neovim/Lua/editor-specific code to the `viewmd` Python package itself — the
   CLI's job ends at "emit correct ANSI to stdout when asked."
6. SHOULD note the known limitation up front (for `viewmd.nvim`'s own docs): a `:terminal` buffer
   is pty-backed, so it won't behave like a normal editable/searchable Vim buffer (no native
   `/search`, folding, or user colorscheme) — that's the tradeoff of the thin-wrapper approach
   versus a future ANSI-to-highlight buffer-native version.

## Non-goals

- A buffer-native renderer that converts viewmd's ANSI into `nvim_buf_add_highlight`/extmarks so
  output lives in a normal scratch buffer. That's a materially larger, separate effort (a real
  ANSI→highlight translator, resize-triggered re-render into a buffer) and would be its own
  future issue if pursued.
- Vim8/9 (non-Neovim) support — no equivalently clean native ANSI-in-terminal-buffer story exists
  there today.
- Building/publishing the `viewmd.nvim` plugin itself as part of this repo's release process.

## Design notes / links

- `viewmd/pager.py`: `display_document()`/`should_page()` — confirms `--no-pager` bypasses the
  pager entirely and just prints ANSI, which is the integration point.
- `viewmd/__main__.py`: `_resolve_width()` — confirms `--width` takes an explicit column count,
  needed so a wrapper can pass the split's width instead of the whole terminal's.

## Acceptance / verification

- Manual: from a Neovim terminal split, run
  `viewmd --no-pager --color always --width 80 README.md` directly and confirm the split renders
  correct colors, tables, and (on a file with one) a Mermaid diagram, with no pager invoked and
  no non-zero exit.
- `./run-tests.sh` stays green (no code changes expected in this package beyond, if needed, a
  short mention in `docs/PLAN.md` or a README pointer to the existence of `viewmd.nvim`).

## Peer review


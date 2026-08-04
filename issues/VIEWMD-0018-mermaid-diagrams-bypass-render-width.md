---
id: VIEWMD-0018
title: Mermaid diagrams shouldn't be wrapped/capped to the render width
status: in-progress
area: [render, mermaid]
effort: medium
created: 2026-08-04
updated: 2026-08-04
accepted_by: George Moses
accepted_at: 2026-08-04
commits: []
related: [VIEWMD-0019]
supersedes: []
changelog:
reason:
---

# Mermaid diagrams shouldn't be wrapped/capped to the render width

## Summary

Mermaid diagrams wider than the render width are word-wrapped and padded like ordinary text, which interleaves box tops, labels, and lifelines onto separate rows and destroys the 2D art. Because the default width is capped at 100 columns, this happens even on a wide terminal. Mermaid art should bypass console-width wrapping and keep its own natural width.

## Motivation / problem

The whole document is rendered by one Rich `Console` at a fixed width (`viewmd/render.py:48,54`), and Rich word-wraps + right-pads code blocks to that width. The default width is capped (`DEFAULT_MAX_WIDTH = 100`, `_resolve_width` returns `min(100, terminal_width)`, `viewmd/__main__.py:17,37`), so a wide terminal still wraps at 100 unless `--width full`/`--width N` is passed. Mermaid art is spliced back into the body as a plain ` ``` ` fence (`viewmd/mermaid/preprocess.py`), so it goes through the same width-bound code-block path as ordinary code. The sequence renderer already emits correct art at the diagram's natural width; it's Rich's re-wrapping to the console width that mangles it. Real-world trigger: 7-participant sequence diagrams in a wide SAD document.

## Requirements

1. MUST render mermaid ASCII art at its own natural width, unaffected by the document's render width (`--width`/terminal-derived cap).
2. MUST NOT apply Rich's word-wrap/right-pad `CodeBlock` treatment to mermaid output.
3. MUST distinguish mermaid-generated output from ordinary fenced code blocks (e.g. a sentinel info-string or a separate render path), so this change does not also affect plain code blocks (see the conflict noted below, tracked as [[VIEWMD-0019]]).
4. SHOULD decide and document whether the pager should chop long lines (`less -S`) for overflowing diagrams, versus leaving the current soft-wrap-inside-`less` behavior (`viewmd/pager.py:8`, currently `-R -F -X`, no `-S`).

## Non-goals

Redesigning the mermaid rendering algorithm itself, or changing how diagrams are parsed, is out of scope — this is purely about how already-rendered diagram art reaches the terminal/pager.

## Design notes / links

This issue conflicts with the code-block width issue ([[VIEWMD-0019]]): since mermaid is currently rendered *as* a code block, any change to how code blocks handle overly-wide lines needs to distinguish diagram art from ordinary code, via a sentinel info-string or a distinct render path. **Note:** VIEWMD-0019 originally planned "opposite treatment" (diagrams full-width, code cropped at render width), but was revised after testing to give both the same full-natural-width treatment — see VIEWMD-0019's peer review for why. The sentinel/distinguishing mechanism this issue calls for is still exactly what makes that possible; it just routes both to "don't lose content" instead of one path cropping.

Source: https://github.com/mo6/viewmd/issues/2

## Acceptance / verification

- Reproduction case renders each diagram row intact (not folded/padded at 100 columns) even at the default width cap:
  ````
  ```mermaid
  sequenceDiagram
      participant AAAAAAAAAA as First service with a long name
      participant BBBBBBBBBB as Second service with a long name
      participant CCCCCCCCCC as Third service with a long name
      AAAAAAAAAA->>BBBBBBBBBB: do something
      BBBBBBBBBB->>CCCCCCCCCC: forward it
  ```
  ````
- A regression test confirming an ordinary (non-mermaid) code block is unaffected by this change (still governed by [[VIEWMD-0019]]'s behavior).
- `./run-tests.sh` green.

## Peer review

- **Cursor Grok** (agent), 2026-08-04: accept. Shared sentinel `mermaid-rendered` in `viewmd/mermaid/preprocess.py` discriminates the two paths; `ViewmdCodeBlock` emits raw `Segment`s for that sentinel (natural width, no pad/wrap) and `Syntax(..., word_wrap=False, padding=0)` for ordinary fences (hard crop to render width). Body print uses `crop=False` so wide mermaid rows survive Rich's post-render crop without disabling paragraph wrapping. Open questions resolved: (req. 4) hard crop, not ellipsis — matches `Syntax`'s native `word_wrap=False` behavior and `less -S` semantics, no invented marker; (req. 4) added `-S` to `DEFAULT_PAGER` so less chops long diagram rows instead of soft-wrapping them (overridable via `$PAGER`). Reproduction at width 100 keeps all three actor labels on one intact row; 120-char code line yields exactly one 100-column line. Discrimination regression covers both directions. `./run-tests.sh` green (192 passed).
- **Claude** (agent), 2026-08-04: independent re-verification. Confirmed all file:line references against current code, reproduced both original GH-issue repros directly (diagram intact, code line hard-cropped to one line), and confirmed the sentinel correctly discriminates in a combined mermaid+code document. Checked `crop=False` for side effects on other wide content (tables, long unbreakable words in paragraphs) -- none, they still wrap/crop to width. Found one unrequested regression: `padding=0` on ordinary fences dropped Rich's prior `padding=1`, silently removing the blank line above/below and left margin every code block used to have (visible in `docs/example.md`'s Python sample, confirmed side-by-side against `develop`). Fixed by restoring `padding=1` -- verified this doesn't conflict with req. 1, since `Syntax`'s own no-wrap crop happens independently of the top-level `crop=False`; updated `tests/test_render.py::test_long_code_block_line_is_truncated_not_wrapped`, which had baked in the no-padding assumption via an exact-string match, to assert the padding-aware invariant (single 100-column line, full 120-char content never let through) instead. `./run-tests.sh` green (192 passed) after the fix.
- **George Moses** (maintainer), 2026-08-04: accept, "I've tested it and it works correct."


---
id: VIEWMD-0019
title: Long lines in code blocks should be cut off, not wrapped
status: in-progress
area: [render]
effort: medium
created: 2026-08-04
updated: 2026-08-04
accepted_by: George Moses
accepted_at: 2026-08-04
commits: []
related: [VIEWMD-0018]
supersedes: []
changelog:
reason:
---

# Long lines in code blocks should be cut off, not wrapped

## Summary

A line inside a fenced ` ``` ` code block that is longer than the render width is currently wrapped onto additional lines. It should instead be cut off (truncated) at the render width, so long code lines don't reflow into the surrounding layout.

## Motivation / problem

The document is rendered by a single Rich `Console` at a fixed width (`viewmd/render.py:48,54`). Rich's default Markdown `CodeBlock` word-wraps and right-pads code content to the console width, and Rich 15.0.0 hardcodes this in the default code-block element, so there's no config flag to flip. Example: a code block containing one 120-character line, rendered at width 100, currently produces two output lines (100 chars + 20 chars, both padded to 100) instead of one truncated line.

## Requirements

1. MUST render fenced code-block lines with `no_wrap=True` (or equivalent) so a line longer than the render width is cut at the render width instead of folding onto additional lines.
2. MUST implement this via a custom Markdown `CodeBlock` element override wired into the `Markdown(...)` call in `viewmd/render.py:54`, since Rich has no built-in flag for this.
3. MUST NOT apply this truncation to mermaid-rendered diagram output — that must keep its natural width per [[VIEWMD-0018]]. This requires distinguishing mermaid output from ordinary fenced code (sentinel info-string or separate render path), coordinated with [[VIEWMD-0018]].
4. SHOULD resolve, as part of implementation, whether truncation is a hard crop (silent cut) or marks the cut point with an ellipsis (`…`) — open question for peer review.

## Non-goals

Changing how mermaid diagram art is rendered or wrapped is out of scope here — that's [[VIEWMD-0018]]; this issue only concerns ordinary fenced code blocks.

## Design notes / links

Depends on / conflicts with [[VIEWMD-0018]] (the Mermaid width issue): mermaid art is currently rendered *as* a code block (`viewmd/mermaid/preprocess.py`), and that issue wants diagrams *not* truncated. Truncating all code blocks would break diagrams unless the two are coordinated via a shared sentinel/distinguishing mechanism.

Source: https://github.com/mo6/viewmd/issues/3

## Acceptance / verification

- Reproduction case: a code block containing a single 120-character line, rendered at width 100, produces exactly one output line, truncated at 100 columns (with or without an ellipsis marker, per the resolved open question).
- A regression test confirming mermaid diagram output is unaffected by this truncation (covered jointly with [[VIEWMD-0018]]).
- `./run-tests.sh` green.

## Peer review

- **Cursor Grok** (agent), 2026-08-04: accept. Implemented jointly with VIEWMD-0018 via the shared `mermaid-rendered` sentinel. Ordinary fences go through `ViewmdCodeBlock` → `Syntax(..., word_wrap=False, padding=0)`, which hard-crops at the console width; mermaid-tagged fences take the Segment path and are unaffected. Open question (req. 4): hard crop rather than an ellipsis marker — silent cut matches Rich's native no-wrap crop and is consistent with the pager's new `-S` chop; an ellipsis would invent content that was never in the source. Reproduction: 120-char line at width 100 → exactly one 100-column output line. Cross-issue discrimination test confirms ordinary code still truncates when mermaid bypasses. `./run-tests.sh` green (192 passed).


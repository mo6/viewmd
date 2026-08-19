---
id: VIEWMD-0086
title: Decide and document how Obsidian embed/transclusion syntax (![[Target]]) is handled
status: proposed
area: [wikilinks, render, docs]
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

# Decide and document how Obsidian embed/transclusion syntax (![[Target]]) is handled

## Summary

`viewmd/wikilinks.py` rewrites `[[Target]]`/`[[Target|Display]]` wikilinks but never mentions Obsidian's embed/transclusion form, `![[Target]]` (and `![[Target#Heading]]`/`![[Target#^block]]`), which today falls through to the Markdown parser un-rewritten and renders however Rich happens to treat a literal `![[...]]` string. This issue is first about making that behavior a deliberate, tested, documented choice — full recursive embedding of another note's content is an explicit non-goal unless a follow-up issue decides otherwise.

## Motivation / problem

`![[Target]]` is common enough in real Obsidian vaults that its current fate (whatever falling through to Rich's Markdown parser produces) is effectively undefined behavior — no test pins it, no doc line describes it. A vault with these in real notes hits an unspecified render with no way to know if it's a bug.

## Requirements

1. MUST add a test in `tests/test_wikilinks.py` pinning today's actual output for `![[Target]]` and `![[Target|Display]]` through `rewrite_wikilinks`/full render, whatever that turns out to be, as a documented baseline before any behavior change.
2. MUST choose one explicit treatment and implement it consistently: (a) render as a plain, clearly-marked, non-broken link (matching non-embed wikilink styling, perhaps with a distinguishing glyph) since full transclusion is out of scope, or (b) leave the raw `![[Target]]` text visibly intact rather than however Rich's default image-syntax handling mangles it. Pick (a) unless the peer review prefers (b); either is acceptable as long as it's a real decision, not an accident.
3. MUST NOT attempt to inline the target note's actual content (no recursive file reads, no cross-file embedding) — that's a materially larger feature (needs cycle detection, its own rendering pass, path resolution shared with VIEWMD-0082) left for a future issue if wanted.
4. MUST update `README.md`'s wikilinks paragraph to state the chosen behavior for `![[...]]` explicitly.

## Non-goals

- Full transclusion (rendering the embedded note's actual body inline).
- Embedding non-Markdown targets (images, PDFs) — that's covered separately by VIEWMD-0088 (image handling) if pursued.

## Design notes / links

Sits next to `viewmd/wikilinks.py`'s existing `_WIKILINK_RE`; the `!` prefix is the only new thing to detect — reuse the existing fence/inline-code skipping logic unchanged.

## Acceptance / verification

New/updated tests in `tests/test_wikilinks.py` and `tests/test_render.py` covering the chosen rendering for `![[Target]]`, `![[Target|Display]]`, inside/outside code fences. `./run-tests.sh` green.

## Peer review


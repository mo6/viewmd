---
id: VIEWMD-0086
title: Decide and document how Obsidian embed/transclusion syntax (![[Target]]) is handled
status: implemented
area: [wikilinks, render, docs]
effort: low
created: 2026-08-19
updated: 2026-08-19
accepted_by: George Moses <gmo6nl@gmail.com>
accepted_at: 2026-08-19
commits: [ea38277]
related: [VIEWMD-0099]
supersedes: []
changelog: "[1.45.0]"
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

- (agent, implementer) Implemented treatment (a): `![[Target]]`/`![[Target|Display]]` (and `#Heading`/`#^block` suffixes) now rewrite to the same `[Display](<wikilink:Target>)` link form as a plain wikilink, with display text prefixed by a distinguishing 📎 glyph; no target content is inlined. Pinned the pre-change baseline (un-rewritten `!` fell through to Rich's broken-image-placeholder rendering of `![Target](<wikilink:Target>)`) as a documented historical note in `tests/test_wikilinks.py`/`tests/test_render.py` before changing behavior. `./run-tests.sh` pytest/ruff/pip-audit all green; this is a work summary from the implementing agent, not an independent review -- a genuinely independent pass is still needed before the maintainer's sign-off per `issues/AGILE.md`.
- (agent, independent reviewer) Reviewed `viewmd/wikilinks.py`'s diff line by line: the new `![[`-prefixed branch runs before the plain `[[` branch and correctly falls through to literal-character handling (leaving `!` untouched, then matching `[[` on the next iteration) when `_WIKILINK_RE` fails to match, so an unterminated `![[foo` degrades the same way an unterminated `[[foo` already did. `#Heading`/`#^block` suffixes are carried through verbatim in `target`, matching a plain wikilink's own handling, per requirement 2's "reuse the existing fence/inline-code skipping logic unchanged." README's wikilinks paragraph states the chosen behavior explicitly (requirement 4). Also drove the change manually end-to-end (`./viewmd.sh` against a scratch file with real target `.md` files) to confirm click-navigation resolves embed hrefs the same way plain wikilink hrefs do, and confirmed the fence-detection gap found during that manual pass (`> ` `` ``` `` blockquote-nested fences not recognized) is pre-existing back to VIEWMD-0006, not introduced by this diff -- filed separately as VIEWMD-0099 rather than blocking this issue. `./run-tests.sh` reconfirmed green after merge to `develop`. Verdict: approve, no changes requested.
- (maintainer, George Moses) 2026-08-19: "accept and close issue 86" -- explicit landing approval given in-conversation.


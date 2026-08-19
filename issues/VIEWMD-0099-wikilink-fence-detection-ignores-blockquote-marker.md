---
id: VIEWMD-0099
title: Wikilink fence detection misses code fences indented under a blockquote marker
status: proposed
area: [wikilinks]
effort:
created: 2026-08-19
updated: 2026-08-19
accepted_by:
accepted_at:
commits: []
related: [VIEWMD-0006, VIEWMD-0086]
supersedes: []
changelog:
reason:
---

# Wikilink fence detection misses code fences indented under a blockquote marker

## Summary

`viewmd.wikilinks.rewrite_wikilinks`'s fence-toggle check (`_FENCE_RE.match(line.lstrip())`) only strips leading whitespace before testing for a ` ``` `/`~~~` fence marker, so a fence line prefixed with a blockquote marker (e.g. `> ` ```` ``` ````) is never recognized as a fence — wikilinks and embed-wikilinks inside such a code block get rewritten instead of left literal.

## Motivation / problem

The module's own docstring claims "a fence indented under a list item or blockquote is still recognized," which is only half true: list-item indentation (plain leading spaces) works because `.lstrip()` strips it, but a blockquote's `>` marker is not whitespace, so `.lstrip()` leaves it in place and `_FENCE_RE` never matches. A real note with a fenced code block quoted inside a blockquote (a common Markdown pattern) gets its `[[...]]`/`![[...]]` text silently corrupted into a rewritten link instead of rendering literally. Found via manual testing of VIEWMD-0086; confirmed pre-existing back to VIEWMD-0006 (affects plain wikilinks too, not just embeds) and unrelated to VIEWMD-0086's own diff.

## Requirements

1. MUST recognize a fence line whose content, after stripping both leading whitespace and one or more leading `>` blockquote markers (with their own optional interspersed whitespace, matching how Markdown nests blockquotes), starts with ` ``` ` or `~~~`.
2. MUST leave `[[...]]` and `![[...]]` text inside such a blockquote-nested fenced code block untouched by `rewrite_wikilinks`, matching the existing behavior for a plain (non-blockquoted) fenced code block.
3. MUST NOT change behavior for any currently-passing case (plain fences, list-item-indented fences, inline code spans).
4. SHOULD correct the module docstring's "list item or blockquote" claim to match whatever the actual fix covers (including nested blockquotes, if in scope, or narrowing the claim if not).

## Non-goals

- No general blockquote-aware Markdown parsing elsewhere in `viewmd/wikilinks.py` — this is narrowly about fence *detection* for the purpose of skipping wikilink rewriting, not a full blockquote model.

## Design notes / links

`viewmd/wikilinks.py`'s `_FENCE_RE = re.compile(r"^(```|~~~)")` and its use at `rewrite_wikilinks`'s `if _FENCE_RE.match(line.lstrip()):` line are the two things to change together.

## Acceptance / verification

New tests in `tests/test_wikilinks.py` covering: a `[[Target]]` and an `![[Target]]` each inside a fenced code block nested under a single `>` blockquote marker, both asserted untouched. `./run-tests.sh` green.

## Peer review


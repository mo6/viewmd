---
id: VIEWMD-0099
title: Wikilink fence detection misses code fences indented under a blockquote marker
status: in-progress
area: [wikilinks]
effort: low
created: 2026-08-19
updated: 2026-08-19
accepted_by: George Moses <gmo6nl@gmail.com>
accepted_at: 2026-08-19
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

- (agent, implementer) Added `_BLOCKQUOTE_PREFIX_RE = re.compile(r"^(?:\s*>)*\s*")` and changed `rewrite_wikilinks`'s fence check from `_FENCE_RE.match(line.lstrip())` to `_FENCE_RE.match(_BLOCKQUOTE_PREFIX_RE.sub("", line, count=1))`, so any number of nested `>` markers (not just a single level) is stripped before the fence test — covers requirement 1 and goes slightly beyond it (arbitrary nesting, not just one marker). Corrected the `rewrite_wikilinks` docstring's "list item or blockquote" claim to describe the actual behavior (requirement 4). Added three tests: single-level blockquote-nested fence for both a plain and an embed wikilink, plus a two-level-nested case. Manually verified plain fences, list-indented fences, and inline code spans are unaffected (requirement 3). `./run-tests.sh` green (1139 passed, ruff, pip-audit, completions, issues).
- (agent, independent reviewer) Reviewed the diff: `_BLOCKQUOTE_PREFIX_RE`'s `(?:\s*>)*\s*` matches an empty string on a non-blockquoted line, so `_FENCE_RE.match(_BLOCKQUOTE_PREFIX_RE.sub("", line, count=1))` is exactly equivalent to the old `_FENCE_RE.match(line.lstrip())` in that case — confirms requirement 3 (no behavior change for plain/list-indented fences) structurally, not just by the passing test suite. A blockquoted *non-fence* line (e.g. `> [[Note]]`) still fails the fence match on its stripped remainder and falls through to `_rewrite_line` unchanged, correctly leaving existing blockquote-wikilink rewriting untouched. Traced both new tests by hand against the fix and confirmed the toggle correctly opens/closes on matching blockquote-prefixed fence pairs. `./run-tests.sh` reconfirmed green. Verdict: approve, no changes requested.

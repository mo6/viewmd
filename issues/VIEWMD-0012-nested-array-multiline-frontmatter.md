---
id: VIEWMD-0012
title: Parse nested mappings, list/array-of-object values, and multiline block scalars in front matter without cross-key corruption
status: in-progress
area: [render]
effort: medium
created: 2026-08-03
updated: 2026-08-03
accepted_by: George Moses
accepted_at: 2026-08-03
commits: []
related: [VIEWMD-0004, VIEWMD-0005, VIEWMD-0011]
supersedes: []
changelog:
reason:
---

# Parse nested mappings, list/array-of-object values, and multiline block scalars in front matter without cross-key corruption

## Summary

VIEWMD-0011's investigation, run against real test documents, found that `viewmd/frontmatter.py`
doesn't just decline to support nested YAML structures -- it silently mis-renders them, including
one outright correctness bug: a nested key can overwrite an unrelated top-level key of the same
name. This issue implements the missing pieces the investigation flagged as worth fixing --
nested mappings, block-list (`- item`) arrays, array-of-objects, and multiline block scalars (`|`
and `>`) -- so each renders as its own recognizable value instead of corrupting, or silently
dropping, other fields.

## Motivation / problem

From VIEWMD-0011's recorded findings (`issues/archive/VIEWMD-0011-*.md` once archived):

- **Nested objects**: indentation is ignored entirely, so `seo:` (no value) is dropped and its
  child `title:` is treated as a second top-level `title:` line -- silently overwriting the
  document's real title in the table. This is the one active correctness bug, not just a gap.
- **Array of objects** (`authors:` with `- name: ... / email: ...` items): each item line is
  parsed as its own flat key; only the last item's fields survive, earlier entries are silently
  lost.
- **Block-list arrays** (`tags:` with `- item` lines, no `:` on the item line): silently dropped
  with no row in the table at all, unlike the already-working `[a, b, c]` bracket form.
- **Multiline block scalars** (`|` literal, `>` folded): only the marker character itself is
  captured; the actual content lines are dropped (each continuation line has no `:` and is
  skipped like a bare list item).

Dates, quoted scalars, and boolean-alias (`yes`/`no`) values already render correctly per
VIEWMD-0011 and need no change here.

## Requirements

1. MUST NOT let a nested key overwrite an unrelated top-level key of the same name. A key
   nested under a parent (e.g. `seo.title`) MUST be distinguishable in the parsed result from a
   top-level key of the same short name (e.g. `title`) -- e.g. a dotted path (`seo.title`) as the
   display key.
2. MUST render a block-list array (`key:` followed by `- item` lines, one scalar per item) as a
   value equivalent to today's `[a, b, c]` bracket form (comma-joined), so `tags:` with `- item`
   lines and `tags: [item, ...]` produce the same displayed value for the same data.
3. MUST render an array-of-objects (`key:` followed by `- field: value` items, each item itself a
   mapping) so that every item's data is visible in the output -- not just the last item -- and
   items are distinguishable from each other in the rendered value.
4. MUST render a literal block scalar (`|`) preserving its internal line breaks, and a folded
   block scalar (`>`) with internal line breaks collapsed to spaces, matching standard YAML block
   scalar semantics.
5. MUST continue to pass every existing case covered by VIEWMD-0004 and VIEWMD-0005 (flat
   `key: value`, `[a, b, c]` bracket lists, quote-stripping, comment/blank-line skipping, the
   empty-block and unterminated-block fallbacks, `drop_empty` behavior) unchanged.
6. MUST NOT introduce a YAML parsing dependency -- extend the existing hand-written parser in
   `viewmd/frontmatter.py`, per the rationale in VIEWMD-0004's Design notes and `docs/PLAN.md`.

## Non-goals

- TOML (`+++`) or JSON (`;;;`) front-matter formats. VIEWMD-0011 confirmed these already degrade
  safely (clean fallback to "no front matter detected", per VIEWMD-0004 requirement 5) and remain
  out of scope, unchanged from VIEWMD-0004's Non-goals.
- Full YAML fidelity (anchors/aliases, flow mappings `{a: b}`, multi-document streams, arbitrary
  nesting depth beyond what the test fixtures below exercise). This is still not a general YAML
  parser -- only the specific shapes VIEWMD-0011 tested and flagged.
- Typed values (booleans/numbers/dates as anything other than display strings). VIEWMD-0011 found
  no bug here; out of scope.

## Design notes / links

Builds on `viewmd/frontmatter.py` (VIEWMD-0004) and its `drop_empty` (VIEWMD-0005). The exact
internal representation for nested/array values (dotted keys vs. a nested-table rendering, one
row per array item vs. a single joined cell) is an implementation decision for the branch, not
fixed by this issue -- but requirement 1 (no cross-key overwrite) and requirement 3 (no silent
data loss across array items) are the hard constraints either representation must satisfy.
Reuses the test fixtures already written for VIEWMD-0011 in
`tests/fixtures/frontmatter-advanced/` (`01-nested-objects.md`, `02-array-of-objects.md`,
`03-dash-list-arrays.md`, `04-multiline-strings.md`, `09-kitchen-sink.md`) as the acceptance
fixtures for this issue -- render them before/after to show the fix.

## Acceptance / verification

- `./run-tests.sh` green; new unit tests in `tests/test_frontmatter.py` cover requirements 1-4
  directly (nested-key non-collision, block-list array, array-of-objects, both block-scalar
  styles), plus a regression case asserting VIEWMD-0004/0005's existing fixtures still parse
  identically to before (requirement 5).
- Manual: re-render `tests/fixtures/frontmatter-advanced/01-nested-objects.md`,
  `02-array-of-objects.md`, `03-dash-list-arrays.md`, `04-multiline-strings.md`, and
  `09-kitchen-sink.md` and confirm against VIEWMD-0011's recorded findings that: the real
  top-level `title` in `01-nested-objects.md` no longer gets overwritten by the nested `seo.title`;
  both authors appear in `02-array-of-objects.md`; `tags` in `03-dash-list-arrays.md` renders
  the same as `tags_bracket_form`; both block scalars in `04-multiline-strings.md` show their
  actual content, not just `|`/`>`.

## Peer review

- **Claude (Sonnet 5)** (agent), 2026-08-03: PASS. `./run-tests.sh` green (61 tests, ruff clean,
  pip-audit clean, issues index current); 7 new unit tests in `tests/test_frontmatter.py` cover
  requirements 1-4 directly plus a requirement-5 regression case. Manually re-rendered all five
  VIEWMD-0011 fixtures with `./viewmd.sh --color=never`: `01-nested-objects.md`'s top-level
  `title` no longer collides with `seo.title` (now two distinct rows); `02-array-of-objects.md`
  shows both authors; `03-dash-list-arrays.md`'s `tags` renders identically to
  `tags_bracket_form`; `04-multiline-strings.md` shows the literal block's actual line breaks and
  the folded block's actual space-joined text, not the `|`/`>` markers; `09-kitchen-sink.md`
  combines all of the above correctly in one document. Confirmed TOML/JSON front matter
  (`07-toml-frontmatter.md`, `08-json-frontmatter.md`) still fall back unchanged (out of scope,
  per Non-goals). Also dogfooded by rendering this issue's own front matter -- unaffected.


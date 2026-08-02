---
id: VIEWMD-0005
title: Hide empty front-matter fields by default; --full-front-matter shows them all
status: implemented
area: [render, cli]
effort: low
created: 2026-08-02
updated: 2026-08-02
accepted_by: George Moses
accepted_at: 2026-08-02
commits: [a5778fb]
related: [VIEWMD-0004]
supersedes: []
changelog: "[0.4.0]"
reason:
---

# Hide empty front-matter fields by default; --full-front-matter shows them all

## Summary

VIEWMD-0004's front-matter table shows every parsed field, including ones with no value (e.g.
`accepted_at:` before an issue is accepted, or `related: []`). By default the table should show
only fields that have a value; a new `--full-front-matter` flag opts back into seeing every
field, empty ones included.

## Motivation / problem

Reported by the maintainer: this project's own issue files carry several fields that are
routinely blank (`accepted_by`, `accepted_at`, `commits`, `related`, `supersedes`, `reason`,
`changelog`) until an issue reaches a particular lifecycle stage. Showing every blank row by
default clutters the table with rows that carry no information; but the full picture (including
what's still blank) is sometimes exactly what's wanted, so it shouldn't be lost, only opt-in.

## Requirements

1. MUST omit a front-matter field from the rendered table by default when its parsed value is
   empty (an empty string after whitespace-trimming; this includes an empty `[]` list, which
   VIEWMD-0004 already renders as an empty joined string).
2. MUST support `--full-front-matter` to render every parsed field, empty ones included,
   restoring VIEWMD-0004's original behavior.
3. MUST still apply VIEWMD-0004 requirement 7 (skip the table and divider entirely when there is
   nothing to show) using the *filtered* set by default -- a front-matter block whose every field
   is empty renders no table unless `--full-front-matter` is given.
4. MUST NOT change how a field's value itself renders (no change to list-joining, quote-stripping,
   etc. from VIEWMD-0004) -- this issue only changes which rows are included.

## Non-goals

- Any change to which fields get *parsed* (VIEWMD-0004's flat key/value + `[a, b]`-list parsing
  is unchanged); this is purely a display-time filter.
- A per-field allow/deny list; "empty or not" is the only filter this issue adds.

## Design notes / links

Extends [VIEWMD-0004](VIEWMD-0004-front-matter-table.md); see its entry in
[docs/PLAN.md](../docs/PLAN.md) for the front-matter parsing rationale, unchanged here. The
empty-field filter is a small pure function in `viewmd/frontmatter.py` (alongside
`parse_front_matter`), so it's unit-testable the same way, and `render_markdown()` gains a
`full_front_matter: bool` parameter that `__main__.py` wires to the new flag.

## Acceptance / verification

- `./run-tests.sh` green; new unit tests cover the filter function directly (drops empty-string
  values, drops values that are only whitespace, keeps non-empty ones, empty input yields empty
  output) and `tests/test_render.py` gains cases for: a file with a mix of empty/non-empty fields
  renders only the non-empty ones by default; the same file with `full_front_matter=True` (or via
  CLI, `--full-front-matter`) shows every field; a file where every field is empty renders no
  table by default but does with `--full-front-matter`.
- Manual: render one of this project's own archived issues (which has several blank fields:
  `related`, `supersedes`, `reason`) with and without `--full-front-matter` and confirm the blank
  rows disappear/reappear accordingly.

## Peer review

- **Claude (Sonnet 5)** (agent), 2026-08-02: PASS. `./run-tests.sh` green (45 tests, ruff clean,
  issues index current). Verified manually on `issues/archive/VIEWMD-0004-front-matter-table.md`
  (which has blank `related`/`supersedes`/`reason`): those rows are absent by default and
  reappear with `--full-front-matter`.

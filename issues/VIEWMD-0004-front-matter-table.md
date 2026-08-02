---
id: VIEWMD-0004
title: Render YAML front matter as a table, clearly separated from the document body
status: in-progress
area: [render]
effort: medium
created: 2026-08-02
updated: 2026-08-02
accepted_by: George Moses
accepted_at: 2026-08-02
commits: []
related: []
supersedes: []
changelog:
reason:
---

# Render YAML front matter as a table, clearly separated from the document body

## Summary

Many `.md` files (this project's own `issues/*.md` included) open with a YAML front-matter block
(`--- ... ---`) of key/value metadata. Today it renders as a plain horizontal rule followed by
raw `key: value` text mixed into the document body, indistinguishable from prose. Front matter
should render as a two-column table at the top of the document, with a clear visual divider
before the rest of the body.

## Motivation / problem

Reported by the maintainer: front matter should be shown as a table at the start of the
document, clearly separated from the rest of the text, rather than rendered inline as prose.

## Requirements

1. MUST detect a leading YAML front-matter block: the file's first line is exactly `---`, and a
   later line that is exactly `---` closes it; everything between is the front matter, everything
   after is the document body.
2. MUST parse the front-matter block as flat `key: value` pairs, one per line, matching this
   project's own issue front-matter shape (see `tools/issues.py`'s parser, which this reuses the
   approach of): a `[a, b, c]`-style bracketed value MUST render as a comma-joined list; a
   quoted scalar MUST have its quotes stripped; blank lines and `#`-comment lines MUST be
   skipped. This is deliberately not a full YAML parser (see Non-goals).
3. MUST render the parsed pairs as a table (key column, value column) before the rendered
   Markdown body.
4. MUST render a clear visual divider between the front-matter table and the body (distinct from
   Markdown's own horizontal-rule rendering, so the two aren't visually confused).
5. MUST render a file with no leading `---` line exactly as today: no table, no divider.
6. MUST fall back to today's behavior (no table, no divider, front matter left as literal text in
   the body) when a file opens with `---` but never closes it with a matching `---` line -- an
   unterminated block is not front matter.
7. SHOULD skip the table (and divider) entirely, rendering only the body, if a well-formed
   front-matter block parses to zero key/value pairs (e.g. it's empty or all comments) --
   nothing worth tabulating.

## Non-goals

- A full YAML parser (nested maps, multi-line scalars, anchors, etc.). Values that don't fit the
  flat `key: value` / `[a, b]` shape render as their raw string. Revisit only against a real file
  that needs it.
- Rendering front matter for formats other than the `--- ... ---` YAML-block convention (e.g.
  TOML `+++` front matter).

## Design notes / links

Parsing lives in a new `viewmd/frontmatter.py`, separate from `render.py`, so the split/parse
logic is unit-testable without going through Rich at all. The parser's shape (flat keys, `[...]`
lists, quote-stripping, `#`-comment skipping) intentionally mirrors `tools/issues.py`'s
hand-written front-matter parser rather than introducing a YAML dependency -- see
[docs/PLAN.md](../docs/PLAN.md) for why this project avoids new dependencies for a narrow, known
input shape.

## Acceptance / verification

- `./run-tests.sh` green; new unit tests in `tests/test_frontmatter.py` cover requirements 1-2
  and 6-7 directly (split/parse functions), and `tests/test_render.py` gains a case asserting a
  front-matter table's key and value text appear before the body's own content, and that a
  plain file (no front matter) renders unchanged.
- Manual: render one of this project's own issue files (real front matter, several key shapes
  including a `[a, b]` list) and confirm the table reads cleanly with a visible divider before
  the body.

## Peer review

- **Claude (Sonnet 5)** (agent), 2026-08-02: PASS. `./run-tests.sh` green (38 tests, ruff clean,
  issues index current). Verified manually by rendering this project's own
  `issues/archive/VIEWMD-0003-max-line-width.md`: front matter (including the `area: [cli,
  render]` list) renders as a bordered table, followed by a visually distinct dim double-line
  (`═`) divider, then the body heading — confirmed in both `--color=never` and default-colored
  output. Unit tests directly cover the no-front-matter, unterminated-block, and
  empty-block-yields-no-pairs fallback paths (requirements 5-7).

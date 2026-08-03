---
id: VIEWMD-0011
title: Check whether advanced YAML/TOML/JSON front-matter features render correctly
status: implemented
area: [render, docs]
effort: low
created: 2026-08-03
updated: 2026-08-03
accepted_by: George Moses
accepted_at: 2026-08-03
commits: [f8555e3]
related: [VIEWMD-0004, VIEWMD-0005, VIEWMD-0012]
supersedes: []
changelog: "[1.1.2]"
reason:
---

# Check whether advanced YAML/TOML/JSON front-matter features render correctly

## Summary

VIEWMD-0004 shipped a deliberately narrow front-matter parser (flat `key: value` pairs plus single-level `[a, b, c]` lists), explicitly listing a full YAML parser and non-YAML front-matter formats as non-goals. This issue is a verification spike: check, with concrete test documents, whether the "advanced" front-matter features documented at <https://www.markdownlang.com/advanced/frontmatter.html#advanced-frontmatter-features> (nested objects, arrays of objects, block-list arrays, multiline block scalars, date formats, YAML 1.1 boolean aliases, and TOML/JSON front matter) render sensibly today, render as visible garbage, or silently corrupt other fields -- and record the answer so a follow-up implementation issue (if warranted) starts from facts rather than assumptions.

## Motivation / problem

VIEWMD-0004's Non-goals section asserts these are out of scope, but nobody has actually rendered a file exercising each feature and looked at the output. "Out of scope" and "silently produces wrong output" are different problems -- the former is an acceptable limitation, the latter is a bug regardless of scope. In particular, a flat-line parser that ignores YAML indentation can make nested keys collide with top-level keys of the same name, which is worse than just not supporting nesting.

## Requirements

1. MUST provide one manual test document per advanced feature category (nested objects, array of objects, block-list arrays, multiline block scalars, date formats, boolean aliases, TOML front matter, JSON front matter), plus one combined "kitchen sink" document, under `tests/fixtures/frontmatter-advanced/`.
2. MUST render each test document with `./viewmd.sh` (default and `--color=never`) and record the actual output against the feature each file intends to exercise.
3. MUST explicitly flag any case where the output is not just "unsupported" (e.g., raw text shown, block silently skipped) but actively wrong -- a nested key silently overwriting an unrelated top-level key of the same name, or data from one field bleeding into another.
4. MUST NOT modify `viewmd/frontmatter.py` or any other renderer behavior as part of this issue -- this is observation only. Any fix belongs in a separate follow-up issue, referenced back to this one via `related`.

## Non-goals

- Implementing support for any of these features. That's a separate, later issue if this investigation finds it's warranted.
- Exhaustively covering every YAML/TOML/JSON edge case; the reference page's own feature list is the scope boundary.

## Design notes / links

Builds on VIEWMD-0004 (`issues/archive/VIEWMD-0004-front-matter-table.md`) and VIEWMD-0005 (`issues/archive/VIEWMD-0005-hide-empty-front-matter.md`), whose Non-goals and behavior this issue is checking against actual rendered output. Parser under test: `viewmd/frontmatter.py`.

## Acceptance / verification

- Manual: render each file in `tests/fixtures/frontmatter-advanced/` (see that directory's `README.md` for the list and what each one checks) and record findings below.
- No test suite changes required; these are manual/reference fixtures, not asserted by `./run-tests.sh`.

### Findings (2026-08-03, rendered against current `main`)

- **Nested objects** (`01-nested-objects.md`): the parser has no concept of indentation, so `seo:`/`social:` (no value) are silently dropped and their indented children are hoisted to the top level as if flat. Worse: the nested `title` under `seo` silently overwrites the document's real top-level `title` in the table (last `key:` line wins) -- a correctness bug, not just a scope gap.
- **Array of objects** (`02-array-of-objects.md`): each `- name: ...` / `email: ...` line pair is parsed as its own flat key; only the last author survives (`- name` / `email` rows), earlier entries are silently lost.
- **Dash-list arrays** (`03-dash-list-arrays.md`): bare `- item` lines have no `:`, so they're silently dropped entirely (no error, no partial row) -- `tags` disappears from the table while the bracket-form `tags_bracket_form` renders correctly, confirming the bracket form is the only supported list syntax.
- **Multiline block scalars** (`04-multiline-strings.md`): only the `|`/`>` marker itself is captured as the value; the actual multi-line content is dropped (each continuation line has no `:` and is silently skipped, same as dash-list items).
- **Date formats** (`05-date-formats.md`): all four render correctly as plain strings -- ISO 8601 with an offset, bare date, quoted date, and UTC `Z` all survive because they're flat scalars with only one meaningful `:` for the parser to split on (`partition` only splits on the first `:`). No bug here; dates were never at risk given the parser's line-oriented design.
- **Boolean aliases** (`06-boolean-values.md`): all four (`true`/`false`/`yes`/`no`) render as their literal text, consistent with VIEWMD-0004's design (values are strings, not typed) -- not a bug, just confirms booleans are never coerced.
- **TOML front matter** (`07-toml-frontmatter.md`): correctly falls back to VIEWMD-0004 requirement 5's documented behavior -- no `---` opener, so no table, no divider, `+++` block left as literal body text (rendered as a wrapped paragraph, since it's not fenced as code).
- **JSON front matter** (`08-json-frontmatter.md`): same correct fallback as TOML -- no table, no divider, `;;; { ... } ;;;` left as literal body text.
- **Kitchen sink** (`09-kitchen-sink.md`): combines the above; confirms the same title-clobbering and silent-data-loss behavior occurs simultaneously when multiple advanced features appear in one real-world-shaped document.

**Conclusion**: TOML/JSON front matter and multiline/array-shaped YAML degrade safely (either a clean fallback or a clean drop). The one real bug is nested-key collision silently overwriting an unrelated top-level field with the same name -- worth its own follow-up issue.

## Peer review

- **Claude (Sonnet 5)** (agent), 2026-08-03: PASS. Rendered all 9 fixtures in `tests/fixtures/frontmatter-advanced/` with `./viewmd.sh --color=never` and recorded the actual output against each one's intent (see Findings above). `./run-tests.sh` green (54 tests, ruff clean, pip-audit clean, issues index current) -- no code touched, so no regression risk. Found one real correctness bug (nested-key collision overwriting an unrelated top-level field) worth a follow-up issue, filed separately as VIEWMD-0012.
- **George Moses** (maintainer), 2026-08-03: accepted the issue and its findings; directed closing it out and starting VIEWMD-0012.

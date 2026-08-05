---
id: VIEWMD-0029
title: An ER attribute key token after a quoted comment is silently dropped
status: proposed
area: [render, mermaid]
effort: low
created: 2026-08-05
updated: 2026-08-05
accepted_by:
accepted_at:
commits: []
related: [VIEWMD-0016]
supersedes: []
changelog:
reason:
---

# An ER attribute key token after a quoted comment is silently dropped

## Summary

`viewmd/mermaid/er/parser.py`'s `_parse_attribute` (ported byte-for-byte from `pkg/er/parser.go`'s `parseAttribute` as part of VIEWMD-0016) extracts an attribute row's quoted comment by keeping only the text *before* the opening quote and discarding everything from there on. When a diagram writes the `PK`/`FK`/`UK` key token *after* the comment instead of before it (`type name "comment" KEY`, rather than the more common `type name KEY "comment"`), the key is silently thrown away with no error -- the row renders with a blank key column, as if the key had never been written.

## Motivation / problem

This was found while byte-for-byte porting `pkg/er` for VIEWMD-0016, verified against the real Go binary, and reported upstream as-is (see `~/Documents/Projects/mermaid-ascii/bugs/mermaid-ascii-upstream-bugs.md`, bug 6) since it's a genuine upstream bug, not a viewmd-introduced one -- the port deliberately kept it during VIEWMD-0016 to stay byte-for-byte faithful to the reference implementation being ported, per AGENTS.md's porting methodology. This issue is the separate question VIEWMD-0016 explicitly deferred: should viewmd's own port diverge from that (buggy) upstream behavior and parse the key correctly regardless of which side of the comment it's written on, discarding only the comment's own quoted span?

## Requirements

1. MUST parse a `PK`/`FK`/`UK` key token that appears after a quoted comment (`type name "comment" KEY`) the same as one that appears before it (`type name KEY "comment"`) -- both orderings populate `Attribute.keys` identically for equivalent input.
2. MUST NOT change parsing of the existing (and far more common) `type name KEY "comment"` ordering already covered by VIEWMD-0016's golden fixtures.
3. MUST NOT change comment extraction itself -- only remove the quoted span from the line before tokenizing, rather than truncating at the first quote.
4. MUST handle the existing "unclosed quote" tolerance (`_parse_attribute`'s `else` branch, taking the rest of the line as the comment when there's no closing quote) without regressing -- there's no text after an unclosed quote to preserve, so this path is unaffected.
5. SHOULD add a code comment at the fix site noting this is a deliberate divergence from the byte-for-byte upstream port (VIEWMD-0016) and pointing at this issue, matching the pattern of prior divergence issues (e.g. VIEWMD-0022 through VIEWMD-0028).

## Non-goals

- Any other ER-diagram parsing or rendering behavior -- this is scoped to the single quoted-comment/key-ordering interaction in `_parse_attribute`.
- Filing or fixing the bug upstream in `github.com/AlexanderGrooff/mermaid-ascii` itself -- that's tracked separately in the bug report file referenced above, for the maintainer to file with the upstream project if desired.
- Changing `tests/fixtures/mermaid_er/attribute_keys_and_types.mmd`'s existing differential-tested cases, which currently pin the *upstream* (buggy) behavior -- this issue adds new, hand-verified coverage for the fixed ordering rather than changing what that fixture asserts, since there's no longer a reference output to diff the fixed behavior against (same testing posture as VIEWMD-0022/0023/0025/0026/0027/0028).

## Design notes / links

`viewmd/mermaid/er/parser.py`'s `_parse_attribute` (ported from `pkg/er/parser.go` lines 277-289) is the fix site: currently `line = line[:idx].strip()` after extracting the comment (`idx`/`end` bracket the quoted span); the fix removes just `line[idx:end+1]` instead of everything from `idx` onward. `~/Documents/Projects/mermaid-ascii/bugs/mermaid-ascii-upstream-bugs.md` bug 6 has the full root-cause writeup and a suggested upstream fix. VIEWMD-0016 (`issues/archive/VIEWMD-0016-mermaid-er-diagrams.md`) is the byte-for-byte baseline this diverges from.

## Acceptance / verification

- A hand-verified unit test in `tests/test_mermaid_er_parser.py` parsing `type name "comment" KEY` and asserting `Attribute.keys == ["KEY"]` (currently `[]` under the upstream-faithful behavior).
- Existing `type name KEY "comment"` parser tests and `tests/fixtures/mermaid_er/` differential fixtures continue to pass unchanged.
- `./run-tests.sh` green.

## Peer review

Left blank until implemented and tested; filled in as part of the Definition of Done landing gate.

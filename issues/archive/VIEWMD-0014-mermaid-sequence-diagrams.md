---
id: VIEWMD-0014
title: Render Mermaid sequence diagrams as box-drawing ASCII art
status: implemented
area: [render, mermaid]
effort: high
created: 2026-08-03
updated: 2026-08-03
accepted_by: George Moses
accepted_at: 2026-08-03
commits: [e357e8f]
related: []
supersedes: []
changelog: "[1.3.0]"
reason:
---

# Render Mermaid sequence diagrams as box-drawing ASCII art

## Summary

Fenced ` ```mermaid ` code blocks containing a `sequenceDiagram` are rendered to box-drawing ASCII/Unicode art in place, instead of being shown as unhighlighted source text. This is the first of a planned family of Mermaid diagram types (flowcharts and others to follow in later issues), and introduces a general preprocessor-plugin pipeline so later diagram types (and any other future Markdown extension) plug in the same way wikilinks already do.

## Motivation / problem

viewmd currently renders ` ```mermaid ` fences as plain/unhighlighted code, same as any other unrecognized language. Sequence diagrams are common in project docs and READMEs; a reader in a terminal currently sees raw Mermaid syntax instead of the diagram it describes. Shelling out to the upstream `mermaid-ascii` Go tool (or a repackaged PyPI wheel bundling its binary) was considered and rejected: it would add a 9-19 MB compiled binary per platform to a single-dependency, pure-Python CLI tool, from an unofficial third-party repackaging with unclear licensing. Instead, `pkg/sequence` of `github.com/AlexanderGrooff/mermaid-ascii` (MIT licensed, ~1,450 non-test lines, no concurrency, no complex layout algorithm) was ported directly to Python, verified byte-for-byte against the real Go binary on a differential-test corpus.

## Requirements

1. MUST render ` ```mermaid ` fences containing a `sequenceDiagram` to box-drawing art, matching the upstream Go implementation's output byte-for-byte for: all 10 arrow types (solid/dotted, arrowhead/open/cross/point, bidirectional), central connections (`()`), self-messages, notes (`over`/`left of`/`right of`, single and multi-participant), fragments (`loop`/`opt`/`alt`/`par`/`critical`/`break`/`rect`) including nesting and `else`/`and`/`option` dividers, `autonumber`, participant aliasing (`participant X as Y`), and `%%` comments.
2. MUST leave a ` ```mermaid ` fence untouched (original source shown, no crash) when its diagram type isn't a `sequenceDiagram` or when parsing fails.
3. MUST NOT add any new runtime dependency beyond a small pure-Python one (`wcwidth`, for display-width-aware layout matching the Go port's `go-runewidth` usage) -- no compiled binaries, no shelling out.
4. MUST introduce a preprocessor-plugin pipeline (`viewmd/preprocessors.py`) that the existing wikilink rewriter and the new Mermaid renderer both run through, so a future preprocessor (e.g. a flowchart renderer) is added by extending one list rather than threading a new call through `render.py`.
5. SHOULD keep the port's module structure (`viewmd/mermaid/`) diagram-type-agnostic at the top level, so flowchart/ER ports (future issues) can sit alongside `viewmd/mermaid/sequence/` without reshaping the package.

## Non-goals

- Flowchart, ER, class, state, Gantt, pie, user journey, and git-graph diagram types -- future issues, not this one.
- Sizing/wrapping the rendered diagram to the terminal's `--width` -- a diagram wider than the terminal renders as-is (consistent with how code blocks already behave).
- Styling directives (`classDef`, `style`, `rect`'s fill colour) -- ASCII output can't represent colour; a `rect` block's colour argument is dropped and the frame drawn plain, matching upstream's own behavior.

## Design notes / links

`pkg/sequence/{parser,renderer,charset}.go` in `~/Documents/Projects/mermaid-ascii` (not part of this repo) is the reference. The port lives in `viewmd/mermaid/`: `textutil.py` (shared line-splitting/comment-stripping), `sequence/charset.py`, `sequence/parser.py`, `sequence/renderer.py`, and `preprocess.py` (fence detection and splicing). `viewmd/preprocessors.py` is the new pipeline; `viewmd/render.py` calls `preprocess(body)` in place of the old direct `rewrite_wikilinks(body)` call.

## Acceptance / verification

- `tests/test_mermaid_sequence.py`: 84 golden-file cases (42 `.mmd` fixtures x unicode/ascii charset) in `tests/fixtures/mermaid_sequence/`, each pinned to output captured from the real Go binary (built locally from the cloned upstream repo) -- covers every arrow type, note placement, fragment type/nesting, and several edge cases (unicode labels, five participants, no-label messages, `rect` with/without a colour argument).
- `tests/test_mermaid_sequence_parser.py`: unit tests for parse-error paths (empty input, missing keyword, no participants, duplicate participant, unmatched `end`/`else`, unclosed fragment, invalid syntax) and `sniff()` dispatch.
- `./run-tests.sh` (ruff + full pytest suite) green.

## Peer review

- **Claude Sonnet 5** (agent), 2026-08-03: Reviewed the full diff after `./run-tests.sh` went green. Found and fixed two gaps during review: (1) no third-party attribution for the ported algorithm despite it being a direct translation, not an independent implementation -- added `THIRD_PARTY_NOTICES.md` and a pointer to it from `viewmd/mermaid/__init__.py`; (2) the new Mermaid/wikilink behavior wasn't mentioned in `README.md`'s usage docs -- added a paragraph next to the existing wikilinks one. Checked: `_render_message`'s direct rune-array indexing (no bounds padding, ported as-is from Go) is safe because `buildLifeline` always right-trims to exactly the last participant's center column, which is >= every index touched when rendering any single message -- verified this reasoning against the corpus rather than taking it on faith. Confirmed the preprocessor pipeline runs wikilinks before Mermaid and that fence detection doesn't interfere with the existing wikilink fence-skipping logic. No correctness issues found in the ported parser/renderer beyond what the 84-case differential corpus (verified byte-for-byte against the actual Go binary, not hand-written expectations) already covers. Also added `docs/example.md`, a showcase file exercising every feature (front matter, wikilinks, and every supported Mermaid sequence-diagram construct including the graceful flowchart fallback), rendered end-to-end through `./viewmd.sh` to confirm it looks right.
- **George Moses** (maintainer), 2026-08-03: "yes, commit and close this out" -- approved for landing.

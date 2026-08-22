---
id: VIEWMD-0104
title: Highlight regions marked by sentinel HTML comments
status: implemented
area: [render]
effort: medium
created: 2026-08-21
updated: 2026-08-22
accepted_by: George Moses <gmo6nl@gmail.com>
accepted_at: 2026-08-22
commits: [37942a9]
related: [VIEWMD-0091]
supersedes: []
changelog: "[1.51.0]"
reason:
---

# Highlight regions marked by sentinel HTML comments

## Summary

Teach viewmd to recognize a pair of sentinel HTML comments — `<!-- viewmd:mark start kind=KIND -->` … `<!-- viewmd:mark end -->` — and render the block-level content enclosed between them with a colored background tint, per `kind`. The markers are ordinary HTML comments, so they are invisible to every other Markdown renderer and inert in viewmd when the feature is not exercised. viewmd never computes what changed; a caller that already knows the changes injects the markers into the document it pipes in. This lets such a caller show "what changed" *inside* a formatted Markdown/Mermaid render, rather than only as a line diff.

## Motivation / problem

viewmd renders a *document*, beautifully — headings, tables, task lists, Mermaid — but it has no way to say "this part is new / changed." The concrete driver is [gitgleam](https://github.com/mo6/gitgleam), a sibling macOS menu-bar app that watches a git repository and previews a changed Markdown file through viewmd instead of a raw diff. Its `Sources/Gitgleam/MarkdownHighlighter.swift` already wraps each changed block in `viewmd:mark` sentinels ahead of viewmd support (they are inert HTML comments until this issue ships), using exactly the marker format this issue specifies — that file is the concrete contract to implement against, not a hypothetical one. It could pass line ranges on the command line instead, but line numbers are meaningless the moment viewmd reflows a paragraph to its render width: the highlight would land on the wrong text. A marker embedded in the source travels *with* its content through reflow, wraps when the content wraps, and can bound exactly the blocks that changed — so it stays correct regardless of `--width`. Keeping the diff computation in the caller also keeps viewmd free of any git/diff knowledge: it only has to render what it is told is marked.

## Requirements

1. MUST recognize a paired, block-level sentinel: a start comment `<!-- viewmd:mark start kind=KIND -->` and an end comment `<!-- viewmd:mark end -->`, each on its own line between blocks. Everything between them (one or more block elements) is the *marked region*.
2. MUST accept `kind` ∈ {`added`, `changed`, `removed`}; a missing or unrecognized `kind` defaults to `changed`. Matching MUST tolerate flexible inner whitespace (`<!--viewmd:mark start-->` and `<!--  viewmd:mark  start  kind=added  -->` both match). Note: gitgleam's own marker generation only ever emits `added`/`changed` (a pure deletion has no line in the after-file to mark) — `removed` stays part of viewmd's own generic contract regardless, for any other caller.
3. With color enabled, MUST tint the *background* of every rendered line of the region — including wrapped continuation lines, table rows, fenced code-block lines, and the lines of a rendered Mermaid diagram — per kind: `added` green, `changed` amber/yellow, `removed` red. No characters are added (no gutter column, no glyph): this preserves layout exactly, matching how the theme system (VIEWMD-0091) already swaps a background while leaving layout untouched. Foreground colors within the region (syntax highlighting, a Mermaid diagram's own foreground tints) MUST be preserved; only the background changes.
4. When the underlying content already carries its own background (a themed code fence's own background color, a Mermaid quadrant's own quadrant-fill background), the mark's background MUST take precedence there too, the same override-the-background/keep-the-foreground precedent VIEWMD-0091's quadrant-chart and code-fence theming already established.
5. The background tint MUST extend across the line's full rendered width, not just behind the marked text's own extent, so a region reads as one continuous highlighted band (the common diff-viewer convention), not a ragged patch that only covers the characters.
6. With color disabled (`--color=never`, `NO_COLOR`, or non-tty without `--color=always`), a marked region MUST render identically to the same content with no marks at all — there is no non-color-safe way to show a background tint, so the feature is simply inert rather than falling back to an ASCII substitute. gitgleam itself always renders with `--color=always`, so this path exists for viewmd's own general correctness, not because the concrete driver needs it.
7. The sentinel comments themselves MUST NOT appear anywhere in the output.
8. Removing a sentinel MUST NOT change the surrounding blank-line spacing versus the same document with that sentinel line simply deleted from the source — this MUST be done by stripping `viewmd:mark` sentinel lines from the Markdown source at the preprocessing stage (the same place `viewmd/wikilinks.py` and `viewmd/mermaid/preprocess.py` already rewrite source text ahead of `rich.markdown.Markdown`'s own parser), not by suppressing an unknown block element after Rich has already parsed it. The latter is what [docs/mark-highlight-example.md](../docs/mark-highlight-example.md) demonstrates as a reproducible bug today: `rich.markdown.Markdown` treats an unrecognized HTML comment as its own block element, and `MarkdownElement.new_line`'s default of `True` (never overridden for an unhandled token) makes the render loop insert a blank-line segment on both sides of it — so every marked block's surrounding gap roughly doubles even though the comment's own text never appears, satisfying requirement 7 while still failing this one.
9. A document that contains **no** `viewmd:mark` sentinels MUST render byte-for-byte identically to today (ordinary HTML comments, including other `<!-- ... -->`, keep their current handling).
10. MUST fail safe on malformed input: an unbalanced start (no matching end) applies to the end of the document; an end with no open start, or any `viewmd:mark` comment that cannot be parsed, is ignored. Either case MUST emit a single `viewmd: ...` warning to stderr and MUST NOT crash or abort the render.

## Non-goals

- **Inline / sub-block granularity.** First cut marks whole blocks only; highlighting a single changed *word* inside a paragraph is out of scope (the background tint marks the whole block).
- **Nested or overlapping regions.** Regions are flat; a start inside an already-open region is a malformed input under requirement 10.
- **A single-block shorthand** (e.g. a lone `<!-- viewmd:mark kind=added -->` applying to just the next block). Paired start/end only, for now — matches how gitgleam's own generator always emits a pair per block.
- **Computing the diff.** viewmd does not read git, does not diff two files, and does not decide what is "changed" — it only renders regions a caller has already marked. Injecting the markers, and choosing the `kind`, is entirely the caller's job.
- **A `--highlight-style` / configurable palette.** One built-in per-kind treatment for now.
- **An ASCII/no-color visual substitute for the highlight.** Per requirement 6, no-color output is simply unmarked — no gutter glyph, no other indicator.
- **Fixing gitgleam's own ANSI parser.** gitgleam's `Sources/Gitgleam/ANSIText.swift` currently parses and discards every background-color SGR code (`40–47`/`100–107`/`48;5;n`/`48;2;r;g;b`) before turning viewmd's output into a SwiftUI `AttributedString`, so until gitgleam's own parser is taught to forward background color too, this feature will render correctly from viewmd's side but stay invisible in gitgleam's preview. That is a separate, follow-up change in gitgleam's own repo, tracked there, not part of this issue.

## Design notes / links

- The background tint is deliberately a *post-layout* decoration keyed to the region's rendered line span, not inline markup woven into the text runs. That is what makes it survive reflow and work identically for prose, tables, code, and Mermaid art. Wrapping an already-rendered, already-colored line in a new background style has one real gotcha: an embedded `RESET` partway through the line (e.g. a code fence's own syntax-highlighting colors) cancels the wrapping style early unless it is re-applied after every reset — exactly the bug found and fixed once already in `_wrap_hover` (`viewmd/interactive_pager.py`, VIEWMD-0092), reuse that same technique rather than re-deriving it. See [docs/PLAN.md](../docs/PLAN.md) for the render/layout pipeline this hooks into.
- Real risk to verify visually, not just in isolated fixtures (per this project's own established lesson about verifying rendering in composition — VIEWMD-0022's diamond/rectangle finding): a Mermaid diagram that already paints its own background (a quadrant chart, a kanban board's per-column fill) could look wrong once a solid mark background is laid over its own internal coloring. Check this during implementation with a real marked quadrant/kanban fixture, not just a marked paragraph. [docs/mark-highlight-example.md](../docs/mark-highlight-example.md) has a marked pie chart as a starting point; add a quadrant/kanban case there too when implementing.
- HTML comments were chosen over a CLI line-range interface precisely because they are reflow-stable and block-accurate, and because they keep viewmd git-agnostic (the contract is "render what's marked," nothing about *why* it's marked). A CLI `--highlight L1-L2` alternative was considered and rejected on those grounds.
- Because the markers are standard HTML comments, a marked document is still valid Markdown and renders cleanly (markers simply ignored) in GitHub, Obsidian, and any other viewer — so a caller may inject them into a throwaway copy piped on stdin without corrupting anything.

## Acceptance / verification

New `tests/test_highlight.py` covering, at the documented render width:

- an `added` region's rendered lines carry a green background SGR/truecolor code across their full width, including a paragraph wrapped across several lines and a multi-line Mermaid/table block; `changed`/`removed` show amber/red;
- the region's own foreground colors (syntax highlighting inside a marked code fence, a marked Mermaid diagram's own foreground tints) are unchanged versus the same content unmarked;
- a marked region inside content that already sets its own background (a themed code fence, a Mermaid quadrant fill) shows the mark's background, not the original one;
- `--color=never` output with sentinels present is byte-for-byte identical to the same document with the sentinels removed (requirement 6);
- the sentinel comments never appear in the output;
- a marked document's blank-line spacing matches the same document with its sentinels plainly deleted, not just its comment text hidden (requirement 8);
- a document with no sentinels is unchanged versus a golden render (requirement 9);
- an unbalanced start, and a stray end, each warn to stderr and still render (requirement 10).

A fixture showing a marked region alongside the rest of viewmd's output, including one marked Mermaid diagram specifically (per the Design notes' composition risk), already exists at [docs/mark-highlight-example.md](../docs/mark-highlight-example.md) — it currently doubles as a bug repro (render it today to see the blank-line-doubling problem described there, caused by `rich.markdown.Markdown` having no special handling for the sentinel comments yet). Once this issue is implemented, re-render it to confirm the doubling is gone and the marked regions show their background tints. `./run-tests.sh` green (pytest, ruff, `./tools.sh issues --check`).

## Peer review

- (agent, code-review skill @ high) Found a MUST-fix (requirement 10): a malformed `viewmd:mark` comment that fails to match the strict sentinel pattern was silently left in place with no warning, reproducing the blank-line-doubling bug it was meant to fix; also found that `strip_marks` had no fence-tracking, so a sentinel-*looking* line inside a fenced code example would be incorrectly stripped. Also flagged: duplicate stderr warnings across the interactive pager's repeated `render_markdown` calls per document load; O(n²) region-measurement cost; and a duplicated ANSI-stripping regex already present in `interactive_pager.py`.
- (agent, independent fresh review, no prior context) Confirmed the same requirement-10 gap as a MUST-fix, verified empirically. Also benchmarked the O(n²) region-measurement cost directly (150→900 marked blocks: 0.17s→5.63s) and flagged it as worth discussion given gitgleam's own "marks nearly every block" usage; flagged missing test coverage for the Mermaid-specific acceptance-criteria items (only code fences were covered); flagged the `test_document_with_no_sentinels...` test being a self-comparison rather than a real regression check against a pre-change baseline. Confirmed by direct inspection that requirements 4/6/9 and the `_strip_bg_params` truecolor-collision fix are correct, and that the real single continuous `console.print()` calls are genuinely untouched as the `_mark_line_ranges` docstring claims.

Both MUST-fix findings (malformed-sentinel warning, fence-tracking) were fixed and covered by new tests (`test_strip_marks_malformed_comment_is_stripped_and_warns`, `test_strip_marks_leaves_sentinel_looking_text_inside_a_fence_untouched`). The Mermaid-specific test gap was closed (`test_marked_mermaid_quadrant_chart_keeps_its_own_foreground_tints`, `test_marked_mermaid_quadrant_chart_background_overrides_its_own_quadrant_fill`), and the no-sentinels test now pins a golden string verified against a checkout of the pre-change `develop` tip rather than comparing against itself. The O(n²) region-measurement cost and the duplicated ANSI-stripping regex are deliberately left as follow-up candidates rather than rushed now — see `_mark_line_ranges`'s own docstring in `viewmd/render.py` for why a faster scheme isn't a safe drop-in fix. The duplicate-stderr-warning-on-pager-reload nit was also left as-is (cosmetic, not a correctness issue).

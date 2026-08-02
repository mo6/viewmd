---
id: VIEWMD-0006
title: Highlight Obsidian-style [[wikilinks]]; confirm standard Markdown links are highlighted
status: in-progress
area: [render]
effort: medium
created: 2026-08-02
updated: 2026-08-02
accepted_by: George Moses
accepted_at: 2026-08-02
commits: []
related: [VIEWMD-0007]
supersedes: []
changelog:
reason:
---

# Highlight Obsidian-style [[wikilinks]]; confirm standard Markdown links are highlighted

## Summary

Obsidian-style wikilinks (`[[Target]]`, `[[Target|Display text]]`) are not standard CommonMark
syntax, so today they render as literal bracketed text, e.g. `[[DELVE-0046]]` in
`~/Documents/Projects/delve/issues/DELVE-0047-llm-grader-scenario-benchmark.md`. They should
render highlighted the same way a standard Markdown link already does. Standard Markdown links
already get Rich's default link styling (`markdown.link_url`: blue + underline); this issue also
adds regression coverage confirming that, since nothing currently asserts it.

## Motivation / problem

Reported by the maintainer, pointing at real usage in `../delve/issues/DELVE-0047-...md` (and
`DELVE-0017`, `DELVE-0019`, `DELVE-0035`, `DELVE-0051`, which all use `[[DELVE-NNNN]]`-style
links): wikilinks should stand out visually the way a normal link does.

## Requirements

1. MUST recognize `[[Target]]` and `[[Target|Display text]]` outside of code (see requirement 3)
   and render them with the same visual highlight Rich already gives a standard Markdown link
   (`markdown.link_url` style): the display text is `Display text` if given, else `Target`,
   brackets not shown.
2. MUST confirm (via a test, not just manual eyeballing) that a standard `[text](url)` Markdown
   link renders with Rich's `markdown.link_url` style, since VIEWMD-0006 is also the first issue
   to assert this rather than assume it.
3. MUST NOT transform `[[...]]`-shaped text that appears inside a fenced code block or an inline
   code span (`` `...` ``) -- e.g. a Lua long-bracket string literal like `des.map([[...]])`
   (real text in `../delve/AGENTS.md`) must render as literal code, unhighlighted, exactly as
   today.
4. SHOULD treat a wikilink as visual highlighting only in this issue, not a real navigable link
   (no file resolution, no jump-to-target) -- that's the separate, larger navigation feature the
   maintainer flagged as a future request (tracked separately, see Related).

## Non-goals

- Actual navigation to a wikilink's target (opening another file, jumping to a heading). This
  issue is highlighting only; see the separate future issue for in-document/cross-document
  navigation.
- Handling a code fence opened with an unusual/mismatched marker (e.g. a fence marker longer than
  three characters that this project's own simplified fence-detection doesn't match exactly).
  Fenced-block detection here is "any line starting with ` ``` ` or `~~~` toggles code-fence
  state," matching common usage; exotic nested-fence Markdown is out of scope.
- Multi-backtick inline code spans (`` ``code with a ` backtick`` ``). Single-backtick inline
  spans (the overwhelming common case, including the real `` `ollama run ...` `` and
  `` `des.map([[...]])` `` examples this issue is scoped against) are what requirement 3 covers.

## Design notes / links

Implemented as a text-level preprocessing pass in a new `viewmd/wikilinks.py`, run on the body
text (after front matter is split off, VIEWMD-0004) before it reaches Rich's `Markdown`, rather
than by subclassing Rich's `Markdown`/`MarkdownIt` internals to add a custom inline rule --
`rich.markdown.Markdown.__init__` builds its `MarkdownIt` parser internally with no public
extension point, so subclassing would mean depending on undocumented internals across Rich
versions. The preprocessor rewrites `[[Target]]` / `[[Target|Display]]` into an ordinary Markdown
link `[Display](wikilink:Target)`, which Rich then renders through its existing, already-styled
link path for free -- this is why requirement 1 says "the same visual highlight," not a new
style. The `wikilink:` scheme is inert (never expected to be opened); it exists only so the text
is syntactically a valid Markdown link.

## Acceptance / verification

- `./run-tests.sh` green; new unit tests in `tests/test_wikilinks.py` cover the preprocessor
  directly: bare `[[Target]]`, `[[Target|Display]]`, a wikilink inside a fenced code block left
  untouched, a wikilink-shaped string inside inline code left untouched, and plain text with no
  wikilinks passed through unchanged. `tests/test_render.py` gains cases confirming a standard
  `[text](url)` link and a converted wikilink both carry `markdown.link_url`'s ANSI styling
  (ANSI present with color, absent with `color=False`).
- Manual: render `~/Documents/Projects/delve/issues/DELVE-0047-llm-grader-scenario-benchmark.md`
  and `~/Documents/Projects/delve/issues/DELVE-0051-evaluate-qwen35-9b-grader.md` and confirm
  every `[[DELVE-NNNN]]` renders highlighted, brackets gone.

## Peer review

- **Auto (Composer)** (agent), 2026-08-02: PASS. `./run-tests.sh` green (53 tests, ruff clean, issues index current). Manual on `~/Documents/Projects/delve/issues/DELVE-0047-...md` and `DELVE-0051-...md`: every `[[DELVE-NNNN]]` renders with `markdown.link_url` underline-blue styling via inert `wikilink:` links, brackets gone; fenced/inline-code paths covered by unit tests.
- **Claude (Sonnet 5)** (agent), 2026-08-02: CONFIRMED, one bug found and fixed inline before
  landing. `_FENCE_RE.match(line)` in `viewmd/wikilinks.py` was anchored at column 0 with no
  leading-whitespace tolerance, so a fenced code block indented under a list item or blockquote
  (a common, unremarkable Markdown shape) was never recognized as a fence, and wikilink-shaped
  text inside it got wrongly rewritten -- a real violation of requirement 3. Fixed by matching
  against `line.lstrip()` instead; added a regression test
  (`test_wikilink_inside_indented_fenced_code_block_is_untouched`). Also found the top-level
  `README.md` and `docs/PLAN.md` had no mention of the new wikilink behavior despite every prior
  issue in this project updating both as part of landing; added a short usage note to each.
  Re-ran `./run-tests.sh` after both fixes: green, 54 tests. Re-verified the manual acceptance
  check on both real `../delve` files (bracket-free, correctly highlighted, multiple wikilinks
  per line handled, bare `DELVE-NNNN` mentions without `[[...]]` correctly left alone) and spot
  checked colored ANSI output directly (`4;34m` + OSC-8 hyperlink wrapping each wikilink). No
  further findings.

---
id: VIEWMD-0062
title: Render a table of contents from a document's heading structure
status: implemented
area: [render]
effort: medium
created: 2026-08-16
updated: 2026-08-16
accepted_by: George Moses
accepted_at: 2026-08-16
commits: [611a831, 7eb2c4e, 0bf909f]
related: [VIEWMD-0007, VIEWMD-0061, VIEWMD-0006]
supersedes: []
changelog: "[1.29.0]"
reason:
---

# Render a table of contents from a document's heading structure

## Summary

Render a table of contents (ToC) under a document's leading `#` title, built from its `#`/`##`/`###`
(`h1`/`h2`/`h3`) heading structure, indented to reflect nesting. The title heading itself is not
repeated in the ToC. Depth is chosen dynamically so the ToC stays at most 20 entries: start at
h1–h3, drop to h1–h2, then to h1-only, if a deeper outline would overflow; every remaining h1 is
always kept, even when there are more than 20 of them. On by default; togglable via a
`--toc`/`--no-toc` CLI flag and a `toc` key in the [VIEWMD-0061](VIEWMD-0061-global-config-file.md)
config file, CLI overriding config overriding the (on) built-in default.

## Motivation / problem

Longer Markdown documents -- this project's own `README.md`, `docs/PLAN.md`, and `issues/*.md`
files among them -- have no at-a-glance outline today; a reader has to page through the whole
rendered body to find a section. A ToC is also direct groundwork for
[VIEWMD-0007](VIEWMD-0007-link-navigation.md): that issue's own research note (see its "Research:
GNU Info's pager model" section) identifies Info's `* Menu:` block -- a node's list of links to its
children -- as one of two distinct link concepts a future interactive pager needs, and a
heading-derived ToC is the closest thing viewmd's static (non-interactive) renderer can produce
today. Filing this now, ahead of VIEWMD-0007's own scoping, lets the heading-outline extraction
logic and its rendering be built and used on its own merits (a real, immediately useful feature)
rather than only as a byproduct of the larger, still-unscoped interactive-pager work.

## Requirements

1. MUST extract a document's `h1`/`h2`/`h3` headings, in document order, as a heading-outline data
   structure (text and level), from the same parsed representation `viewmd/render.py:render_markdown`
   already builds (Rich's `Markdown`, backed by `markdown-it-py` tokens) -- not a second,
   independent Markdown parse -- so the ToC can never disagree with what the body itself renders as
   a heading.
2. MUST render the ToC as a list, one line per heading, indented by level (`h1` flush left, `h2`
   indented one step, `h3` indented two steps), in the same document order the headings appear in
   the body. When a leading `h1` is shown as the document title (requirement 3), it is omitted from
   this list; remaining `h2`/`h3` (and any later `h1`) entries keep those indent steps.
3. MUST render the ToC after the front-matter table (if any, per VIEWMD-0004/VIEWMD-0005) and its
   divider, and after the document's leading `h1` (the title, rendered as a normal body heading),
   and before the rest of the body. A document with no leading `h1` (the first `h1`/`h2`/`h3` is
   not an `h1`) keeps the ToC ahead of the whole body. The leading `h1` is the document title, not
   a ToC entry -- it MUST appear once, as the centered heading, not again as a flush-left ToC line
   and not again in the body below the ToC.
4. MUST be on by default (no flag needed) for a single document; MUST be togglable off via a
   `--no-toc` CLI flag (and back on via `--toc`, e.g. to override a config file that disabled it --
   see requirement 6).
5. MUST NOT include `h4` or deeper headings in the ToC (see Non-goals). The deepest heading the ToC
   will ever consider is `h3`.
6. MUST read a `toc` boolean key from the VIEWMD-0061 config file when present, at the precedence
   VIEWMD-0061 requirement 4 already establishes (CLI flag overrides config value overrides the
   built-in default of "on").
7. MUST omit the ToC entirely for a document with fewer than two qualifying (`h1`-`h3`) headings --
   a single heading (or none) has nothing to outline. This check is against the extracted outline
   *before* the depth cap in requirement 11; a document that has enough headings to outline, then
   drops to a one-line h1-only ToC under that cap, still renders that one line.
8. MUST NOT crash or alter body rendering for a document with irregular heading nesting (e.g. an
   `h3` appearing before any `h1`/`h2`) -- render the outline exactly as the headings appear, without
   inferring or correcting a "logical" hierarchy.
9. MUST style ToC entries consistently with how the body's headings themselves render (weight/
   color), not introduce a third, unrelated visual style for heading text.
10. MUST NOT change output for `--no-pager`-piped or non-terminal invocations beyond adding the
    ToC itself -- i.e. this issue changes what's rendered, not how color/width/pager behavior is
    otherwise resolved.
11. MUST cap the ToC at 20 entries by choosing the deepest heading level that fits, in this order:
    (1) `h1`+`h2`+`h3`, (2) `h1`+`h2`, (3) `h1` only. The cap counts *displayed* ToC lines (the
    leading title `h1` is not a ToC line, requirement 3). A deeper outline that would exceed 20
    entries MUST be replaced by the next-shallower one. Remaining `h1` headings in the ToC MUST
    always be included even when there are more than 20 of them -- the cap never drops an `h1`.
    Exactly 20 entries at a given depth is allowed (the cap is "more than 20", not "20 or more").
    If dropping a level would leave the ToC empty (e.g. 21 `h3`s and no remaining `h1`/`h2`, under
    requirement 8's irregular nesting), keep the deeper outline rather than rendering nothing.

## Non-goals

- Making ToC entries actual jump targets / clickable links to their section -- viewmd has no
  concept of an addressable in-document position yet (that's exactly what
  [VIEWMD-0007](VIEWMD-0007-link-navigation.md) is for); this issue renders a static, read-only
  outline only. VIEWMD-0007, once scoped, is expected to turn this ToC into its "Menu" concept
  (from that issue's Info research) once node navigation exists to jump to.
- `h4`-`h6` headings in the outline -- three levels is the ceiling (requirement 5); deferred, not
  ruled out permanently. The 20-entry cap (requirement 11) only steps down within h1–h3.
- A configurable maximum heading depth or ToC length (e.g. "only h1/h2", "at most 10 lines") --
  v1's depth is chosen automatically from the 20-entry cap (requirement 11), not by a CLI/config
  option; a depth or length *option* is a possible follow-up, not this issue.
- Numbering ToC entries (`1.`, `1.1.`, ...) -- plain indented list only.
- A combined multi-file ToC when viewmd is invoked with several paths (VIEWMD-0013's concatenated
  multi-file mode) -- v1 scopes to a single document's own headings; each file in a multi-file
  invocation rendering its own ToC (or not) ahead of its own content is a reasonable default but
  not mandated by this issue -- left to implementation.

## Design notes / links

`viewmd/render.py:render_markdown` is the integration point: extracting the heading outline needs
to happen from the same parse Rich's `Markdown` already does internally (`Markdown.parse`, backed
by `markdown-it-py`) -- prefer walking that existing token stream (e.g. via `Markdown.parsed`/the
tokens `Markdown.__init__` produces) over introducing a second `markdown_it.MarkdownIt()` parse
of `body` purely for headings, to avoid the two parses ever producing different results for the
same document (requirement 1). The 20-entry cap (requirement 11) is a count of ToC *entries*
(one per included heading), not of wrapped terminal rows -- a long heading that wraps still
counts as one. Depends on [VIEWMD-0061](VIEWMD-0061-global-config-file.md) for the `toc` config
key (requirement 6) -- that issue's config-resolution mechanism should land first, or this
issue's `--toc`/`--no-toc` flag can land first with the config key wired in once VIEWMD-0061
exists, implementation's choice on sequencing. See
[VIEWMD-0007](VIEWMD-0007-link-navigation.md)'s "Research: GNU Info's pager model" section for how
this ToC is expected to relate to that issue's later "Menu" concept.

## Acceptance / verification

- `./run-tests.sh` green, including new `pytest` fixture coverage for: a multi-heading document
  rendering an indented ToC matching its h2/h3 structure under the leading h1 title (requirements
  1-3), correct placement relative to front matter, title, and body (requirement 3), `--no-toc`/`--toc`
  each overriding the default and a config value (requirements 4, 6), a single-heading document
  rendering with no ToC (requirement 7), an irregularly-nested document (e.g. `###` before any `#`)
  rendering its outline without crashing or reordering (requirement 8), `h4`+ headings absent from
  the ToC while still rendering normally in the body (requirement 5), a document whose displayed
  ToC is 20 entries keeping all three levels, a document whose displayed ToC exceeds 20 dropping
  h3 (and h2 if still over) while keeping every remaining h1, a document with more than 20 ToC h1s
  still listing every remaining h1, and an irregular document with more than 20 h3s and no h1/h2
  keeping those h3s rather than rendering an empty ToC (requirement 11).
- Manual check: `./viewmd.sh issues/VIEWMD-0041-mermaid-class-diagrams.md --no-pager | head -30`
  and confirm the centered title heading comes first, then the ToC (without repeating that title),
  then the body starting at Summary; rerun with `--no-toc` and confirm the ToC is absent.

## Peer review

- **Independent review agent** (agent), 2026-08-16: pass-with-nits on `611a831`+`7eb2c4e` vs develop. MUST 1–11 hold; `pytest -k toc` (22) and full suite (939) green; `./viewmd.sh issues/VIEWMD-0041-mermaid-class-diagrams.md --no-pager --color never --width 80` is front matter, centered title, ToC (title omitted), then Summary; `--no-toc` omits the outline; `--width 60` vs `200` reaches the title. Should-fix: cutting the leading h1 at `token.map` and re-parsing `title_src` drops later link-reference definitions (`# See [foo]` plus `[foo]: url` renders `See [foo]` with ToC, `See foo` with `--no-toc`). Nits: placement test's `or` is tautological; inline-markup ToC coverage only exercises the omitted title h1; no pytest for the no-leading-h1 ToC-before-body branch.
- **George Moses** (maintainer), 2026-08-16: "Accept, commit, merge and close this issue" — approved to land.

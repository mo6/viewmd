---
id: VIEWMD-0062
title: Render a table of contents from a document's heading structure
status: proposed
area: [render]
effort: medium
created: 2026-08-16
updated: 2026-08-16
accepted_by:
accepted_at:
commits: []
related: [VIEWMD-0007, VIEWMD-0061, VIEWMD-0006]
supersedes: []
changelog:
reason:
---

# Render a table of contents from a document's heading structure

## Summary

Render a table of contents (ToC) at the start of a document's output, built from its `#`/`##`/`###`
(`h1`/`h2`/`h3`) heading structure, indented to reflect nesting. On by default; togglable via a
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
   the body.
3. MUST render the ToC after the front-matter table (if any, per VIEWMD-0004/VIEWMD-0005) and its
   divider, and before the document body, matching `render_markdown`'s existing front-matter →
   divider → body ordering.
4. MUST be on by default (no flag needed) for a single document; MUST be togglable off via a
   `--no-toc` CLI flag (and back on via `--toc`, e.g. to override a config file that disabled it --
   see requirement 6).
5. MUST NOT include `h4` or deeper headings in the ToC (see Non-goals).
6. MUST read a `toc` boolean key from the VIEWMD-0061 config file when present, at the precedence
   VIEWMD-0061 requirement 4 already establishes (CLI flag overrides config value overrides the
   built-in default of "on").
7. MUST omit the ToC entirely for a document with fewer than two qualifying (`h1`-`h3`) headings --
   a single heading (or none) has nothing to outline.
8. MUST NOT crash or alter body rendering for a document with irregular heading nesting (e.g. an
   `h3` appearing before any `h1`/`h2`) -- render the outline exactly as the headings appear, without
   inferring or correcting a "logical" hierarchy.
9. MUST style ToC entries consistently with how the body's headings themselves render (weight/
   color), not introduce a third, unrelated visual style for heading text.
10. MUST NOT change output for `--no-pager`-piped or non-terminal invocations beyond adding the
    ToC itself -- i.e. this issue changes what's rendered, not how color/width/pager behavior is
    otherwise resolved.

## Non-goals

- Making ToC entries actual jump targets / clickable links to their section -- viewmd has no
  concept of an addressable in-document position yet (that's exactly what
  [VIEWMD-0007](VIEWMD-0007-link-navigation.md) is for); this issue renders a static, read-only
  outline only. VIEWMD-0007, once scoped, is expected to turn this ToC into its "Menu" concept
  (from that issue's Info research) once node navigation exists to jump to.
- `h4`-`h6` headings in the outline -- three levels is enough for a useful at-a-glance outline
  without the ToC itself becoming as long as a heavily-nested document's body; deferred, not ruled
  out permanently.
- A configurable maximum heading depth (e.g. "only h1/h2") -- v1's depth is fixed at h1-h3
  (requirement 5); a depth *option* is a possible follow-up, not this issue.
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
same document (requirement 1). Depends on [VIEWMD-0061](VIEWMD-0061-global-config-file.md) for the
`toc` config key (requirement 6) -- that issue's config-resolution mechanism should land first, or
this issue's `--toc`/`--no-toc` flag can land first with the config key wired in once VIEWMD-0061
exists, implementation's choice on sequencing. See
[VIEWMD-0007](VIEWMD-0007-link-navigation.md)'s "Research: GNU Info's pager model" section for how
this ToC is expected to relate to that issue's later "Menu" concept.

## Acceptance / verification

- `./run-tests.sh` green, including new `pytest` fixture coverage for: a multi-heading document
  rendering an indented ToC matching its h1/h2/h3 structure in order (requirements 1-2), correct
  placement relative to front matter and body (requirement 3), `--no-toc`/`--toc` each overriding
  the default and a config value (requirements 4, 6), a single-heading document rendering with no
  ToC (requirement 7), an irregularly-nested document (e.g. `###` before any `#`) rendering its
  outline without crashing or reordering (requirement 8), and `h4`+ headings absent from the ToC
  while still rendering normally in the body (requirement 5).
- Manual check: `./viewmd.sh README.md --no-pager | head -30` and confirm the printed ToC's
  entries and indentation match `README.md`'s actual `#`/`##`/`###` structure; then rerun with
  `--no-toc` and confirm it's absent with the rest of the output unchanged.

## Peer review

Not applicable; not yet built.

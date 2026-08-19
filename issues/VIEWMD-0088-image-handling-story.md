---
id: VIEWMD-0088
title: Define and document viewmd's handling of Markdown image syntax
status: proposed
area: [render, docs]
effort:
created: 2026-08-19
updated: 2026-08-19
accepted_by:
accepted_at:
commits: []
related: []
supersedes: []
changelog:
reason:
---

# Define and document viewmd's handling of Markdown image syntax

## Summary

Pin down and document what `![alt text](path/to/image.png)` currently renders as (whatever Rich's `Markdown` does with it today, un-costumized by viewmd), and decide whether that's the intended permanent behavior (alt-text-only, styled like a link) or whether inline terminal-graphics rendering (Kitty/iTerm2 image protocols, detected the same way color support is detected) is worth a follow-up issue.

## Motivation / problem

viewmd's README documents headers, tables, code blocks, task lists, admonitions, wikilinks, and Mermaid diagrams in detail, but never mentions image syntax at all. For a general-purpose Markdown viewer, `![...](...)` is common enough (screenshots in READMEs, diagrams-as-PNG in notes) that silence on it reads as an oversight rather than a decision — a reader has no way to know if what they're seeing (probably just the alt text, rendered as a dim link) is final behavior or an unfinished area.

## Requirements

1. MUST add a test in `tests/test_render.py` pinning today's actual rendered output for an image reference, both inline (`![alt](x.png)`) and as its own paragraph, as a documented baseline.
2. MUST add a paragraph to `README.md` stating current behavior explicitly (e.g. "an image reference renders its alt text only, styled like a link; no image data is fetched or drawn").
3. SHOULD evaluate, as a design note (not required to implement here), whether inline rendering via the Kitty graphics protocol / iTerm2 inline-images escape sequence is worth a dedicated follow-up issue, gated the same way pie-chart truecolor is gated on color-capability detection (`viewmd/render.py`) — terminals without either protocol would keep the alt-text fallback.
4. MUST NOT silently attempt to fetch a remote image URL over the network — `docs/SECURITY.md` states viewmd has no network access anywhere in the tool today, and any future image-loading design must preserve that boundary or treat it as an explicit, separately-reviewed exception.

## Non-goals

- Implementing actual terminal image rendering is not required by this issue — only defining/documenting current behavior and, optionally, filing the follow-up if the design note recommends it.
- No local-file image thumbnailing/resizing logic in this issue.

## Design notes / links

See `docs/SECURITY.md` section 2 ("no network access anywhere in the tool") — any future image-fetching design must be weighed against that stated security posture explicitly, not incidentally broken by an image feature.

## Acceptance / verification

New pinned test(s) in `tests/test_render.py`; updated `README.md` paragraph. `./run-tests.sh` green. If a follow-up rendering issue is filed per requirement 3, link it via `related:`.

## Peer review


---
id: VIEWMD-0052
title: Stop gitGraph dead-lane dashes extending past their own last commit
status: in-progress
area: [render, mermaid]
effort: low
created: 2026-08-12
updated: 2026-08-12
accepted_by: George Moses <gmo6nl@gmail.com>
accepted_at: 2026-08-12
commits: []
related: [VIEWMD-0042]
supersedes: []
changelog:
reason:
---

# Stop gitGraph dead-lane dashes extending past their own last commit

## Summary

Fix `viewmd/mermaid/gitgraph/renderer.py` so a branch lane's dash line stops at its own last commit instead of extending rightward whenever a later, unrelated `merge`/`cherry-pick`/`branch` connector between two *other* lanes happens to cross that lane's row on its way between them.

## Motivation / problem

`render()`'s `touched` bookkeeping (renderer.py:158-167) adds a connector's column to *every* lane row it passes through, not just the two lanes it actually connects, so that the connector's vertical bar has a dash background to junction into. This is correct when the passthrough lane is still active, but once a branch is merged and receives no further commits, later, unrelated connectors between other branches keep stretching its dash line out to their column anyway -- purely an artifact of row order (lanes are stacked in first-appearance order, so a connector between two rows straddling a dead lane's row must cross it), not anything that happened on that branch. Reported by the maintainer against this input:

```
gitGraph
    commit
    commit
    branch feat/i18n
    commit
    commit
    checkout main
    merge feat/i18n
    branch feat/seo
    commit
    commit
    checkout main
    merge feat/seo
```

Current (wrong) output -- `feat/i18n`'s dash line runs all the way to the `feat/seo` merge column, well past its own last commit:

```
  main      ────●───────●───────┼─────────────●─────┼─────────────●─
             0-1075  1-ab8f     │             │     │             │
                                │             │     │             │
  feat/i18n                     ●───────●─────┼─────┼─────────────┼
                             2-d7e4  3-7657         │             │
                                                    │             │
  feat/seo                                          ●───────●─────┼
                                                 4-16c1  5-b81b
```

`feat/i18n` is done after its merge into `main`; nothing later happens on that lane, so its dash line reading past that point as if the branch were still "active" is misleading, especially as more sibling branches accumulate.

## Requirements

1. MUST render a passthrough connector (one whose column is not one of the crossed lane's own commits) as a bare vertical bar over blank background at that row, not as a junction spliced into manufactured dash fill -- i.e. remove the passthrough-column contribution to a lane's dash-extent calculation while still drawing the connector itself at the correct row/column.
2. MUST NOT change the dash extent of any lane whose own last commit's column is at or past every connector that crosses its row (i.e. no behavior change for the four reference examples already fixed in VIEWMD-0042 -- `develop`/`feat/i18n`-style lanes still fully alive when the last connector through them lands).
3. MUST NOT change how a connector is drawn/junction-merged where it crosses a lane's own dash line or marker (junction-merging behavior for a *live* lane's own content is unchanged; this issue only touches lanes where the crossed row has no dash background of its own at that column).
4. MUST NOT change behavior for any other Mermaid diagram type.

## Non-goals

- Reassigning/reusing a dead branch's row for a later-declared branch (a layout change, not a drawing-extent fix) -- considered and explicitly deferred; the maintainer picked this narrower renderer-only fix instead.
- Any change to the parser's row-assignment or column-numbering model (`viewmd/mermaid/gitgraph/parser.py`).

## Design notes / links

`viewmd/mermaid/gitgraph/renderer.py:158-167` (`touched` bookkeeping) and `renderer.py:182-204` (dash-extent/`max_fill` calculation) are the two sites to change: stop folding connector-passthrough columns into `touched[row]`, and at connector-draw time (`renderer.py:220-237`) fall back to drawing directly over blank background (skipping the "existing dash/junction" merge path) when the crossed row has no dash of its own at that column.

## Acceptance / verification

- New fixture: the maintainer's two-sequential-merged-branches example above, hand-verified so `feat/i18n`'s dash line stops at its own last commit (one trailing dash past commit `3-...`) and the `feat/seo` merge's vertical bar crosses `feat/i18n`'s row as a bare `│` over blank space, not spliced into extended dashes.
- Existing gitGraph fixtures (VIEWMD-0042's four reference examples plus its cherry-pick/merge/tag regression tests) byte-for-byte unchanged -- diff against the pre-change commit, not just a green `pytest`.
- `./run-tests.sh` green.

## Peer review


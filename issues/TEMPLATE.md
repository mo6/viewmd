---
id: VIEWMD-NNNN
title: <short imperative title>
status: proposed          # proposed | in-progress | implemented | superseded | rejected
area: []                  # free-form tags, e.g. render, pager, cli, tools, docs
effort:                   # low | medium | high; required from in-progress onward
created: YYYY-MM-DD
updated: YYYY-MM-DD
accepted_by:               # who explicitly accepted this issue (Definition of Ready, AGILE.md);
                          # blank while status: proposed, required from in-progress onward
accepted_at:               # YYYY-MM-DD the acceptance above was given; set together with accepted_by
commits: []               # short SHAs, filled on implementation
related: []               # other VIEWMD ids (siblings/dependencies)
supersedes: []            # VIEWMD ids this replaces, if any
changelog:                # CHANGELOG.md anchor, filled on release
reason:                   # optional; why a rejected issue was turned down
---

# <title>

## Summary

One paragraph: what changes and why.

## Motivation / problem

The need this addresses. What is wrong, missing, or harder than it should be today.

## Requirements

A plain numbered list of testable MUST / SHOULD / MUST NOT statements. Keep every item
observable and headlessly testable.

1. MUST ...
2. SHOULD ...

## Non-goals

What is explicitly out of scope, so the issue is not read as asking for more than it is.

## Design notes / links

Pointers into `docs/` for the *why* behind any non-obvious choice. Do not re-derive the design
here; link it.

## Acceptance / verification

How "done" is judged: named tests, `./run-tests.sh`, or a manual command to run. Each
requirement above should map to something here. An issue with no way to check it is not finished
being written.

## Peer review

Left blank until the change is implemented and tested. Filled in as part of the Definition of
Done's landing gate ([AGILE.md](AGILE.md)): **at minimum two lines, in order** -- the reviewing
agent's own pass, then the maintainer's own sign-off -- each appended (never overwritten) as the
review happens. The maintainer's line may be transcribed by an agent from what the maintainer
actually said, attributed to the maintainer as reviewer, but it must be a real recorded verdict,
not inferred from a bare "commit and close this out?" yes.

- **<reviewer name>** (agent|maintainer), YYYY-MM-DD: verdict, and a one-line pointer to any
  findings (fixed inline, or left as a follow-up issue).

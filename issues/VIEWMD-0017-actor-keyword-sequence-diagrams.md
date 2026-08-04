---
id: VIEWMD-0017
title: Support the "actor" keyword in Mermaid sequence diagrams
status: in-progress
area: [render, mermaid]
effort: low
created: 2026-08-04
updated: 2026-08-04
accepted_by: George Moses
accepted_at: 2026-08-04
commits: []
related: []
supersedes: []
changelog:
reason:
---

# Support the "actor" keyword in Mermaid sequence diagrams

## Summary

Mermaid sequence diagrams whose participants are declared with `actor` (instead of `participant`) fail to render; the diagram is silently left as raw Mermaid source in the output instead of being drawn as box-drawing ASCII art. Add `actor` as a synonym for `participant` in the sequence parser.

## Motivation / problem

The sequence parser only recognizes the `participant` keyword. The declaration regex at `viewmd/mermaid/sequence/parser.py:15` is `r'(?i)^\s*participant\s+(?:"([^"]+)"|(\S+))(?:\s+as\s+(.+))?$'`. An `actor` line matches no rule in the parse loop and hits the catch-all at `parser.py:304`, raising `MermaidError: line 2: invalid syntax: "actor U as User"`. Per the fallback in `viewmd/mermaid/preprocess.py:60`, a diagram that fails to parse is left untouched — so a single unrecognized `actor` line drops the *entire* diagram back to raw source. Diagrams commonly lead with `actor U as User`, so this is the only blocker for otherwise-valid documents (confirmed: swapping `actor` → `participant` renders correctly).

## Requirements

1. MUST accept `actor` as a synonym for `participant` in sequence-diagram declarations, including the quoted-name and `as`-label forms.
2. MUST render an `actor`-declared participant identically to a `participant`-declared one (as a box) — drawing an actual stick-figure glyph is out of scope (see Non-goals).
3. MUST NOT change parsing of a message where a participant is literally named `actor` (e.g. `actor->>B: hi`) — the existing whitespace-separated-keyword protection that `participant` relies on must continue to apply.
4. MUST NOT change the existing capture-group indices used by `_parse_participant`.

## Non-goals

Drawing a distinct stick-figure glyph for `actor` participants (visually different from `participant` boxes) is a larger, separate change and out of scope here.

## Design notes / links

Proposed one-line fix, using a non-capturing group so existing capture indices are untouched:

```python
_PARTICIPANT_RE = re.compile(
    r'(?i)^\s*(?:participant|actor)\s+(?:"([^"]+)"|(\S+))(?:\s+as\s+(.+))?$'
)
```

Source: https://github.com/mo6/viewmd/issues/1

## Acceptance / verification

- A parser unit test asserting an `actor` declaration produces a participant (including the `as`-label form).
- A render/golden test for a small `actor`-led sequence diagram (e.g. the reproduction below), confirmed to render as ASCII art rather than falling back to raw source.
- Reproduction case:
  ````
  ```mermaid
  sequenceDiagram
      actor U as User
      participant CU as Gateway check user
      U->>CU: Click AskJLR button
  ```
  ````
- `./run-tests.sh` green.

## Peer review


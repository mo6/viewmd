---
title: Mermaid diagram showcase
author: viewmd
tags: [mermaid, showcase, testcase]
status: draft
---

# Mermaid diagram showcase

An exhaustive, one-of-everything tour of the Mermaid diagram types and features viewmd renders —
every arrow type, fragment, node shape, direction, and edge case that has its own golden fixture
under `tests/fixtures/`. Two purposes at once: a visual showcase (view this file with viewmd
itself, `./viewmd.sh docs/mermaid-examples.md`, to see every example below rendered as box-drawing
art), and a living manual testcase — if a change to the renderer breaks one of these, it'll be
visibly wrong here even before `./run-tests.sh` catches it.

`docs/example.md` covers Mermaid alongside viewmd's other Markdown features, with just a couple of
representative examples; this file is Mermaid-only and goes deep on both diagram types instead.

## Sequence diagrams

### Every arrow type

```mermaid
sequenceDiagram
    participant Alice
    participant Bob
    Alice->>Bob: solid arrow with head
    Bob-->>Alice: dotted arrow with head
    Alice->Bob: solid, no head
    Bob-->Alice: dotted, no head
    Alice-xBob: solid, cross head (failed message)
    Bob--xAlice: dotted, cross head
    Alice-)Bob: solid, async point head
    Bob--)Alice: dotted, async point head
    Alice<<->>Bob: bidirectional, solid
    Bob<<-->>Alice: bidirectional, dotted
```

### Self-messages and central connections

```mermaid
sequenceDiagram
    participant Worker
    Worker->>Worker: think it over
    Worker()->>()Worker: central connection on both ends
```

### Notes: over, left of, and right of

```mermaid
sequenceDiagram
    participant Alice
    participant Bob
    Alice->>Bob: start the job
    Note over Alice,Bob: both parties agree on scope
    Note left of Alice: Alice waits
    Note right of Bob: Bob starts work
    Bob-->>Alice: done
```

### Every fragment type

```mermaid
sequenceDiagram
    autonumber
    participant Client
    participant Server
    loop retry until acknowledged
        Client->>Server: request
        alt server is healthy
            Server-->>Client: 200 OK
        else server is overloaded
            Server-->>Client: 503, retry later
        end
    end
    opt client wants a receipt
        Server-->>Client: receipt
    end
    par fetch profile
        Client->>Server: GET /profile
    and fetch settings
        Client->>Server: GET /settings
    end
    critical acquire lock
        Client->>Server: LOCK
    option lock unavailable
        Server-->>Client: retry later
    end
    break connection lost
        Client-xServer: (nothing further happens)
    end
```

### Actors

An `actor` declaration draws a random 3-line stick figure instead of a plain box; with more than
one actor in a diagram, each gets a different figure before any repeat.

```mermaid
sequenceDiagram
    actor Customer
    participant Gateway
    actor Support
    Customer->>Gateway: submit request
    Gateway->>Support: escalate
    Support-->>Customer: follow up
```

### Full width, even wider than the terminal

Diagram rows keep their natural width instead of being wrapped/padded to the render width
(VIEWMD-0018) — same as a wide code block's long lines (VIEWMD-0019). Every box below stays intact
on one row, scrolling horizontally in the pager instead of folding:

```mermaid
sequenceDiagram
    participant AAAAAAAAAA as First service with a fairly long descriptive name
    participant BBBBBBBBBB as Second service with a fairly long descriptive name
    participant CCCCCCCCCC as Third service with a fairly long descriptive name
    participant DDDDDDDDDD as Fourth service with a fairly long descriptive name
    AAAAAAAAAA->>BBBBBBBBBB: forward the request
    BBBBBBBBBB->>CCCCCCCCCC: forward it again
    CCCCCCCCCC->>DDDDDDDDDD: and once more
    DDDDDDDDDD-->>AAAAAAAAAA: finally, a response
```

## Flowcharts

Only `A[Label]` square-bracket syntax renders as a distinct node shape — other Mermaid shape
syntax (`()`, `{}`, `(())`) falls back to a bare label, and `BT`/`RL` directions are accepted but
drawn the same as `TD`/`LR` rather than actually reversed. Both are real limitations of
`mermaid-ascii`, the upstream implementation this is ported from — not a viewmd choice — and
tracked for a possible future viewmd-only extension in VIEWMD-0022.

### Branching and labelled edges

```mermaid
graph TD
    A[Start] --> B{Decision}
    B -->|yes| C[Do it]
    B -->|no| D[Skip it]
```

### Directions: TD/LR draw as expected, BT/RL alias to them

```mermaid
graph LR
    A --> B --> C
```

```mermaid
graph RL
    A --> B --> C
```

The `RL` diagram above renders identically to `LR` — same left-to-right flow — since `RL` is
parsed but not actually reversed (see the note at the top of this section).

### Chained arrows and fan-out

```mermaid
graph LR
    A --> B --> C
    A & B --> D
```

### Bidirectional edges

```mermaid
graph TD
    A[Client] <-->|sync| B[Server]
```

### Subgraphs, including nested

```mermaid
graph TD
    subgraph outer
        A --> B
        subgraph inner
            B --> C
        end
    end
    A --> D
```

### Subgraphs with left-to-right layout

The `DB --> Server` edge below flows "backward" (right to left) relative to the diagram's overall
`LR` direction, so the router sends it out the bottom of both boxes to avoid threading back
through the nodes in between — and its horizontal segment lands on the same row as the `Backend`
subgraph's own bottom border, visually fusing the arrow into the frame. This is an upstream
`mermaid-ascii` layout limitation (subgraph padding doesn't reserve space for backward-routed
edges), reproduced here byte-for-byte, not a viewmd defect:

```mermaid
graph LR
    subgraph Frontend
        UI[UI] --> API[API Client]
    end
    subgraph Backend
        Server[Server] --> DB[(Database)]
    end
    API --> Server
    DB --> Server
```

### `classDef`/`:::` styling

Renders as real 24-bit ANSI colour, matching the upstream renderer's `wrapTextInColor` — but only
when the `classDef` line has zero leading whitespace, a real upstream parsing quirk (see
`viewmd/mermaid/flowchart/parser.py`'s `test_classdef_must_be_unindented`):

```mermaid
graph TD
classDef red fill:#f96,color:#ff0000
A[Start]:::red --> B[End]
```

### Parallel edges between the same pair of nodes

```mermaid
graph TD
    A --> B
    A --> B
    A --> B
```

### Self-loops

```mermaid
graph TD
    A --> A
    A --> B
```

### Routing around an obstacle node

The A*-based router sends `A --> D` around `B` and `C` rather than through them:

```mermaid
graph TD
    A --> B
    A --> C
    B --> D
    C --> D
    A --> D
```

### Multi-line labels

```mermaid
graph TD
    A[Line one<br/>Line two] --> B[Single]
```

### Long labels

```mermaid
graph TD
    A[This is a rather long label for testing width] --> B[Another long one here too]
```

## Graceful fallback

Diagram types other than `sequenceDiagram` and `graph`/`flowchart` — and any block that fails to
parse — render as plain source text instead of raising an error, since only those two are
supported so far:

```mermaid
classDiagram
    Animal <|-- Duck
```

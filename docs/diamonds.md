---
title: Decision diamond sizes
author: viewmd
tags: [mermaid, flowchart, diamond, showcase]
status: draft
---

# Decision diamond sizes

Diamonds (`A{Label}`) render as a flat-topped/bottomed rounded lozenge -- the same shape family as `round`/`stadium`/`circle`, sized exactly like a same-content rectangle: one row per label line, plus 1 top and 1 bottom border row. A `◇` marks all four attachment points: centred in the top/bottom border (UP/DOWN), and immediately beside the label on every content row (LEFT/RIGHT). Unlike the old tapered-rhombus design, a diamond's height never depends on its own or a sibling's width -- only its own label's line count (VIEWMD-0038).

View this file with `./viewmd.sh docs/diamonds.md`.

## Short label

```mermaid
graph TD
    A[Go] --> B{OK}
    B -->|yes| C[Y]
    B -->|no| D[N]
```

```mermaid
graph TD
    A{X}
```

## Typical decision label

```mermaid
graph TD
    A[Start] --> B{Decide}
    B -->|yes| C[Do it]
    B -->|no| D[Skip]
```

```mermaid
graph TD
    A{Maybe}
```

## Multi-line label

A `<br>` label packs one row per line, with `◇` beside every content row:

```mermaid
graph TD
    A[Start] --> B{Decisions<br>Triangles}
    B -->|yes| C[Do it]
    B -->|no| D[Skip it]
```

```mermaid
graph TD
    A{Hello world}
```

## Several diamonds in one graph

Every diamond renders at the same height regardless of its own or a neighbour's label width:

```mermaid
graph LR
    S{OK} --> M{Decide}
    M --> L{Continue?}
```

## Nested decisions at mixed label lengths

A short gate into a longer follow-up question -- both diamonds render at the same height:

```mermaid
graph TD
    A([Begin]) --> B{Go?}
    B -->|no| C([Stop])
    B -->|yes| D{Ready to<br>ship?}
    D -->|yes| E([Release])
    D -->|no| F([Keep working])
```

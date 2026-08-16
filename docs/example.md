---
title: viewmd feature showcase
author: viewmd
tags: [demo, markdown, mermaid]
status: draft
reviewer:
---

# viewmd feature showcase

View this file with viewmd itself to see everything below rendered:

```
./viewmd.sh docs/example.md
```

The front-matter block above renders as a key/value table ahead of this heading, with a divider
after it. The empty `reviewer:` field is omitted by default -- pass `--full-front-matter` to show
it anyway.

## Text formatting

Paragraphs support **bold**, *italic*, ***bold italic***, ~~strikethrough~~, and `inline code`.

> A blockquote, for a callout or a quoted remark.

---

## Wikilinks

Obsidian-style wikilinks like [[Getting Started]] or [[Getting Started|a custom display name]]
render the same as an ordinary Markdown link, brackets gone.

## Lists

- Bullet item one
- Bullet item two
  - Nested item
    1. Numbered inside a bullet
    2. Second numbered item
- Bullet item three

1. First step
2. Second step
3. Third step

- [x] Write the draft
- [x] Review it
- [ ] Publish

## Tables

| Feature          | Status      | Notes                                   | Value |
|------------------|:-----------:|------------------------------------------|------:|
| Headers          | done        | all six levels                            | &euro;&nbsp;2,95 |
| Tables           | done        | this one, with alignment                  | &euro;&nbsp;1,50 |
| Front matter     | done        | rendered as a table, see the intro page   | &euro;&nbsp;12,50 |
| Wikilinks        | done        | see the formatting page                   | &euro;&nbsp;250,00 |
| Mermaid diagrams | done        | sequence, flowchart, ER, pie, packet, quadrant | &euro;&nbsp;1.395,00 |

## Syntax-highlighted code

```python
def render(text: str, *, width: int, color: bool) -> str:
    """Render Markdown to an ANSI string, width columns wide."""
    return _console_render(text, width=width, color=color)
```

### A line too wide for the render width

An ordinary code line longer than the render width stays intact on one line rather than folding
onto a second (VIEWMD-0019) -- same as a mermaid diagram (VIEWMD-0018). The line below is exactly
120 characters; at the default 100-column cap it should still render as a single unbroken line,
scrolling horizontally in the pager (`less -S`) instead of wrapping or being cut off:

```python
result = some_function(argument_one, argument_two, argument_three, argument_four, argument_five, argument_six, xxxxxxxx)
```

## Admonition callouts

GitHub and Obsidian `> [!TYPE]` callouts render as a bordered card instead of a plain quote:

> [!NOTE]
> Useful information that users should know, even when skimming.

> [!TIP]
> Optional information to help a user be more successful.

> [!IMPORTANT]
> Crucial information necessary for users to succeed.

> [!WARNING]
> Critical content demanding immediate user attention due to potential risks.

> [!CAUTION]
> Negative potential consequences of an action.

> [!HINT]
> An unrecognized type still renders as a generic card, using the type token as its label.

## Mermaid diagrams

A fenced ` ```mermaid ` block containing a `sequenceDiagram`, `graph`/`flowchart`, `erDiagram`,
`pie`, `packet-beta`/`packet`, or `quadrantChart` renders as box-drawing art in place of its
source. Other Mermaid diagram types, and any block that fails to parse, are left as plain source
text rather than causing an error.

### Sequence diagrams

Sequence diagrams support notes, loop/alt/par fragments, and `actor` participants (drawn as a
random 3-line stick figure instead of a box).

```mermaid
sequenceDiagram
    autonumber
    participant Client
    participant Server
    Client->>Server: request
    alt server is healthy
        Server-->>Client: 200 OK
    else server is overloaded
        Server-->>Client: 503, retry later
    end
```

### Flowcharts

Flowcharts support subgraphs, labelled and bidirectional edges, `classDef` styling, A*-based
routing around other nodes, and distinct node shapes (round, stadium/pill, circle, subroutine,
cylinder/database, and diamond decision nodes rendered as a rounded lozenge -- see
[docs/diamonds.md](diamonds.md) for the shape specifically). One real limitation inherited from the upstream
renderer flowcharts are ported from: `BT`/`RL` directions are accepted but not actually reversed
(aliased to `TD`/`LR`).

Source:

```
graph TD
    A[Start] --> B{Decision}
    B -->|yes| C[Do it]
    B -->|no| D[Skip it]
```

Rendered:

```mermaid
graph TD
    A[Start] --> B{Decision}
    B -->|yes| C[Do it]
    B -->|no| D[Skip it]
```

### ER diagrams

ER diagrams support attribute tables, crow's-foot cardinality notation, and
identifying/non-identifying relationships. See [docs/mermaid-examples.md](mermaid-examples.md)
for an exhaustive tour of sequence diagrams, flowcharts, and ER diagrams -- every arrow type and
fragment, every flowchart direction/subgraph/styling case, ER cardinality notation, and the
graceful-fallback behavior for diagram types that aren't supported yet.

Source:

```
erDiagram
    CUSTOMER ||--o{ ORDER : places
    CUSTOMER {
        string name
        string custNumber PK
    }
    ORDER {
        int orderNumber
        string deliveryAddress
    }
```

Rendered:

```mermaid
erDiagram
    CUSTOMER ||--o{ ORDER : places
    CUSTOMER {
        string name
        string custNumber PK
    }
    ORDER {
        int orderNumber
        string deliveryAddress
    }
```

### Pie charts render two ways, chosen by color (VIEWMD-0043)

Unlike the other diagram types, a `pie` chart renders differently depending on whether color is
available. With color (the default on a real terminal), it draws as an actual circle: each slice
a distinct truecolor region, a legend beside it, and its own size scaled to roughly 60% of what
comfortably fits the render width -- try `--width 60` vs. `--width 200` against this file and
compare:

```mermaid
pie title Pets adopted by volunteers
    "Dogs" : 386
    "Cats" : 85
    "Rats" : 15
```

Without color (`--color never`, `NO_COLOR` set, or piped output), the same chart falls back to a
horizontal bar chart instead -- a circular pie was tried without color and found illegible, so
the fallback is a deliberate second design, not a lesser version of the first. Run
`./viewmd.sh docs/example.md --color never` to see it.

### Packet diagrams (VIEWMD-0049)

A `packet-beta`/`packet` block draws a fixed-width bit/byte field layout -- the kind used to
document a network protocol header -- wrapped onto rows of 32 bits each. See
[docs/mermaid-packet.md](mermaid-packet.md) for fixtures with the `+<count>` shorthand and a
field spanning a row boundary.

```mermaid
packet-beta
    title TCP Packet
    0-15: "Source Port"
    16-31: "Destination Port"
    32-63: "Sequence Number"
    64-95: "Acknowledgment Number"
    96-99: "Data Offset"
    100-105: "Reserved"
    106: "URG"
    107: "ACK"
    108: "PSH"
    109: "RST"
    110: "SYN"
    111: "FIN"
    112-127: "Window"
    128-143: "Checksum"
    144-159: "Urgent Pointer"
    160-191: "(Options and Padding)"
    192-255: "Data (variable length)"
```

### Quadrant charts (VIEWMD-0047)

A `quadrantChart` block draws a bordered box split into four labelled quadrants by an internal
cross, with each `<label>: [x, y]` point plotted at its `(x, y)` position and labelled beneath its
marker. Like the pie chart, its size scales to the render width, and with color available each
quadrant's border, label, and points are tinted a distinct color over a darkened background fill.
Without color, the same box renders plain instead. See
[docs/mermaid-quadrant.md](mermaid-quadrant.md) for more fixtures.

```mermaid
quadrantChart
    title Reach and engagement of campaigns
    x-axis Low Reach --> High Reach
    y-axis Low Engagement --> High Engagement
    quadrant-1 We should expand
    quadrant-2 Need to promote
    quadrant-3 Re-evaluate
    quadrant-4 May be improved
    Campaign A: [0.3, 0.6]
    Campaign B: [0.45, 0.23]
    Campaign C: [0.57, 0.69]
    Campaign D: [0.78, 0.34]
    Campaign E: [0.40, 0.34]
    Campaign F: [0.35, 0.78]
```

### Kanban boards (VIEWMD-0034)

A `kanban` block draws ordered columns of stacked task cards, each column its own colored-header
box and each card its own nested box within it. Cards word-wrap long labels and can carry
`@{ ticket, assigned, priority }` metadata, rendered as a colored line under the label: a
severity-colored `[H]`/`[VH]`/`[L]`/`[VL]`/`[M]` priority token, an underlined ticket ID, and a
right-aligned assignee. Columns size to a uniform card width but hug their own content height, so
a short column doesn't pad out to match a taller one beside it.

```mermaid
kanban
  Todo
    [Create Documentation]
    docs[Create Blog about the new diagram]
  [In progress]
    id6[Create renderer so that it works in all cases. We also add some extra text here for testing purposes. And some more just for the extra flare.]
    id8[Design grammar]@{ assigned: 'knsv' }
    id4[Create parsing tests]@{ ticket: MC-2038, assigned: 'K.Sveidqvist', priority: 'High' }
  id11[Done]
    id5[define getData]
    id2[Title of diagram is more than 100 chars when user duplicates diagram with 100 char]@{ ticket: MC-2036, priority: 'Very High'}
    id3[Update DB function]@{ ticket: MC-2037, assigned: knsv, priority: 'High' }
```

### Gantt charts (VIEWMD-0032)

A `gantt` block draws one row per task: a status-tagged bar (`done`/`active`/untagged/`crit`) or a
single `◆` point for a `milestone`, against a scaled timeline axis with full-height gridlines and
`section`-grouped rows. With color available, each status gets its own hue and `crit` tasks get a
distinct bracket color layered on top; a longer span switches the axis to week ticks and adds a
date-anchor line under the chart so `W<n>` labels still say what date they fall on. This is
Mermaid's own "full syntax" reference example, exercising `excludes weekends`, `after`/`until`
chaining, hour-granularity durations, and every status tag at once -- see
[docs/mermaid-gantt.md](mermaid-gantt.md) for more.

```mermaid
gantt
    dateFormat  YYYY-MM-DD
    title       Adding GANTT diagram functionality to mermaid
    excludes    weekends

    section A section
    Completed task            :done,    des1, 2014-01-06,2014-01-08
    Active task               :active,  des2, 2014-01-09, 3d
    Future task               :         des3, after des2, 5d
    Future task2               :        des4, after des3, 5d

    section Critical tasks
    Completed task in the critical line :crit, done, 2014-01-06,24h
    Implement parser and jison          :crit, done, after des1, 2d
    Create tests for parser             :crit, active, 3d
    Future task in critical line        :crit, 5d
    Create tests for renderer           :2d
    Add to mermaid                      :until isadded
    Functionality added                 :milestone, isadded, 2014-01-25, 0d
```

### gitGraph diagrams (VIEWMD-0042)

A `gitGraph` block draws one horizontal lane per branch, in first-appearance order, as `──●──`
segments with commit ids centered beneath each marker. Supports `branch`/`checkout`, `merge`,
`cherry-pick`, an optional `tag:` in `[brackets]`, and a bare `commit` with no `id:` (auto-generates
a random 4-hex-char id, matching Mermaid's own behavior). Vertical connectors merge into
`┼`/`├`/`┤` where they cross a lane's own content. With color available, each branch gets its own
hue and every commit id shares one neutral hue across the diagram -- see
[docs/mermaid-gitgraph.md](mermaid-gitgraph.md) for more.

```mermaid
gitGraph
       commit
       commit
       branch nice_feature
       checkout nice_feature
       commit id: "3" tag: "v0.1"
       checkout main
       commit id: "4"
       checkout nice_feature
       branch very_nice_feature
       checkout very_nice_feature
       commit id: "5"
       checkout main
       commit id: "6"
       checkout nice_feature
       commit id: "7"
       checkout main
       merge nice_feature id: "customID" tag: "customTag" type: REVERSE
       checkout very_nice_feature
       commit id: "8"
       checkout main
       commit
       cherry-pick id: "8"
```

### Mindmap diagrams (VIEWMD-0045)

A `mindmap` block draws an indentation-defined tree radiating from a root: children fan out to the
right via `─╭─`/`─├─`/`─╰─` branch connectors, and once a single-direction fan would grow too tall
some root children overflow to the left instead. Mermaid shape markers (`(round)`, `[square]`,
`((circle))`, `{{hexagon}}`, `)cloud(`) are stripped to plain text; `**bold**` and `*italic*` spans
in a label render as real ANSI styling. See [docs/mermaid-mindmap.md](mermaid-mindmap.md) for more.

```mermaid
mindmap
  root((mindmap))
    Origins
      Long history
      Popularisation
        British popular psychology author Tony Buzan
    Research
      On effectiveness
      On automatic creation
    Tools
      Pen and paper
      Mermaid
```

### Block diagrams (VIEWMD-0040)

A `block-beta` (or bare `block`) diagram lays labeled boxes onto an explicit or implicit grid,
positioned by declaration order rather than by edges: a `columns N` directive fixes row width, and
a `:N` suffix lets a block span multiple columns, widening to match their combined width. Blocks
sharing a grid column equalize to the widest one in that column, even across rows. A block can
optionally connect to another same-row block with a plain flowchart-style `-->` arrow. See
[docs/mermaid-block.md](mermaid-block.md) for more.

```mermaid
block-beta
    columns 3
    A["Header"]:3
    B["Left"] C["Center"] D["Right"]
```

### XY charts (VIEWMD-0048)

An `xychart-beta` (or bare `xychart`) block plots one bar dataset, one line dataset, or both on the same axes: categories along the bottom, numeric values up the left. Bars fill with eighth-resolution block glyphs; lines are a rounded-corner step/staircase drawn on top of the bars in a combo chart. Plot size scales with `--width` (capped at the viewport, never narrower than half of it). See [docs/mermaid-xychart.md](mermaid-xychart.md) and [docs/nvidia-stock-xychart.md](nvidia-stock-xychart.md) for more.

```mermaid
xychart-beta
    title "Sales vs Target"
    x-axis [Q1, Q2, Q3, Q4]
    y-axis 0 --> 120
    bar  [40, 60, 80, 100]
    line [60, 80, 60, 120]
```

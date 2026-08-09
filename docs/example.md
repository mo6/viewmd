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
after it. The empty `reviewer:` field is omitted by default — pass `--full-front-matter` to show
it anyway.

## Text formatting

Paragraphs support **bold**, *italic*, ***bold italic***, ~~strikethrough~~, and `inline code`.

> A blockquote, for a callout or a quoted remark.

---

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

## Tables

| Feature          | Status      | Notes                                   |
|------------------|-------------|------------------------------------------|
| Headers          | done        | all six levels                            |
| Tables           | done        | this one                                  |
| Front matter     | done        | rendered as a table, see the top of this file |
| Wikilinks        | done        | see below                                 |
| Mermaid sequence | done        | see below                                 |
| Mermaid flowchart | done       | see below                                 |
| Mermaid ER diagram | done      | see below                                 |
| Mermaid pie chart | done       | see below                                 |

## Syntax-highlighted code

```python
def render(text: str, *, width: int, color: bool) -> str:
    """Render Markdown to an ANSI string, width columns wide."""
    return _console_render(text, width=width, color=color)
```

### A line too wide for the render width

An ordinary code line longer than the render width stays intact on one line rather than folding
onto a second (VIEWMD-0019) — same as a mermaid diagram (VIEWMD-0018). The line below is exactly
120 characters; at the default 100-column cap it should still render as a single unbroken line,
scrolling horizontally in the pager (`less -S`) instead of wrapping or being cut off:

```python
result = some_function(argument_one, argument_two, argument_three, argument_four, argument_five, argument_six, xxxxxxxx)
```

## Wikilinks

Obsidian-style wikilinks like [[Getting Started]] or [[Getting Started|a custom display name]]
render the same as an ordinary Markdown link, brackets gone.

## Mermaid diagrams

A fenced ` ```mermaid ` block containing a `sequenceDiagram`, `graph`/`flowchart`, `erDiagram`, or
`pie` renders as box-drawing art in place of its source. See
[docs/mermaid-examples.md](mermaid-examples.md) for an exhaustive tour of the first three — every
arrow type and fragment, every flowchart direction/subgraph/styling case, ER cardinality notation,
and the graceful-fallback behavior for diagram types that aren't supported yet. Four representative
examples here:

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

```mermaid
graph TD
    A[Start] --> B{Decision}
    B -->|yes| C[Do it]
    B -->|no| D[Skip it]
```

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

```mermaid
pie title Pets adopted by volunteers
    "Dogs" : 386
    "Cats" : 85
    "Rats" : 15
```

Diagram rows keep their natural width instead of being wrapped/padded to the render width
(VIEWMD-0018) — same as a wide code block's long lines (VIEWMD-0019); docs/mermaid-examples.md has
an example wide enough to demonstrate the horizontal scroll this produces in the pager.

### Pie charts render two ways, chosen by color (VIEWMD-0043)

Unlike the other three diagram types, a `pie` chart renders differently depending on whether color
is available. With color (the default on a real terminal — try the pie chart above, or run
`./viewmd.sh docs/example.md --color always`), it draws as an actual circle: each slice a distinct
truecolor region, a legend beside it, and its own size scaled to roughly 60% of what comfortably
fits the render width — try `--width 60` vs. `--width 200` against this file and compare. Without
color (`--color never`, `NO_COLOR` set, piped output, or a plain-ASCII terminal via `--ascii`-style
rendering), the same chart falls back to a horizontal bar chart instead — a circular pie was tried
without color and found illegible (jagged edges, indistinguishable slices), so the fallback is a
deliberate second design, not a lesser version of the first:

```
Pets adopted by volunteers

Dogs┃████████████████████████████████   79.4%
Cats┃███████   17.5%
Rats┃█▎    3.1%
```

Run `./viewmd.sh docs/example.md --color never` to see this file's pie chart render that way
instead.

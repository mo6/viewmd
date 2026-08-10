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

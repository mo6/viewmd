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

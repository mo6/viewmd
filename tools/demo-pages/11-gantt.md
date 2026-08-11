### Gantt charts (VIEWMD-0032)

A `gantt` block draws one row per task: a status-tagged bar (`done`/`active`/untagged/`crit`) or a
single `◆` point for a `milestone`, against a scaled timeline axis with full-height gridlines and
`section`-grouped rows. With color available, each status gets its own hue and `crit` tasks get a
distinct bracket color layered on top; a longer span switches the axis to week ticks and adds a
date-anchor line under the chart so `W<n>` labels still say what date they fall on. See
[docs/mermaid-gantt.md](mermaid-gantt.md) for the full worked mock-ups.

```mermaid
gantt
    title Release checklist
    dateFormat YYYY-MM-DD
    section Planning
        Spec review       :done, 2024-03-01, 3d
        Design sign-off    :active, 3d
    section Build
        Implement feature  :crit, active, 5d
        Ship release        :milestone, 2024-03-16, 0d
```

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

---
id: VIEWMD-0032
title: Render Mermaid Gantt charts
status: implemented
area: [render, mermaid]
effort: medium
created: 2026-08-06
updated: 2026-08-11
accepted_by: George Moses
accepted_at: 2026-08-11
commits: [1314772, 48ced38, 8a5f909, 0df9c05, 67a11e4, ec3b680, 2b97ac9]
related: []
supersedes: []
changelog: "[1.17.0]"
reason:
---

# Render Mermaid Gantt charts

## Summary

Add a fourth Mermaid diagram type -- `gantt` -- alongside the existing flowchart, sequence, and ER renderers (`viewmd/mermaid/{flowchart,sequence,er}/`). This first version targets a horizontal-bar-per-task representation with a scaled timeline axis (vertical gridlines included, not just top/bottom tick labels), `section` grouping, and `done`/`active`/`milestone` status-tag rendering -- not the full breadth of Mermaid's gantt syntax (`crit` styling, task dependencies beyond `after <id>`, weekend shading, etc.), those remain deferred, see Non-goals.

## Motivation / problem

`viewmd/mermaid/__init__.py:render` raises `UnsupportedDiagramError` for any `gantt` fence today -- it falls through all three `_is_*_diagram` sniffs. Gantt charts are one of Mermaid's most common diagram types (https://mermaid.ai/open-source/syntax/gantt.html) for project/task timelines, and are a natural fit for viewmd's box-drawing/ANSI rendering model: a task list with proportional bars is close to what a terminal can already draw well, similar in spirit to how `docs/` renders bar-style content today.

## Requirements

1. MUST recognize a ` ```mermaid ` fence beginning with `gantt` (`viewmd/mermaid/gantt/parser.py:sniff`, following the `sniff`/`parse`/`render` module shape already used by `flowchart`, `sequence`, and `er`) and wire it into `viewmd/mermaid/__init__.py:render` alongside the other three sniffs.
2. MUST parse `title <text>` (optional, rendered above the chart) and `dateFormat <fmt>` (informational for parsing task dates; `YYYY-MM-DD` MUST be supported, other formats MAY be deferred with a clear parse error rather than silently misinterpreted).
3. MUST parse `section <name>` lines, grouping the tasks that follow until the next `section` (or end of diagram) under that section's label.
4. MUST parse a task line of the form `<label> : <start>, <duration|end>` (Mermaid's basic syntax, optionally prefixed with `<id>,` for internal reference) where `<start>` is either an explicit date matching `dateFormat`, `after <id>` referencing a previously-declared task's end, or `until <id>` bounding the task's *end* at a previously-declared task's *start* (the task's own start is then whatever `<duration>` implies backward from that end, or the implicit-continuation default of 4a if no duration is given -- matching D2's `Add to mermaid :until isadded`). `<duration>` is a number followed by `d`/`w`/`h` (days/weeks/hours); an explicit end date in place of duration MUST also parse. Hour durations MUST be tracked precisely for date math (so chained `after <id>` references stay correct) even though rendering rounds each task's column width to the nearest whole day.
4a. MUST default a task's start to the end of the immediately preceding task in the diagram when the task line omits both an explicit date and `after <id>`/`until <id>` (e.g. `another task :24d`) -- real Mermaid's own implicit-chaining behavior, and exercised directly by both example gantt charts in mock-ups D1/D2 below (`another task`, and every un-prefixed duration-only line in D2's `Critical tasks`/`Last section`).
4b. MUST allow a task id to be reused across different sections within the same diagram (D2 redeclares `a1` in `Documentation` after it's also used elsewhere); a later `after <id>`/`until <id>` reference resolves to the most recently declared task carrying that id at the point of reference, not the first.
5. MUST render one row per task: the task label left-aligned in a fixed-width label column (sized to the longest label, section headers included), followed by a bar spanning the task's date range, filled with a glyph per requirement 5a below, proportional to the diagram's overall date span mapped onto the available terminal width.
5a. MUST parse an optional leading status tag (`done`, `active`, `milestone`, `crit`, or `crit` combined with `done`/`active`) on a task line (Mermaid's `<label> : [status,] [id,] start, duration` form) and render it distinctly: `done` MUST use a solid glyph (`█`), `active` a visibly lighter/different glyph (e.g. `▓`), an untagged (not-yet-started) task the lightest of the three (e.g. `░`), and `milestone` MUST render as a single point glyph (e.g. `◆`) rather than a bar, regardless of its (typically `0d`) duration. `crit` MUST render as an additional visual marker layered on top of whichever of `done`/`active`/untagged also applies (or on its own, untagged glyph, if `crit` is the only tag) -- bracket the bar with `[`/`]` markers immediately before/after its fill glyphs (already ASCII-safe, no separate fallback needed) rather than inventing a new glyph. Each status glyph MUST have a `use_ascii`-safe fallback per the existing `use_ascii` convention used elsewhere in `viewmd/mermaid/`.
6. MUST render section labels as their own header row (or inline prefix -- exact layout is a design decision for this issue, see mock-ups below) that visually groups the tasks under it, distinct from task rows.
7. MUST render a timeline axis (top and/or bottom of the chart) showing tick marks and labels at a reasonable interval given the overall date span (e.g. week numbers for a multi-week chart, like the mock-ups below) -- exact tick spacing/labelling is a design decision for this issue, not dictated by any upstream reference.
7a. MUST extend each axis tick as a vertical gridline (`|`) down through every row of the chart body, not just the top/bottom axis labels -- see mock-up D below. Where a task's bar overlaps a gridline column, the bar glyph takes precedence over the `|`.
7b. MUST automatically switch tick granularity based on the diagram's total date span rather than using a single fixed granularity always: week-level ticks (labelled `W<n>`) for longer spans, day-level ticks (labelled `MM-DD`, at a multi-day interval so labels don't collide) for shorter spans -- matching mock-up D1 (~7-week span, week ticks) vs. D2 (~19-day span, day ticks at 3-day intervals) below. The exact threshold between the two is an implementation judgment call (a span around 3-4 weeks is a reasonable boundary), not dictated by any upstream reference.
7c. MUST render an anchor line under the chart when in week-mode (requirement 7b), mapping every 4th `W<n>` tick to its absolute calendar date (`W<n>: YYYY-MM-DD`, comma-separated, aligned under the label column), since `W<n>` labels alone don't say what date the timeline starts from the way day-mode's already-absolute `MM-DD` labels do -- e.g. `W1: 2014-01-01, W5: 2014-01-29` for mock-up D1 (maintainer review feedback, 2026-08-11). Day-mode charts need no such line.
8. MUST parse an `excludes weekends` line when present and, when it is, skip Saturday/Sunday when computing a task's end date from a day/week duration (calendar-day math otherwise, per the Non-goals below `excludes <specific date>`/`excludes <day-of-week name>` stay unsupported for v1 -- a fence using either falls back to the raw-fence behavior of requirement 9).
9. MUST leave a `gantt` fence whose content fails to parse untouched (fall back to showing the raw fence), same fallback discipline as the other three Mermaid renderers' MUST-NOT-crash requirement.
10. MUST NOT change behavior for any existing recognized Mermaid diagram type (flowchart, sequence, er).
11. MUST tint each task's fill glyphs by status when the caller passes `color=True` (the same `--color` plumbing already read by `viewmd/mermaid/pie/renderer.py` and `viewmd/mermaid/quadrant/renderer.py`), one hue per `done`/`active`/untagged/`milestone` status, approximating Mermaid's own default gantt palette the same way the pie/quadrant renderers approximate theirs -- not a byte-for-byte theme match, since gantt has no upstream reference to port a palette from either (maintainer review feedback, 2026-08-11). `crit`'s bracket markers (requirement 5a) MUST get their own distinct hue, layered on top of whichever status hue the task's fill already carries, not a replacement for it. Grid lines, section headers, and the axis stay uncolored. `color` and `use_ascii` are independent, matching the quadrant renderer's convention (`--ascii` picks the glyph set, `--color` tints it, either can be on without the other).

## Non-goals

- `excludes <specific date>` and `excludes <day-of-week name>` (e.g. `excludes 2014-01-10`, `excludes monday`) -- only the bare `excludes weekends` form (requirement 8) is in scope for v1.
- Task dependencies beyond `after <id>`/`until <id>` chaining (requirements 4/4a/4b).
- Mermaid's `%%` directive comments, click interactions, and any non-`YYYY-MM-DD` `dateFormat` value.
- Matching any upstream reference implementation byte-for-byte -- `mermaid-ascii` (the Go reference `viewmd/mermaid/flowchart` was originally ported from) does not implement gantt charts at all, so there is no reference output to differential-test against. Fixtures for this issue are necessarily hand-authored/visually-verified, same posture as VIEWMD-0022's shape work.
- Terminal-width responsiveness beyond a reasonable fixed assumption -- matching how the other Mermaid renderers currently size their output is sufficient; a dedicated resize/reflow pass is out of scope here.

## Design notes / links

`viewmd/mermaid/__init__.py` is the dispatch point: add a `_is_gantt_diagram`/`_parse_gantt`/`_render_gantt` import trio and a fourth `if` branch, mirroring the `er` branch (parse-then-render, catching a module-local `ParseError` into `MermaidError`). New module lives at `viewmd/mermaid/gantt/` (`parser.py`, `renderer.py`), sibling to `viewmd/mermaid/{flowchart,sequence,er}/`. `viewmd/mermaid/grid/canvas.py`'s `use_ascii` fallback convention (unicode glyph with an ASCII-safe substitute) should be reused for the bar-fill glyph rather than inventing a new fallback scheme.

### Mock-ups (pending maintainer review)

Only one design survives from the earlier exploration (previous revisions of this issue also considered a compact single-line-per-task layout and a plain-`|` no-gridline layout; both are dropped, superseded by the layout below): section-grouped, aligned label column, a dual (top+bottom) tick axis, gridlines running the full height of the chart body using proper box-drawing characters (`┬`/`┴`/`─`/`│`) instead of plain `|`/`-`, and status-differentiated bar glyphs (`█` done, `▓` active, `░` untagged/not-yet-started, `◆` milestone point) per requirement 5a. Both mock-ups below render that one design against two real Mermaid examples the maintainer supplied, generated column-exactly from each example's actual parsed date math (not hand-aligned), to check the layout holds up under realistic, messier input rather than just the earlier hand-picked cases.

**Mock-up D1 -- the mermaid.js "basic" reference example**, exercising `section`, `after <id>` chaining, and requirement 4a's implicit-continuation default (`another task`'s `:24d` has no start at all -- it continues from the immediately preceding task, `Task in Another`, per 4a):

```
gantt
    title A Gantt Diagram
    dateFormat YYYY-MM-DD
    section Section
        A task          :a1, 2014-01-01, 30d
        Another task    :after a1, 20d
    section Another
        Task in Another :2014-01-12, 12d
        another task    :24d
```

resolves to (`a1` 01-01→01-31, `Another task` 01-31→02-20, `Task in Another` 01-12→01-24, `another task` 01-24→02-17; none of these four carry a status tag, so all four render in the untagged/`░` glyph):

```
A Gantt Diagram

                        W1     W2     W3     W4     W5     W6     W7     W8
                        ┬──────┬──────┬──────┬──────┬──────┬──────┬──────┬───
  Section
    A task              ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░     │      │      │
    Another task        │      │      │      │      │ ░░░░░░░░░░░░░░░░░░░░
  Another
    Task in Another     │      │   ░░░░░░░░░░░░     │      │      │      │
    another task        │      │      │      │ ░░░░░░░░░░░░░░░░░░░░░░░░  │
                        ┴──────┴──────┴──────┴──────┴──────┴──────┴──────┴───
                        W1     W2     W3     W4     W5     W6     W7     W8

                        W1: 2014-01-01, W5: 2014-01-29
```

**Mock-up D2 -- the mermaid.js "full syntax" reference example**, deliberately the messiest input tried against this design: four sections, `done`/`active`/`crit` combined on one task (`crit,done`), bare (unstatused) tasks meant to read as "future work" (matching this issue's untagged-means-not-yet-started interpretation), an hour-granularity duration (`24h`, `20h`, `48h`), a `milestone`, an `until <id>` end-bound, an `excludes weekends` line, and a reused task id (`a1`) across two different sections:

```
gantt
    dateFormat  YYYY-MM-DD
    title       Adding GANTT diagram functionality to mermaid
    excludes    weekends
    %% (`excludes` accepts specific dates in YYYY-MM-DD format, days of the week ("sunday") or "weekends", but not the word "weekdays".)

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

    section Documentation
    Describe gantt syntax               :active, a1, after des1, 3d
    Add gantt diagram to demo page      :after a1  , 20h
    Add another diagram to demo page    :doc1, after a1  , 48h

    section Last section
    Describe gantt syntax               :after doc1, 3d
    Add gantt diagram to demo page      :20h
    Add another diagram to demo page    :48h
```

`crit`, `excludes weekends`, hour-unit durations, and `until` are now in scope (requirements 4, 4b, 5a, 8) per the maintainer decisions below; the render below is illustrative of the same math described in the original mock-up write-up (calendar-day math with no weekend skipping applied to *this specific* render, hour durations rounded to the nearest whole day for column width, `until isadded` resolved as "ends when the referenced task starts"), except `crit` tasks now additionally get the `[`/`]` bracket treatment from requirement 5a layered onto whatever their other tag's glyph is (untagged `crit`-only tasks, e.g. `Future task in critical line`, get brackets around the `░` glyph rather than rendering identically to an untagged task):

```
Adding GANTT diagram functionality to mermaid

                                         01-06 01-09 01-12 01-15 01-18 01-21 01-24
                                         ┬─────┬─────┬─────┬─────┬─────┬─────┬───────
  A section
    Completed task                       ████  │     │     │     │     │     │
    Active task                          │     ▓▓▓▓▓▓│     │     │     │     │
    Future task                          │     │     ░░░░░░░░░░  │     │     │
    Future task2                         │     │     │     │   ░░░░░░░░░░    │
  Critical tasks
    Completed task in the critical line  ██    │     │     │     │     │     │
    Implement parser and jison           │   ████    │     │     │     │     │
    Create tests for parser              │     │ ▓▓▓▓▓▓    │     │     │     │
    Future task in critical line         │     │     │ ░░░░░░░░░░│     │     │
    Create tests for renderer            │     │     │     │     ░░░░  │     │
    Add to mermaid                       │     │     │     │     │   ░░░░░░░░░░
    Functionality added                  │     │     │     │     │     │     │ ◆
  Documentation
    Describe gantt syntax                │   ▓▓▓▓▓▓  │     │     │     │     │
    Add gantt diagram to demo page       │     │   ░░│     │     │     │     │
    Add another diagram to demo page     │     │   ░░░░    │     │     │     │
  Last section
    Describe gantt syntax                │     │     │ ░░░░░░    │     │     │
    Add gantt diagram to demo page       │     │     │     │ ░░  │     │     │
    Add another diagram to demo page     │     │     │     │   ░░░░    │     │
                                         ┴─────┴─────┴─────┴─────┴─────┴─────┴───────
                                         01-06 01-09 01-12 01-15 01-18 01-21 01-24
```

Note this settles requirement 7b's tick-interval switching in one direction for short spans: D1's ~7-week span uses week ticks, D2's ~19-day span switches to day-level ticks with `MM-DD` labels every 3 days -- both derived from the same "pick a tick interval so labels don't collide and gridlines stay legible" rule rather than a fixed choice, matching mock-up C's now-superseded daily-axis idea folded into this one design instead of being a separate layout. Note also the D2 render above predates the `crit` bracket decision below and so doesn't show it -- the actual D2 fixture (acceptance criteria below) MUST show `[`/`]` brackets around `Completed task in the critical line`, `Implement parser and jison`, `Create tests for parser`, and `Future task in critical line`, recomputed with the extra two columns those brackets need.

Maintainer decisions (2026-08-11, George Moses): (a) pull D2's `crit`, `excludes weekends`, hour-granularity, and `until` into this issue's scope rather than deferring them -- folded into requirements 4, 4b, 5a, and 8 above; (b) implement automatic week-vs-day tick-interval switching as a requirement (7b above), exact threshold left as an implementation judgment call; (c) allow reusing an already-declared task id across sections within one diagram (requirement 4b above), resolving `after`/`until` to the most recent declaration.

## Acceptance / verification

- Unit tests for the parser: `section` grouping, explicit-date, `after <id>`, and `until <id>` task starts, requirement 4a's implicit-continuation default, `d`/`w`/`h` durations, an explicit-end-date task, requirement 4b's id-reuse-across-sections resolution, `excludes weekends` skipping weekend days in duration math, and each of the `done`/`active`/`milestone`/`crit` status tags (including `crit` combined with `done`/`active`) plus the untagged (not-started) case.
- A rendered fixture (hand-verified, no upstream binary to diff against per Non-goals) reproducing mock-up D1 (`A Gantt Diagram`) byte-for-byte against this issue's own math, plus mock-up D2 (`Adding GANTT diagram functionality to mermaid`) in full, including the `crit` brackets noted above.
- A fixture exercising `use_ascii` mode's fallback glyphs for all four status states plus the `crit` bracket marker.
- A malformed `gantt` fence (e.g. a task line missing its `:` separator) falls back to showing the raw fence rather than crashing viewmd.
- Tests for requirement 11: no ANSI when `color=False` (the default); stripping ANSI from a `color=True` render reproduces the `color=False` render exactly; one distinct hue per status is present plus a distinct crit-marker hue on a `crit`-tagged task's brackets; `color` and `use_ascii` combine independently.
- `./run-tests.sh` green.

## Peer review

- George Moses (maintainer), 2026-08-11: reviewed the D1/D2 fixtures and live-rendered output across several rounds -- requested and confirmed the week-mode date-anchor line (requirement 7c), requested and confirmed status-based bar coloring (requirement 11), requested the demo page example be swapped to the D2 full-syntax mock-up and then trimmed to two sections for size. Approved to land.


---
id: VIEWMD-0035
title: Render Mermaid timeline diagrams
status: proposed
area: [render, mermaid]
effort: medium
created: 2026-08-06
updated: 2026-08-06
accepted_by:
accepted_at:
commits: []
related: [VIEWMD-0032, VIEWMD-0033, VIEWMD-0034]
supersedes: []
changelog:
reason:
---

# Render Mermaid timeline diagrams

## Summary

Add a seventh Mermaid diagram type -- `timeline` -- alongside the existing flowchart, sequence, ER, and (pending) gantt/journey/kanban renderers (`viewmd/mermaid/{flowchart,sequence,er}/`, [VIEWMD-0032](VIEWMD-0032-mermaid-gantt-charts.md), [VIEWMD-0033](VIEWMD-0033-mermaid-user-journey-diagrams.md), [VIEWMD-0034](VIEWMD-0034-mermaid-kanban-diagrams.md)). A timeline diagram (https://mermaid.ai/open-source/syntax/timeline.html) is a horizontal sequence of `section`-grouped time periods, each holding one or more events, rendered here as boxed period/event pairs strung along a horizontal timeline arrow -- modelled directly on real Mermaid's own output (see the mock-ups below). This is a first version -- see Non-goals for what's deliberately left out.

## Motivation / problem

`viewmd/mermaid/__init__.py:render` raises `UnsupportedDiagramError` for any `timeline` fence today -- it falls through every `_is_*_diagram` sniff. A timeline diagram is a distinct shape from anything currently supported: unlike flowchart/sequence/er's graph-of-nodes, gantt's date-scaled bars, journey's scored task track, or kanban's stacked columns, a timeline is a left-to-right period axis with a section banner spanning each group of periods above it and a stack of event boxes hanging below it -- a new rendering shape for `viewmd/mermaid/`, not a variation on an existing one.

## Requirements

1. MUST recognize a ` ```mermaid ` fence beginning with `timeline` (`viewmd/mermaid/timeline/parser.py:sniff`, following the `sniff`/`parse`/`render` module shape already used by the other diagram packages) and wire it into `viewmd/mermaid/__init__.py:render` alongside the existing sniffs.
2. MUST parse `title <text>` (optional, rendered centered above the chart).
3. MUST parse `section <name>` lines, grouping the periods that follow until the next `section` (or end of diagram) under that section's label, in declaration order. `section` MAY be absent entirely, in which case every period renders ungrouped (no section banner row).
4. MUST parse a period line `<period> : <event>` as that period's first event, in declaration order.
5. MUST parse a period line whose `<period>` label is blank (i.e. a line starting with `:`) as an additional event appended to the *previous* period rather than a new period -- real Mermaid's own continuation syntax for a period with more than one event, e.g. the reference example's `2300 BC` below has two `:`-prefixed follow-up lines, not two separate `2300 BC` periods.
6. MUST also accept multiple events for one period written on a single line as further `:`-separated segments (`<period> : <event1> : <event2>`), splitting on every colon after the first.
7. MUST recognize an explicit `<br>` inside an event's text as a forced line break (in addition to requirement 8's automatic word-wrap), matching `<br>`'s existing meaning elsewhere in `viewmd/mermaid/` (`viewmd/mermaid/grid/label.py:_HTML_BREAK_RE`).
8. MUST word-wrap a period's label and each of its events' text to a fixed content width inside their boxes (long, unbroken text like the reference example's `id2`-equivalent MUST wrap across multiple lines, not overflow or get truncated).
9. MUST render each section as its own box (`┌─┐│└┘`) spanning the combined width of its periods' boxes, each period as its own box directly below its section's box, and each of that period's events as its own box in a vertical stack directly below the period, all in declaration order, left-to-right -- see the mock-ups below for the specific layout. A period with no section renders without a section-row box above it.
10. MUST render a horizontal timeline axis between the period-box row and the first event-box row, spanning the full chart width with an arrowhead (`▶`) at its right end, and a dashed vertical drop-line (`┊`) from each period's horizontal center, running from the period box down through the axis to its first event box, and continuing below its last event box to end in a downward arrowhead (`▼`) -- see the mock-ups.
11. MUST render each section's period boxes and event boxes with a background color, one fixed hue per *section* in declaration order from the categorical palette `blue, orange, aqua, yellow, magenta, green, violet, red` (cycling past 8 sections), using 24-bit ANSI (`\x1b[48;2;r;g;bm`), with box text in a contrasting ink (light text on the darker/more saturated of these hues) -- note this is per-*section*, unlike [VIEWMD-0034](VIEWMD-0034-mermaid-kanban-diagrams.md)'s per-*column* kanban fill, since a timeline's sections (not its individual periods) are the categorical grouping. A period/event with no enclosing section renders without a background fill.
12. MUST leave a `timeline` fence whose content fails to parse untouched (fall back to showing the raw fence), same fallback discipline as the other Mermaid renderers' MUST-NOT-crash requirement.
13. MUST NOT change behavior for any existing recognized Mermaid diagram type.

## Non-goals

- Respecting `--color never`/`NO_COLOR` for this issue's new coloring (requirement 11) -- same pre-existing gap [VIEWMD-0034](VIEWMD-0034-mermaid-kanban-diagrams.md) already documents for `viewmd/mermaid/__init__.py:render`; not something specific to timeline, and not fixed here.
- The `---\nconfig:\n  timeline: ...\n---` YAML front-matter block Mermaid supports -- same posture as [VIEWMD-0034](VIEWMD-0034-mermaid-kanban-diagrams.md): a `timeline` fence that includes one should still render (ignoring the block), not fail to parse.
- Any interactivity, click handlers, or Mermaid's theming/`%%{init}%%` directives.
- Terminal-width responsiveness -- a five-or-six-period board (both reference examples below) is wide even in plain text; no reflow/wrap-columns-to-terminal-width behavior is in scope for v1, matching the other Mermaid renderers' current fixed-width posture.
- Matching any upstream reference implementation byte-for-byte -- there is no non-Mermaid reference renderer for this diagram type, so fixtures are necessarily hand-authored/visually-verified, same posture as VIEWMD-0022/0032/0033/0034.
- Per-column (rather than per-section) width independence beyond what wrapping already produces -- each period's box is sized to its own content (its label and its events' widest wrapped line), not forced to a uniform width across the whole chart; this is the layout the mock-ups below already use; there's no open question here to defer, unlike kanban's open question (a).

## Design notes / links

`viewmd/mermaid/__init__.py` is the dispatch point: add a `_is_timeline_diagram`/`_parse_timeline`/`_render_timeline` import trio and a seventh `if` branch, mirroring the `er` branch (parse-then-render, catching a module-local `ParseError` into `MermaidError`). New module lives at `viewmd/mermaid/timeline/` (`parser.py`, `renderer.py`), sibling to the other diagram packages. Card/event-label word-wrapping (requirement 8) can reuse whatever wrap helper [VIEWMD-0034](VIEWMD-0034-mermaid-kanban-diagrams.md) lands in `viewmd/mermaid/textutil.py`, if that issue ships first.

A proof-of-concept validating this layout end-to-end (parser, per-section coloring, multi-event stacking, `<br>` handling, both reference examples below) lives at `poc/timeline/timeline_poc.py` (run with `python3 poc/timeline/timeline_poc.py poc/timeline/industry.mmd` or `poc/timeline/england.mmd`, `--color always|never|auto`) -- a throwaway script, not shipped code, but its column-width/drop-line/stacking math is exactly what the real renderer needs to reproduce.

**Color values** (requirement 11) are the validated default palette from Anthropic's `dataviz` skill (`references/palette.md`), reused here rather than invented fresh, same 8-hue categorical order [VIEWMD-0034](VIEWMD-0034-mermaid-kanban-diagrams.md) already uses for its column-header backgrounds: `blue #2a78d6/#3987e5, orange #eb6834/#d95926, aqua #1baf7a/#199e70, yellow #eda100/#c98500, magenta #e87ba4/#d55181, green #008300/#008300, violet #4a3aa7/#9085e9, red #e34948/#e66767` (light/dark). `viewmd/mermaid/grid/canvas.py:wrap_text_in_color` only wraps *foreground* truecolor today; a background counterpart is needed here, same gap [VIEWMD-0034](VIEWMD-0034-mermaid-kanban-diagrams.md) already identifies -- whichever issue lands first should add it to `canvas.py` for the other to reuse.

### Mock-up 1 (pending maintainer review)

Renders the maintainer-supplied reference example:

```
timeline
    title Timeline of Industrial Revolution
    section 17th-20th century
        Industry 1.0 : Machinery, Water power, Steam <br>power
        Industry 2.0 : Electricity, Internal combustion engine, Mass production
        Industry 3.0 : Electronics, Computers, Automation
    section 21st century
        Industry 4.0 : Internet, Robotics, Internet of Things
        Industry 5.0 : Artificial intelligence, Big data, 3D printing
```

Modelled on real Mermaid's own rendering (the maintainer supplied a screenshot: a section banner row, a period-box row, a horizontal timeline arrow with dashed drop-lines through it, and an event-box row below, each row's boxes background-filled per section). Adapted to box-drawing/ASCII: `┌─┐│└┘` for section/period/event boxes, `┊` for the dashed drop, `▶`/`▼` for the axis's and each drop-line's arrowheads. Generated column-exactly (box widths, word-wrap, section spans, and drop-line positions all computed from the data by `poc/timeline/timeline_poc.py`, not hand-aligned) -- section fill shown here as a `[section: <hue>]` tag beneath each banner (**this plain-text `.md` issue file can't display real ANSI color**, unlike a terminal actually interpreting the ANSI the renderer emits; ANSI escapes still stand in for text color and are just not visible when this file itself is rendered):

```
                                   Timeline of Industrial Revolution

┌─────────────────────────────────────────────────────────┐ ┌──────────────────────────────────────────┐
│                    17th-20th century                    │ │               21st century               │
└━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┘ └━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┘
     [section 1: blue bg]                                        [section 2: orange bg]

┌──────────────────┐┌─────────────────────┐┌──────────────┐ ┌─────────────────────┐┌───────────────────┐
│   Industry 1.0   ││    Industry 2.0     ││ Industry 3.0 │ │    Industry 4.0     ││   Industry 5.0    │
└━━━━━━━━━━━━━━━━━━┘└━━━━━━━━━━━━━━━━━━━━━┘└━━━━━━━━━━━━━━┘ └━━━━━━━━━━━━━━━━━━━━━┘└━━━━━━━━━━━━━━━━━━━┘
          ┊                    ┊                   ┊                   ┊                     ┊
          ┊                    ┊                   ┊                   ┊                     ┊
──────────┼────────────────────┼───────────────────┼───────────────────┼─────────────────────┼──────────▶
          ┊                    ┊                   ┊                   ┊                     ┊
          ┊                    ┊                   ┊                   ┊                     ┊
┌──────────────────┐┌─────────────────────┐┌──────────────┐ ┌─────────────────────┐┌───────────────────┐
│ Machinery, Water ││    Electricity,     ││ Electronics, │ │ Internet, Robotics, ││    Artificial     │
│   power, Steam   ││ Internal combustion ││  Computers,  │ │ Internet of Things  ││ intelligence, Big │
│      power       ││    engine, Mass     ││  Automation  │ │                     ││ data, 3D printing │
│                  ││     production      ││              │ │                     ││                   │
└━━━━━━━━━━━━━━━━━━┘└━━━━━━━━━━━━━━━━━━━━━┘└━━━━━━━━━━━━━━┘ └━━━━━━━━━━━━━━━━━━━━━┘└━━━━━━━━━━━━━━━━━━━┘
          ┊                    ┊                   ┊                   ┊                     ┊
          ▼                    ▼                   ▼                   ▼                     ▼
```

Note `Industry 1.0`'s event (`Machinery, Water power, Steam <br>power`) demonstrates requirement 7: the explicit `<br>` forces the break before "power" rather than leaving it to automatic wrapping.

### Mock-up 2 (pending maintainer review) -- multi-event periods and `<br>`

The maintainer additionally supplied a second reference example and screenshot specifically to exercise a period with more than one event (requirements 5-6) and further `<br>` usage (requirement 7):

```
timeline
        title England's History Timeline
        section Stone Age
          7600 BC : Britain's oldest known house was built in Orkney, Scotland
          6000 BC : Sea levels rise and Britain becomes an island.<br> The people who live here are hunter-gatherers.
        section Bronze Age
          2300 BC : People arrive from Europe and settle in Britain. <br>They bring farming and metalworking.
                  : New styles of pottery and ways of burying the dead appear.
          2200 BC : The last major building works are completed at Stonehenge.<br> People now bury their dead in stone circles.
                  : The first metal objects are made in Britain.Some other nice things happen. it is a good time to be alive.
```

`2300 BC` and `2200 BC` each carry two events -- a first event on the `period : event` line, a second on a following `: event` line with no period label (requirement 5). Per the maintainer's screenshot, a period's *second* event box stacks directly beneath its first, along the same drop-line, and a period with only one event has no second box (variable stack height, not padded to match a neighboring period's taller stack):

```
                                 England's History Timeline

┌─────────────────────────────────────────┐ ┌──────────────────────────────────────────────┐
│                Stone Age                │ │                  Bronze Age                  │
└━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┘ └━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┘
        [section 1: blue bg]                              [section 2: orange bg]

┌──────────────────┐┌─────────────────────┐ ┌──────────────────────┐┌──────────────────────┐
│     7600 BC      ││       6000 BC       │ │       2300 BC        ││       2200 BC        │
└━━━━━━━━━━━━━━━━━━┘└━━━━━━━━━━━━━━━━━━━━━┘ └━━━━━━━━━━━━━━━━━━━━━━┘└━━━━━━━━━━━━━━━━━━━━━━┘
          ┊                    ┊                        ┊                       ┊
          ┊                    ┊                        ┊                       ┊
──────────┼────────────────────┼────────────────────────┼───────────────────────┼───────────▶
          ┊                    ┊                        ┊                       ┊
          ┊                    ┊                        ┊                       ┊
┌──────────────────┐┌─────────────────────┐ ┌──────────────────────┐┌──────────────────────┐
│ Britain's oldest ││ Sea levels rise and │ │  People arrive from  ││    The last major    │
│ known house was  ││ Britain becomes an  │ │ Europe and settle in ││  building works are  │
│ built in Orkney, ││       island.       │ │       Britain.       ││     completed at     │
│     Scotland     ││ The people who live │ │  They bring farming  ││     Stonehenge.      │
│                  ││  here are hunter-   │ │  and metalworking.   ││   People now bury    │
│                  ││     gatherers.      │ │                      ││ their dead in stone  │
│                  ││                     │ │                      ││       circles.       │
└━━━━━━━━━━━━━━━━━━┘└━━━━━━━━━━━━━━━━━━━━━┘ └━━━━━━━━━━━━━━━━━━━━━━┘└━━━━━━━━━━━━━━━━━━━━━━┘
          ┊                    ┊                        ┊                       ┊
                                            ┌──────────────────────┐┌──────────────────────┐
                                            │    New styles of     ││   The first metal    │
                                            │ pottery and ways of  ││ objects are made in  │
                                            │   burying the dead   ││  Britain.Some other  │
                                            │       appear.        ││ nice things happen.  │
                                            │                      ││ it is a good time to │
                                            │                      ││      be alive.       │
                                            └━━━━━━━━━━━━━━━━━━━━━━┘└━━━━━━━━━━━━━━━━━━━━━━┘
          ┊                    ┊                        ┊                       ┊
          ▼                    ▼                        ▼                       ▼
```

Both mock-ups above are the exact output of `poc/timeline/timeline_poc.py` (run with `--color never`); the real per-section background fill (requirement 11) is visible when run without that flag, or with `--color always`.

Open questions for maintainer sign-off: (a) whether `7600 BC`/`6000 BC` (Stone Age, one event each) ending their drop-lines shorter than `2300 BC`/`2200 BC` (Bronze Age, two events each) is right, or whether every period's drop-line/arrowhead should align to the tallest stack in the whole chart regardless of section, for a level bottom edge; (b) the wrap width used above (20 content columns) is a v1 guess, not derived from anything upstream -- worth an explicit number in the requirements, or left as an implementation detail; (c) whether a period with no `section` at all (requirement 3's ungrouped case, not exercised by either reference example) should reserve blank vertical space where the section banner row would have gone, so period-box tops still align across a chart mixing grouped and ungrouped periods, or omit the row entirely as the current wording implies.

## Acceptance / verification

- Unit tests for the parser: `title` parsing, `section` grouping (including the no-`section`-at-all case), single-event and multi-event period lines (both the `: event` continuation-line form and the same-line `<period> : e1 : e2` form), and `<br>` recognized inside an event's text.
- A rendered fixture (hand-verified, no upstream binary to diff against per Non-goals) reproducing Mock-up 1 (the Industrial Revolution example) above.
- A rendered fixture reproducing Mock-up 2 (the England's History example) above, covering multi-event stacking and mixed `<br>`/no-`<br>` events in the same diagram.
- A fixture asserting the emitted ANSI escapes: per-section background fill (requirement 11), cycling the categorical palette past 8 sections.
- A malformed `timeline` fence (e.g. an event-continuation line before any period has been declared) falls back to showing the raw fence rather than crashing viewmd.
- `./run-tests.sh` green.

## Peer review


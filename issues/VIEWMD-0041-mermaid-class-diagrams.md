---
id: VIEWMD-0041
title: Render Mermaid class diagrams
status: proposed
area: [render, mermaid]
effort: high
created: 2026-08-08
updated: 2026-08-09
accepted_by:
accepted_at:
commits: []
related: [VIEWMD-0040]
supersedes: []
changelog:
reason:
---

# Render Mermaid class diagrams

## Summary

Add an eighth Mermaid diagram type -- `classDiagram` -- alongside the existing flowchart,
sequence, and ER renderers (`viewmd/mermaid/{flowchart,sequence,er}/`) and the diagram types
proposed in [VIEWMD-0032](VIEWMD-0032-mermaid-gantt-charts.md) through
[VIEWMD-0040](VIEWMD-0040-mermaid-block-beta-diagrams.md). A class diagram
(https://mermaid.js.org/syntax/classDiagram.html) renders UML class boxes -- name, optional
stereotype, attributes, methods, each in its own compartment -- connected by typed UML
relationship lines (inheritance, realization, composition, aggregation, plain association), each
with its own line style and end-glyph. This is a first version -- see Non-goals for what's
deliberately left out.

## Motivation / problem

`viewmd/mermaid/__init__.py:render` raises `UnsupportedDiagramError` for any `classDiagram` fence
today -- it falls through every `_is_*_diagram` sniff. A class diagram's boxes are close cousins
of an ER entity box (`viewmd/mermaid/er/`, itself a compartmented box with a header and rows) and
its relationships are close cousins of flowchart edges (`viewmd/mermaid/flowchart/`,
`viewmd/mermaid/grid/canvas.py:draw_line`), but the specific glyph vocabulary -- hollow triangle
for inheritance/realization, filled/hollow diamond for composition/aggregation, dashed vs. solid
line per relationship kind -- is unique to UML class notation and doesn't exist in either sibling
renderer yet.

## Requirements

1. MUST recognize a ` ```mermaid ` fence beginning with `classDiagram`
   (`viewmd/mermaid/classdiagram/parser.py:sniff`, following the `sniff`/`parse`/`render` module
   shape already used by the other diagram packages) and wire it into
   `viewmd/mermaid/__init__.py:render` alongside the existing sniffs.
2. MUST parse a `class Name { ... }` block: an optional `<<stereotype>>` line first, then member
   lines in declaration order, each either an attribute (`+String name`, `+float radius`) or a
   method (`+draw()`, `+area() float`, trailing return type optional) -- a member line is a
   method iff it contains `(`...`)`, matching Mermaid's own rule.
3. MUST parse a bare `class Name` declaration with no body (no braces at all) as a class with an
   empty member list, per the fourth reference example's `Car`/`Engine`/`Wheel`/`Driver`.
4. MUST recognize a class referenced only via a relationship line (never given its own `class`
   declaration) as an implicitly-declared empty class, so `Shape <|.. Circle` alone (without a
   preceding `class Shape` block) still renders a `Shape` box.
5. MUST render a class box with up to three compartments, each separated by a `├─┤` divider,
   omitting a divider between two compartments where the one below is empty (per the fourth
   reference example's boxes, which have a name-only header and no divider at all since both
   attribute and method compartments are empty):
   - header: the `«stereotype»` line (if present, per requirement 6) above the centered class
     name;
   - attributes, one per line, in declaration order;
   - methods, one per line, in declaration order.
6. MUST render a `<<stereotype>>` line as `«stereotype»` (guillemets, not the literal `<<`/`>>`
   delimiters), centered above the class name inside the header compartment, per the first
   reference example's `Shape`.
7. MUST parse and render the five relationship operators between two already-declared-or-implicit
   class ids, each with its own line style and end-glyph, per the reference examples:
   - `<|..` realization: dashed line (`┆`/`┊`), hollow triangle (`△`) at the interface end;
   - `<|--` inheritance: solid line (`│`), hollow triangle (`△`) at the parent end;
   - `*--` composition: solid line, filled diamond (`◆`) at the whole/container end;
   - `o--` aggregation: solid line, hollow diamond (`◇`) at the whole/container end;
   - `-->` association: solid line, solid arrowhead (`▼`/`▲`/`►`/`◄`) at the target end, its glyph
     computed from the target's actual laid-out position relative to the source (MUST NOT be
     hardcoded to a fixed direction) -- see requirement 7a.
7a. MUST determine an association's arrowhead glyph (requirement 7) from where the source and
   target boxes actually ended up after layout, not from declaration order or a fixed assumption
   -- a `-->` relationship whose target is laid out above its source MUST render `▲`, not `▼`.
   This matters concretely: reversing the fourth reference example's association to
   `Car --> Driver : owns` (same two classes, `Driver` still drawn above `Car` as the fan-out's
   extra leaf, per requirement 9a) must render `▲` pointing up into `Driver`, the actual target
   -- hardcoding `▼` there would render a backwards diagram (visually reading as "Driver owns
   Car," the opposite of what was declared), not merely a less faithful one.
8. MUST parse an optional `: label` trailing a relationship line and render it beside the
   connector, per the fourth reference example's `has` / `has 4` / `drives` labels.
9. MUST lay out a chain of inheritance/realization relationships vertically -- parent directly
   above child, connected by a straight vertical line -- per the first and third reference
   examples.
9a. MUST lay out a parent with two OR MORE composition/aggregation/association children as an
   approximate tree, generalizing the fourth reference example's two-child case to N children:
   the parent centered above a single horizontal branch bar spanning every child's center, a
   plain vertical line from the parent down to the bar, then a straight vertical line from each
   end (and each interior child position) of the bar down through that relationship's end-glyph
   (diamond or arrowhead) and label to the child below it. Where the parent's own down-line meets
   the bar at a column that is *also* a child's branch-down column (e.g. an odd child count with
   one child centered directly under the parent), the two junctions MUST merge into a single
   four-way `┼`, reusing the same junction-merging already needed for the two-child `┴` case
   rather than stacking separate glyphs -- per the new reference example below. This deliberately
   trades the exact upstream Mermaid geometry (diamonds sitting side-by-side directly under the
   parent, asymmetric corner routing) for a simpler shape that reuses one corner/branch primitive
   per fan-out instead of one path per child.
9b. MUST allow a class to simultaneously sit below an inheritance/realization parent (requirement
   9) and above a composition/aggregation/association fan-out of its own (requirement 9a) by
   stacking the two connectors on that class's own box -- the inheritance connector attaches to
   the box's top edge, the fan-out's branch bar attaches to the box's bottom edge, independently
   of each other -- per the new reference example below. No new layout primitive is needed for
   this case beyond composing 9 and 9a on the same box.
10. MUST leave a `classDiagram` fence whose content fails to parse untouched (fall back to
    showing the raw fence), same fallback discipline as the other Mermaid renderers'
    MUST-NOT-crash requirement.
11. MUST NOT change behavior for any existing recognized Mermaid diagram type.

## Non-goals

- Visibility modifiers beyond passing `+`/`-`/`#`/`~` through as literal prefix characters (as the
  reference examples already do) -- translating them into a different glyph, hiding private
  members, or validating the modifier vocabulary is out of scope.
- Generics/templates (`List~string~`), static/abstract member markers (`$`/`*` suffixes), and
  annotations other than a single leading `<<stereotype>>` line.
- Multiplicity/cardinality notation on relationship ends (`"1" --> "many"`) -- only the plain
  `: label` form (requirement 8) is in scope.
- Namespaces (`namespace Foo { ... }`) and interaction/notes (`note for Class "..."`).
- Any relationship layout beyond a single vertical inheritance/realization chain (requirement 9),
  the N-ary fan-out tree approximation (requirement 9a), and the two composed on the same class
  (requirement 9b) -- diagrams whose relationship graph doesn't reduce to one of those shapes
  (e.g. diamond-shaped multiple inheritance, cross-linked non-tree graphs, a fan-out child that is
  itself a fan-out parent -- i.e. nesting two levels deep, as opposed to 9b's single inheritance-
  above/fan-out-below composition on one box) MAY render with a simpler/less faithful layout; this
  issue does not require a general graph-layout engine equivalent to flowchart's.
- Matching upstream Mermaid's own branching-connector geometry pixel-for-pixel (the side-by-side
  diamond pair directly under the parent, asymmetric corner routing) -- requirement 9a is a
  deliberate, simpler approximation instead; see Design notes.
- Click handlers, `%%{init}%%` theming, and CSS class styling (`cssClass`, `classDef` for class
  diagrams).
- Terminal-width responsiveness/reflow -- fixed-width rendering, matching the other Mermaid
  renderers' current posture.
- Matching any upstream reference implementation byte-for-byte -- the local `mermaid-ascii` Go
  oracle used for differential testing the flowchart/sequence/ER ports has no `classDiagram`
  support, so fixtures here are necessarily hand-authored against the maintainer-supplied
  reference examples below (same posture as VIEWMD-0032/0033/0034/0040).

## Design notes / links

`viewmd/mermaid/__init__.py` is the dispatch point: add a
`_is_class_diagram`/`_parse_class_diagram`/`_render_class_diagram` import trio and an eighth `if`
branch, mirroring the `er` branch (parse-then-render, catching a module-local `ParseError` into
`MermaidError`). New module lives at `viewmd/mermaid/classdiagram/` (`parser.py`, `renderer.py`),
sibling to the other diagram packages. The compartmented box itself is close enough to
`viewmd/mermaid/er/renderer.py`'s entity box (header + divided rows) that it's worth checking
whether that box-drawing can be factored out and reused rather than reimplemented; the connector
glyphs (requirement 7) are new vocabulary not present in `viewmd/mermaid/grid/canvas.py` today
(only the flowchart arrowhead exists there) and will need their own small glyph table, likely
alongside `canvas.py:draw_line`/`_box_glyphs`.

Vertical layout for a pure inheritance/realization chain (requirement 9) is a straightforward
stack. The fourth reference example's branching layout (`Driver --> Car`, then `Car` splitting
into `*-- Engine` and `o-- Wheel`) uses the approximate tree shape from requirement 9a instead of
upstream Mermaid's own geometry: one plain `┌─┴─┐` branch bar centered under the parent (reusing
the same corner-junction shape flowchart already draws, `viewmd/mermaid/grid/canvas.py`'s
`merge_junctions`/`is_junction_char`), then a straight vertical drop -- end-glyph, label, line --
from each end of that bar down to its child. This is deliberately simpler than routing an L-shaped
path with the diamond sitting at the parent end for each child individually (upstream Mermaid's
actual rendering): it needs only one branch-bar primitive per fan-out point plus the existing
straight-vertical-connector logic from requirement 9, rather than a bespoke path per child.

### Reference examples (maintainer-supplied)

```
--- source ---
classDiagram
    class Shape {
        <<interface>>
        +draw()
        +area() float
    }
    class Circle {
        +float radius
        +draw()
        +area() float
    }
    Shape <|.. Circle
--- rendered ---

  ┌───────────────┐
  │  «interface»  │
  │     Shape     │
  ├───────────────┤
  │ +draw()       │
  │ +area() float │
  └───────────────┘
          △
          ┆
  ┌───────────────┐
  │    Circle     │
  ├───────────────┤
  │ +float radius │
  ├───────────────┤
  │ +draw()       │
  │ +area() float │
  └───────────────┘
```

```
--- source ---
classDiagram
    class Animal {
        +String name
        +int age
        +makeSound()
    }
--- rendered ---

  ┌──────────────┐
  │    Animal    │
  ├──────────────┤
  │ +String name │
  │ +int age     │
  ├──────────────┤
  │ +makeSound() │
  └──────────────┘
```

```
--- source ---
classDiagram
    class Animal {
        +String name
        +makeSound()
    }
    class Dog {
        +String breed
        +bark()
    }
    Animal <|-- Dog
--- rendered ---

  ┌──────────────┐
  │    Animal    │
  ├──────────────┤
  │ +String name │
  ├──────────────┤
  │ +makeSound() │
  └──────────────┘
          △
          │
  ┌───────────────┐
  │      Dog      │
  ├───────────────┤
  │ +String breed │
  ├───────────────┤
  │ +bark()       │
  └───────────────┘
```

```
--- source ---
classDiagram
    class Car
    class Engine
    class Wheel
    class Driver
    Car *-- Engine : has
    Car o-- Wheel : has 4
    Driver --> Car : drives
--- rendered ---

            ┌──────────────┐
            │    Driver    │
            └──────────────┘
                    │ drives
                    ▼
            ┌──────────────┐
            │     Car      │
            └──────────────┘
                    │
          ┌─────────┴─────────┐
          │                   │
          ◆ has               ◇ has 4
  ┌──────────────┐    ┌──────────────┐
  │    Engine    │    │    Wheel     │
  └──────────────┘    └──────────────┘
```

This is requirement 9a's approximate tree routing: one branch bar under `Car`, then a straight
drop into each child's diamond/label -- simpler than, and not a byte-for-byte match to, upstream
Mermaid's own side-by-side-diamond geometry for the same input.

**Three-plus children (requirement 9a, generalized):**

```
--- source ---
classDiagram
    class Car
    class Engine
    class Wheel
    class Radio
    Car *-- Engine : has
    Car o-- Wheel : has 4
    Car *-- Radio : has
--- rendered ---

                      ┌──────────────┐
                      │     Car      │
                      └──────────────┘
                              │
          ┌───────────────────┼───────────────────┐
          │                   │                   │
          ◆ has               ◇ has 4             ◆ has
  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐
  │    Engine    │    │    Wheel     │    │    Radio     │
  └──────────────┘    └──────────────┘    └──────────────┘
```

With an odd child count, the middle child sits exactly under `Car`, so the parent's down-line and
that child's branch-down column are the same column -- the two junctions merge into a single `┼`
(requirement 9a) instead of a `┴` immediately above a separate `┬`.

**A class both an inheritance child and a fan-out parent (requirement 9b):**

```
--- source ---
classDiagram
    class Vehicle
    class Car
    class Engine
    class Wheel
    Vehicle <|-- Car
    Car *-- Engine : has
    Car o-- Wheel : has 4
--- rendered ---

            ┌──────────────┐
            │   Vehicle    │
            └──────────────┘
                    △
                    │
            ┌──────────────┐
            │     Car      │
            └──────────────┘
                    │
          ┌─────────┴─────────┐
          │                   │
          ◆ has               ◇ has 4
  ┌──────────────┐    ┌──────────────┐
  │    Engine    │    │    Wheel     │
  └──────────────┘    └──────────────┘
```

`Car`'s box is unchanged by having two kinds of relationship attached to it -- the inheritance
triangle connects to its top edge exactly as in the third reference example, and the fan-out
branch bar connects to its bottom edge exactly as in the fourth reference example. No interaction
between the two is needed since they attach to opposite edges of the same box.

**Maintainer decision:** an association's arrowhead glyph is computed from the target's actual
laid-out position (requirement 7a), not hardcoded to a fixed direction.

**Arrowhead orientation (requirement 7a):** the fourth reference example with its one association
reversed -- `Car --> Driver : owns` instead of `Driver --> Car : drives`, same two classes, same
box positions (`Driver` is still the fan-out's extra leaf, still drawn above `Car`):

```
--- source ---
classDiagram
    class Car
    class Engine
    class Wheel
    class Driver
    Car *-- Engine : has
    Car o-- Wheel : has 4
    Car --> Driver : owns
--- rendered ---

            ┌──────────────┐
            │    Driver    │
            └──────────────┘
                    ▲
                    │ owns
            ┌──────────────┐
            │     Car      │
            └──────────────┘
                    │
          ┌─────────┴─────────┐
          │                   │
          ◆ has               ◇ has 4
  ┌──────────────┐    ┌──────────────┐
  │    Engine    │    │    Wheel     │
  └──────────────┘    └──────────────┘
```

The box layout is identical to the fourth reference example -- only the arrowhead differs (`▲`
instead of `▼`), because `Driver`, not `Car`, is now the target. A renderer that hardcoded `▼`
for every vertical association connector would draw this arrowhead pointing into `Car` instead,
misrepresenting the declared relationship.

## Acceptance / verification

- Unit tests for the parser: `class Name { ... }` with a stereotype line, attribute-only body,
  method-only body, mixed body, bare `class Name` with no braces, an implicitly-declared class
  referenced only via a relationship, and each of the five relationship operators with and without
  a trailing `: label`.
- A rendered fixture for each of the four reference examples above, hand-verified against the
  maintainer-supplied output (per Non-goals, no oracle to differential-test against).
- A rendered fixture for the three-child fan-out example (requirement 9a), confirming the `┼`
  junction merge when a child sits directly under the parent (odd child count).
- A rendered fixture for the inheritance-above/fan-out-below example (requirement 9b).
- A rendered fixture for the reversed-association example (requirement 7a), confirming `▲` is
  emitted (not a hardcoded `▼`) when the target is laid out above the source.
- A fixture covering a class with an empty body (name-only box, no dividers) alongside one with a
  populated body, confirming divider omission (requirement 5) is per-class, not global.
- A malformed `classDiagram` fence (e.g. a relationship referencing an operator not in
  requirement 7's list) falls back to showing the raw fence rather than crashing viewmd.
- `./run-tests.sh` green.

## Peer review


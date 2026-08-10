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

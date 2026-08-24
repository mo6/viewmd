# Topics

Reproduction fixture for [VIEWMD-0106](../issues/VIEWMD-0106-mark-region-nested-inside-a-list-item.md) — a sanitized version of the structural shape gitgleam actually generates when a new bullet is appended to an existing list: the `viewmd:mark` sentinels sit *between two list items of the same list*, not between two top-level blocks. Render it with color to confirm the third bullet below is tinted green like any other marked block, not silently left untinted (VIEWMD-0104's original top-level-only matching missed exactly this case).

```
./viewmd.sh --color=always docs/mark-highlight-example-list-item.md
```

- First existing item, unmarked.
- Second existing item, unmarked.
<!-- viewmd:mark start kind=added -->
- Third item, newly added and marked.
<!-- viewmd:mark end -->

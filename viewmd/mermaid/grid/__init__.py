"""Shared grid-diagram engine (coordinates, A* routing, canvas drawing, label
text model), ported from the non-flowchart-specific parts of `cmd/` in
github.com/AlexanderGrooff/mermaid-ascii. Generic across any diagram type that
lays nodes out on an integer grid and routes edges between them -- currently
used by `viewmd.mermaid.flowchart`, not tied to it."""

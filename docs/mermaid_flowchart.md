# Combined fixtures: mermaid_flowchart (*.mmd)

## bare_graph_no_direction

Source:

```
graph
  A --> B
```

Rendered:

```mermaid
graph
  A --> B
```

## basic_two_nodes

Source:

```
graph TD
  A[Start] --> B[End]
```

Rendered:

```mermaid
graph TD
  A[Start] --> B[End]
```

## bidirectional

Source:

```
graph TD
  A[Client] <-->|sync| B[Server]
```

Rendered:

```mermaid
graph TD
  A[Client] <-->|sync| B[Server]
```

## bt_rl_alias

Source:

```
graph BT
  A --> B
```

Rendered:

```mermaid
graph BT
  A --> B
```

## classdef_color

Source:

```
graph TD
classDef red fill:#f96,color:#ff0000
A[Start]:::red --> B[End]
```

Rendered:

```mermaid
graph TD
classDef red fill:#f96,color:#ff0000
A[Start]:::red --> B[End]
```

## complex_backend

Source:

```
graph LR
  subgraph Frontend
    UI[UI] --> API[API Client]
  end
  subgraph Backend
    Server[Server] --> DB[(Database)]
    Server --> Cache[(Cache)]
  end
  API --> Server
  DB --> Server
  Cache --> Server
```

Rendered:

```mermaid
graph LR
  subgraph Frontend
    UI[UI] --> API[API Client]
  end
  subgraph Backend
    Server[Server] --> DB[(Database)]
    Server --> Cache[(Cache)]
  end
  API --> Server
  DB --> Server
  Cache --> Server
```

## diamond_merge

Source:

```
graph TD
  A --> B
  A --> C
  B --> D
  C --> D
```

Rendered:

```mermaid
graph TD
  A --> B
  A --> C
  B --> D
  C --> D
```

## long_labels

Source:

```
graph TD
  A[This is a rather long label for testing width] --> B[Another long one here too]
```

Rendered:

```mermaid
graph TD
  A[This is a rather long label for testing width] --> B[Another long one here too]
```

## lr_direction

Source:

```
graph LR
  A --> B --> C
  A & B --> D
```

Rendered:

```mermaid
graph LR
  A --> B --> C
  A & B --> D
```

## multiline_label

Source:

```
graph TD
  A[Line one<br/>Line two] --> B[Single]
```

Rendered:

```mermaid
graph TD
  A[Line one<br/>Line two] --> B[Single]
```

## obstacle_routing

Source:

```
graph TD
  A --> B
  A --> C
  B --> D
  C --> D
  A --> D
```

Rendered:

```mermaid
graph TD
  A --> B
  A --> C
  B --> D
  C --> D
  A --> D
```

## parallel_edges

Source:

```
graph TD
  A --> B
  A --> B
  A --> B
```

Rendered:

```mermaid
graph TD
  A --> B
  A --> B
  A --> B
```

## self_loop

Source:

```
graph TD
  A --> A
  A --> B
```

Rendered:

```mermaid
graph TD
  A --> A
  A --> B
```

## shape_circle

Source:

```
graph TD
A((Circle))
```

Rendered:

```mermaid
graph TD
A((Circle))
```

## shape_cylinder

Source:

```
graph TD
A[(Database)]
```

Rendered:

```mermaid
graph TD
A[(Database)]
```

## shape_diamond_lr_chain

Source:

```
graph LR
    S{OK} --> M{Decide}
    M --> L{Continue?}
```

Rendered:

```mermaid
graph LR
    S{OK} --> M{Decide}
    M --> L{Continue?}
```

## shape_diamond

Source:

```
graph TD
A{Decision}
```

Rendered:

```mermaid
graph TD
A{Decision}
```

## shape_parallelogram_alt

Source:

```
graph TD
A[\Alt Para\]
```

Rendered:

```mermaid
graph TD
A[\Alt Para\]
```

## shape_parallelogram_lr_chain

Source:

```
graph LR
    A[/Parallelogram/] --> B[\Alt Para\]
```

Rendered:

```mermaid
graph LR
    A[/Parallelogram/] --> B[\Alt Para\]
```

## shape_parallelogram_multiline

Source:

```
graph LR
    A[/Line one<br>Line two/] --> B[\Row one<br>Row two\]
```

Rendered:

```mermaid
graph LR
    A[/Line one<br>Line two/] --> B[\Row one<br>Row two\]
```

## shape_parallelogram_td_chain

Source:

```
graph TD
    A[/Input/] --> B[/Output/]
```

Rendered:

```mermaid
graph TD
    A[/Input/] --> B[/Output/]
```

## shape_parallelogram

Source:

```
graph TD
A[/Parallelogram/]
```

Rendered:

```mermaid
graph TD
A[/Parallelogram/]
```

## shape_round

Source:

```
graph TD
A(Round)
```

Rendered:

```mermaid
graph TD
A(Round)
```

## shape_stadium

Source:

```
graph TD
A([Stadium])
```

Rendered:

```mermaid
graph TD
A([Stadium])
```

## shape_subroutine

Source:

```
graph TD
A[[Subroutine]]
```

Rendered:

```mermaid
graph TD
A[[Subroutine]]
```

## shapes_fallback

Source:

```
graph TD
  A[Start] --> B{Decide}
  B -->|yes| C[Do it]
  B -->|no| D[Skip]
```

Rendered:

```mermaid
graph TD
  A[Start] --> B{Decide}
  B -->|yes| C[Do it]
  B -->|no| D[Skip]
```

## subgraph_backward_edge_lr

Source:

```
graph LR
    subgraph Frontend
        UI[UI] --> API[API Client]
    end
    subgraph Backend
        Server[Server] --> DB[(Database)]
    end
    API --> Server
    DB --> Server
```

Rendered:

```mermaid
graph LR
    subgraph Frontend
        UI[UI] --> API[API Client]
    end
    subgraph Backend
        Server[Server] --> DB[(Database)]
    end
    API --> Server
    DB --> Server
```

## subgraph_backward_edge_td

Source:

```
graph TD
    subgraph Top
        A[A] --> B[B]
    end
    subgraph Bottom
        D[D] --> C[C]
    end
    B --> D
    C --> D
```

Rendered:

```mermaid
graph TD
    subgraph Top
        A[A] --> B[B]
    end
    subgraph Bottom
        D[D] --> C[C]
    end
    B --> D
    C --> D
```

## subgraph_nested

Source:

```
graph TD
  subgraph outer
    A --> B
    subgraph inner
      B --> C
    end
  end
  A --> D
```

Rendered:

```mermaid
graph TD
  subgraph outer
    A --> B
    subgraph inner
      B --> C
    end
  end
  A --> D
```

## subgraph_simple

Source:

```
graph TD
  A --> B
  subgraph one
    B --> C
  end
  subgraph two
    C --> D
  end
```

Rendered:

```mermaid
graph TD
  A --> B
  subgraph one
    B --> C
  end
  subgraph two
    C --> D
  end
```


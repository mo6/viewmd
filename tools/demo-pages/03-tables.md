## Tables

| Feature          | Status      | Notes                                   | Value |
|------------------|:-----------:|------------------------------------------|------:|
| Headers          | done        | all six levels                            | &euro;&nbsp;2,95 |
| Tables           | done        | this one, with alignment                  | &euro;&nbsp;1,50 |
| Front matter     | done        | rendered as a table, see the intro page   | &euro;&nbsp;12,50 |
| Wikilinks        | done        | see the formatting page                   | &euro;&nbsp;250,00 |
| Mermaid diagrams | done        | sequence, flowchart, ER, pie, packet, quadrant | &euro;&nbsp;1.395,00 |

## Syntax-highlighted code

```python
def render(text: str, *, width: int, color: bool) -> str:
    """Render Markdown to an ANSI string, width columns wide."""
    return _console_render(text, width=width, color=color)
```

### A line too wide for the render width

An ordinary code line longer than the render width stays intact on one line rather than folding
onto a second (VIEWMD-0019) -- same as a mermaid diagram (VIEWMD-0018). The line below is exactly
120 characters; at the default 100-column cap it should still render as a single unbroken line,
scrolling horizontally in the pager (`less -S`) instead of wrapping or being cut off:

```python
result = some_function(argument_one, argument_two, argument_three, argument_four, argument_five, argument_six, xxxxxxxx)
```

"""Split and parse a leading YAML-style front-matter block (`--- ... ---`).

Not a full YAML parser: flat and indented `key: value` mappings, `[a, b, c]`-style bracketed
lists, block-list (`- item`) arrays (including arrays of `- field: value` objects), and `|`/`>`
block scalars. This mirrors tools/issues.py's own front-matter parser in spirit rather than
adding a YAML dependency for a narrow, known input shape (docs/PLAN.md). Anchors/aliases, flow
mappings (`{a: b}`), and multi-document streams are out of scope (VIEWMD-0012 Non-goals).
"""


def split_front_matter(text: str) -> tuple[str | None, str]:
    """Split `text` into (raw front-matter block, body).

    Returns (None, text) unchanged when the file doesn't open with a `---` line, or opens with
    one but never closes it with a matching `---` line (an unterminated block is not front
    matter, VIEWMD-0004 requirement 6).
    """
    lines = text.splitlines(keepends=True)
    if not lines or lines[0].rstrip("\n") != "---":
        return None, text
    for i in range(1, len(lines)):
        if lines[i].rstrip("\n") == "---":
            raw = "".join(lines[1:i])
            body = "".join(lines[i + 1:])
            return raw, body
    return None, text


def _indent(line: str) -> int:
    return len(line) - len(line.lstrip(" "))


def _strip_quotes(value: str) -> str:
    return value.strip().strip("'\"")


Node = str | list | dict


def _parse_mapping(lines: list[str], idx: int, indent: int) -> tuple[dict[str, Node], int]:
    result: dict[str, Node] = {}
    while (
        idx < len(lines)
        and _indent(lines[idx]) == indent
        and not lines[idx].strip().startswith("- ")
    ):
        key, sep, value = lines[idx].strip().partition(":")
        idx += 1
        if not sep:
            continue
        key = key.strip()
        value = value.strip()
        if value in ("|", ">"):
            content: list[str] = []
            while idx < len(lines) and _indent(lines[idx]) > indent:
                content.append(lines[idx].strip())
                idx += 1
            result[key] = ("\n" if value == "|" else " ").join(content)
        elif value.startswith("[") and value.endswith("]"):
            inner = value[1:-1].strip()
            result[key] = [v.strip().strip("'\"") for v in inner.split(",") if v.strip()]
        elif value:
            result[key] = _strip_quotes(value)
        elif idx < len(lines) and _indent(lines[idx]) > indent:
            child_indent = _indent(lines[idx])
            if lines[idx].strip().startswith("- "):
                result[key], idx = _parse_list(lines, idx, child_indent)
            else:
                result[key], idx = _parse_mapping(lines, idx, child_indent)
        else:
            result[key] = ""
    return result, idx


def _parse_list(lines: list[str], idx: int, indent: int) -> tuple[list[Node], int]:
    items: list[Node] = []
    while (
        idx < len(lines)
        and _indent(lines[idx]) == indent
        and lines[idx].strip().startswith("- ")
    ):
        item_text = lines[idx].strip()[2:].strip()
        idx += 1
        key, sep, value = item_text.partition(":")
        if not sep:
            items.append(_strip_quotes(item_text))
            continue
        obj: dict[str, Node] = {}
        value = value.strip()
        if value:
            obj[key.strip()] = _strip_quotes(value)
        while (
            idx < len(lines)
            and _indent(lines[idx]) > indent
            and not lines[idx].strip().startswith("- ")
        ):
            sub_key, sub_sep, sub_value = lines[idx].strip().partition(":")
            if sub_sep and sub_value.strip():
                obj[sub_key.strip()] = _strip_quotes(sub_value)
            idx += 1
        items.append(obj)
    return items, idx


def _flatten(node: Node, prefix: str, out: dict[str, str]) -> None:
    if isinstance(node, dict):
        for key, child in node.items():
            _flatten(child, f"{prefix}.{key}" if prefix else key, out)
    elif isinstance(node, list):
        if all(isinstance(item, str) for item in node):
            out[prefix] = ", ".join(node)
        else:
            parts = [
                ", ".join(f"{k}: {v}" for k, v in item.items())
                if isinstance(item, dict)
                else str(item)
                for item in node
            ]
            out[prefix] = "; ".join(parts)
    else:
        out[prefix] = node


def parse_front_matter(raw: str) -> dict[str, str]:
    """Parse a front-matter block into a dict of display-ready strings.

    Nested mappings flatten to dotted keys (`seo: {title: ...}` becomes `seo.title`) so a nested
    key can never collide with an unrelated top-level key of the same name. Lists of scalars
    render comma-joined, matching the `[a, b, c]` bracket form; lists of `- field: value` objects
    render as `; `-separated, comma-joined items so every item's data stays visible.
    """
    lines = [line for line in raw.splitlines() if line.strip() and not line.strip().startswith("#")]
    if not lines:
        return {}
    tree, _ = _parse_mapping(lines, 0, _indent(lines[0]))
    data: dict[str, str] = {}
    _flatten(tree, "", data)
    return data


def drop_empty(data: dict[str, str]) -> dict[str, str]:
    """Front-matter fields whose value is empty (or all whitespace) carry no information for the
    table (VIEWMD-0005); --full-front-matter bypasses this to see every parsed field."""
    return {key: value for key, value in data.items() if value.strip()}

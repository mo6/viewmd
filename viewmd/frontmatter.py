"""Split and parse a leading YAML-style front-matter block (`--- ... ---`).

Not a full YAML parser: flat `key: value` pairs, one per line, plus `[a, b, c]`-style bracketed
lists rendered as a comma-joined string. This mirrors tools/issues.py's own front-matter parser
rather than adding a YAML dependency for a narrow, known input shape (docs/PLAN.md).
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


def parse_front_matter(raw: str) -> dict[str, str]:
    """Parse a flat `key: value` block into a dict of display-ready strings."""
    data: dict[str, str] = {}
    for line in raw.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or ":" not in line:
            continue
        key, _, value = line.partition(":")
        key = key.strip()
        value = value.strip()
        if value.startswith("[") and value.endswith("]"):
            inner = value[1:-1].strip()
            items = [v.strip().strip("'\"") for v in inner.split(",") if v.strip()]
            value = ", ".join(items)
        else:
            value = value.strip("'\"")
        if key:
            data[key] = value
    return data

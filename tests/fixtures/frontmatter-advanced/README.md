Manual test documents for VIEWMD-0011.

Each file below isolates one "advanced" front-matter feature from the reference at <https://www.markdownlang.com/advanced/frontmatter.html#advanced-frontmatter-features>. Render each with `./viewmd.sh <file>` (and again with `--full-front-matter`) and compare what actually appears in the front-matter table against what the file's front matter intends, per `viewmd/frontmatter.py`'s documented flat `key: value` / single-level `[a, b, c]` shape.

- `01-nested-objects.md` — a mapping value nested under a key (`seo:` with indented sub-keys).
- `02-array-of-objects.md` — a YAML list of mappings (`authors:` with `- name: ... / email: ...` items).
- `03-dash-list-arrays.md` — a plain YAML list using the `-` item form, as opposed to this project's already-supported `[a, b, c]` bracket form.
- `04-multiline-strings.md` — a literal block scalar (`|`) and a folded block scalar (`>`).
- `05-date-formats.md` — ISO 8601 with time and timezone, a bare date, and a quoted date string.
- `06-boolean-values.md` — `true`/`false` and the YAML 1.1 `yes`/`no` boolean aliases.
- `07-toml-frontmatter.md` — TOML-delimited front matter (`+++ ... +++`) instead of YAML.
- `08-json-frontmatter.md` — JSON-object front matter fenced by `;;;`.
- `09-kitchen-sink.md` — a realistic blog-post-style front-matter block combining several of the above at once, closer to what the reference page's own examples look like end to end.

Expected outcome, given `viewmd/frontmatter.py`'s current Non-goals (VIEWMD-0004): most of these should NOT render as intended — nested/array-of-object values will show as raw, truncated, or malformed text in the table, and the TOML/JSON files should fall back to today's "no front matter detected" behavior (the block isn't `--- ... ---`-delimited YAML at all). That mismatch is exactly what VIEWMD-0011 is checking and recording.

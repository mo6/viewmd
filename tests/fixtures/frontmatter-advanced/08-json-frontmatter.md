;;;
{
  "title": "JSON front matter test",
  "published": true,
  "tags": ["markdown", "frontmatter", "json"]
}
;;;

# JSON front matter

This file uses JSON-object front matter fenced by `;;;` instead of the YAML `--- ... ---` form.
Check whether viewmd recognizes this block as front matter at all, or falls back to today's
documented behavior for anything that doesn't open with a `---` line: no table, no divider, and
the `;;; ... ;;;` block left as literal text at the top of the rendered body.

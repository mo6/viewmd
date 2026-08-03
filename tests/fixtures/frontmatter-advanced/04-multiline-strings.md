---
title: Multiline strings test
literal_block: |
  Line one, kept as-is.
  Line two, kept as-is.
  Blank lines and indentation are preserved.
folded_block: >
  This is a long description that
  gets folded onto a single line,
  with line breaks turned into spaces.
---

# Multiline strings

`literal_block` (`|`) should preserve its internal line breaks; `folded_block` (`>`) should
collapse its internal line breaks into spaces. Check whether the front-matter table shows either
value correctly, shows only the first line, or shows the raw block-scalar text (including the `|`
and `>` markers) unparsed.

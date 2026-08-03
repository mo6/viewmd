---
title: Dash-style list array test
tags:
  - javascript
  - react
  - frontmatter
tags_bracket_form: [javascript, react, frontmatter]
---

# Dash-style list arrays

`tags` uses YAML's block-list `-` item form (one item per line). `tags_bracket_form` is the same
data using this project's already-supported `[a, b, c]` bracket form (VIEWMD-0004 requirement 2),
included here for a side-by-side comparison. Check whether `tags` renders equivalently to
`tags_bracket_form`, renders as raw text, or is dropped/misparsed.

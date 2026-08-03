---
title: Boolean values test
published_true: true
published_false: false
featured_yes: yes
featured_no: no
---

# Boolean values

`true`/`false` are the standard YAML 1.2 booleans; `yes`/`no` are the YAML 1.1 boolean aliases
some frontmatter tooling still accepts. Check whether all four render as booleans (or as the
literal words `true`/`false`/`yes`/`no`, which would also be acceptable), and whether `yes`/`no`
are treated as booleans at all or left as plain strings.

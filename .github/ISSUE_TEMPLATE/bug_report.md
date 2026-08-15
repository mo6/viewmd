---
name: Bug report
about: Something in viewmd doesn't render or behave as expected
title: ""
labels: bug
assignees: ""
---

**Do not use this template for security vulnerabilities** — see [SECURITY.md](https://github.com/mo6/viewmd/blob/main/SECURITY.md) instead.

## Description

What's wrong, in a sentence or two.

## Steps to reproduce

The exact command you ran, plus the smallest `.md` input that reproduces it (paste it inline, or
attach the file):

```
./viewmd.sh repro.md
```

```markdown
<the minimal Markdown that triggers the bug>
```

## Expected vs. actual

What you expected to see, and what you saw instead. A screenshot or pasted terminal output helps a
lot for rendering bugs — copy/paste often loses color and box-drawing characters.

## Environment

- viewmd version (`viewmd --version`, or the commit/tag if running from source):
- OS and terminal emulator:
- `$PAGER`/`$TERM`, if relevant (e.g. `less -R -F -X`, `xterm-256color`):

## Anything else

Anything you already tried, or suspect is the cause.

---
*If this is accepted, a maintainer will turn it into a `VIEWMD-NNNN` issue under
[issues/](https://github.com/mo6/viewmd/blob/main/issues/README.md) before any code changes —
see [CONTRIBUTING.md](https://github.com/mo6/viewmd/blob/main/CONTRIBUTING.md).*

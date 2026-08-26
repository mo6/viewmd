---
name: documentation
description: Checks a finished viewmd issue's diff for user-facing documentation drift -- changes recorded only in CHANGELOG.md but not reflected in README.md or docs/example.md -- and makes those edits directly when needed. Invoke it from the sdlc-land-issue skill, after tests are green and before the peer-review step, so any doc edits it makes are included in what gets reviewed.
tools: Read, Grep, Glob, Edit, Bash(git diff:*), Bash(git log:*), Bash(git show:*), Bash(git status:*)
---

You are checking whether a finished change needs user-facing documentation, not just a
`CHANGELOG.md` entry. This project's history shows changes landing with only a changelog line and
no `README.md`/`docs/example.md` update, which leaves the docs describing an older version of the
tool than the code actually is.

You will be given: an issue file path under `issues/` and a branch or diff to check
(`git diff develop...HEAD` or as given).

Do this, in order:

1. Read the issue file in full — Summary, Requirements, Non-goals. Decide whether this change is
   user-facing at all (a new CLI flag, a new Mermaid diagram type, a new config key, a rendering
   behavior change someone would notice) versus purely internal (refactor, test-only change,
   tooling/process change, bug fix with no visible behavior change beyond "it now works"). Only
   internal changes get a pass with no doc edit.
2. Read the actual diff and changed files in full context, not just hunks.
3. Check `README.md`:
   - Does a new CLI flag, config key, or top-level feature need a line under the relevant section
     (`Usage`, `Configuration file`, `Shell completion`, `Mermaid diagrams`, etc.)?
   - Does a new Mermaid diagram type need its own `###` subsection under `## Mermaid diagrams`,
     following the existing entries' shape (one or two lines plus a fenced example or link)?
   - Does a behavior change make an existing README line inaccurate (a described default, flag
     behavior, or limitation that no longer holds)?
4. Check `docs/example.md`:
   - Existing sections are tagged with the issue that introduced them, e.g.
     `### Pie charts render two ways, chosen by color (VIEWMD-0043)`. A new renderable feature
     (diagram type, formatting construct, admonition variant) should get its own such section, with
     a real runnable example in a fenced code block, tagged with this issue's id.
   - A change to an existing feature's rendering should update its existing example section rather
     than adding a duplicate one.
5. If either file needs an edit, make it directly with `Edit` — match the surrounding style and
   heading structure exactly rather than inventing a new convention. Keep additions proportionate:
   a one-line CLI flag mention does not need a worked example; a new diagram type does.
6. If you are not sure whether a change is user-facing enough to warrant a doc update, err toward
   flagging it in your report rather than silently skipping it — the maintainer can decide.

**Do not touch `CHANGELOG.md`, `pyproject.toml`, or `viewmd/__init__.py`** — those are the
`sdlc-land-issue` skill's own archive-commit step, not this agent's job. Do not run `./run-tests.sh`
or make any commit yourself.

End with a short report: which file(s) you edited and why, or "no documentation changes needed"
with a one-line reason if the change was purely internal.

## Issue

Link the `VIEWMD-NNNN` issue this implements: <!-- e.g. issues/VIEWMD-0123-....md -->

<!--
Every change needs an accepted issue first (Definition of Ready) — see
CONTRIBUTING.md and issues/AGILE.md. If you don't have one yet, open it
(status: proposed, using issues/TEMPLATE.md) and get maintainer acceptance
before writing code.
-->

## What changed and why

<!-- One or two sentences. The issue has the full "what" — this is the "why now"/approach. -->

## Testing

- [ ] `./run-tests.sh` passes locally (pytest, ruff incl. security rules, `pip-audit`, `issues --check`)
- [ ] Added/updated fixtures or tests covering this change
- [ ] Ran the change against a real `.md` file, not just the test suite, if it touches rendering

## Peer review

<!--
Landing a change requires an independent review (a different agent or a
human — the implementer's own review doesn't count) recorded in the issue's
own "Peer review" section before it's asked to land. Has that happened?
-->

## Checklist

- [ ] Branch is `bug|feature|story/VIEWMD-NNNN`, cut from `develop`, targeting `develop` (never `main`)
- [ ] The issue's "Peer review" section is filled in
- [ ] `CHANGELOG.md`/version bump are **not** included — the maintainer handles that when archiving the issue

---
id: VIEWMD-0069
title: Publish viewmd to PyPI (deferred until the CLI surface stabilizes)
status: proposed
area: [tools]
effort: low
created: 2026-08-16
updated: 2026-08-16
accepted_by:
accepted_at:
commits: []
related: []
supersedes: []
changelog:
reason:
---

# Publish viewmd to PyPI (deferred until the CLI surface stabilizes)

## Summary

Record the maintainer's decision to *not* publish viewmd to PyPI for now, and why -- so the question doesn't get silently re-raised or, conversely, silently acted on by a future session without the context behind holding off. `pip install viewmd` (or an automated `pip-audit`-style dependency check actually finding it on PyPI, instead of always skipping it as unpublished) are real, concrete benefits a publish would unlock; they're just not worth taking on yet.

## Motivation / problem

Discussed with the maintainer (2026-08-16): publishing gives `pip install viewmd` instead of clone-plus-editable-install, lets `pip-audit` (and other supply-chain tooling) check viewmd against a real vulnerability database instead of always landing in its "skip, not found on PyPI" list (see the local dev-environment question this came out of), and gives a stable version pin if viewmd were ever depended on by something else. Against that: publishing makes every version bump an externally-visible, effectively permanent release (PyPI has no real unpublish), invites name-squatting/typosquatting concerns once the name is claimed, and requires setting up a PyPI account/2FA/trusted-publisher flow that doesn't exist yet. `AGENTS.md`'s own status line -- "actively developed, no stability guarantee yet" -- is the deciding factor: the CLI surface (flags, config file format, `$PAGER` defaults, exit codes) is still moving release to release (a new flag or config key most weeks per `CHANGELOG.md`), and publishing early just means more of that ordinary early-development churn becomes a breaking change for real external users instead of an internal detail. (The version number itself, `1.29.0`, is not the signal here -- this project bumps its minor version per ordinary feature per `AGENTS.md`'s own versioning rule, not as a semver maturity milestone, so it long ago passed "1.0" without that ever meaning "stable, safe to publish.")

## Non-goals

- Actually publishing to PyPI, doing any PyPI account/trusted-publisher setup, or adding a publish step to any workflow -- explicitly not happening as part of this issue; this issue's entire content *is* the decision to wait.
- Picking a specific version or milestone (e.g. "at 1.0.0") as the trigger to revisit -- not decided; see Design notes for the general criterion instead of a specific number.
- Any change to how viewmd is installed/developed today (`python3 -m venv .venv && .venv/bin/pip install -e '.[dev]'`, per `README.md`) -- unaffected either way.

## Design notes / links

No code or process changes -- this issue exists purely as a recorded decision, the same pattern [VIEWMD-0007](VIEWMD-0007-link-navigation.md) used to file a large idea without building it yet (`status: proposed`, requirements deliberately left unwritten). Revisit once the CLI surface (flags, config file format, defaults) has held steady across a few consecutive releases rather than changing almost every version bump, per `CHANGELOG.md`'s own history -- that's the general signal AGENTS.md's "no stability guarantee yet" is actually over, not a specific version number chosen in advance. When it is revisited, scope it as a real issue with actual requirements (packaging metadata review, PyPI account/trusted-publisher setup, a `tools/*` or CI publish step, `CHANGELOG.md`/`README.md` install-instruction updates) -- this issue is not that scoping pass.

## Acceptance / verification

Not applicable -- this issue records a decision, not a change to `viewmd` itself. Nothing for `./run-tests.sh` to verify.

## Peer review

Not applicable; not yet built (and not expected to be, per this issue's own content).

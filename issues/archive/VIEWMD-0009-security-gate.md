---
id: VIEWMD-0009
title: Add docs/SECURITY.md and a pip-audit gate in run-tests.sh
status: implemented
area: [tools, docs]
effort: low
created: 2026-08-02
updated: 2026-08-02
accepted_by: George Moses
accepted_at: 2026-08-02
commits: [19657ab]
related: []
supersedes: []
changelog: "[1.1.0]"
reason:
---

# Add docs/SECURITY.md and a pip-audit gate in run-tests.sh

## Summary

Add `docs/SECURITY.md`: a maintainer-facing runbook for viewmd's own security gate, scoped to
its actual (small) attack surface, plus a `pip-audit` step in `./run-tests.sh` so known-CVE
dependencies fail the gate. Ruff's Bandit-compatible `S` rules are already selected in
`pyproject.toml` (`select = [..., "S"]`) and already run in `run-tests.sh`'s `ruff` step; this
issue documents that existing coverage in `SECURITY.md` and adds the missing half (`pip-audit`),
rather than re-adding what already runs.

## Motivation / problem

Requested by the maintainer: viewmd should have a documented security gate -- a
`docs/SECURITY.md` runbook plus `pip-audit` in `run-tests.sh` -- scoped to viewmd's own surface:
it has no network access, no database, no plugin/content-execution system; its actual surface is
a `subprocess` call to `$PAGER` and reading files from disk.

## Requirements

1. MUST add `docs/SECURITY.md` covering: purpose (what the gate catches and doesn't), viewmd's
   own attack surface table (the `$PAGER` subprocess in `viewmd/pager.py`, file/stdin reading in
   `viewmd/__main__.py` -- both, and nothing else meaningfully privileged, since viewmd has no
   network access and no code execution from parsed Markdown), the tools in the gate (`ruff`'s
   `S` rules, `pip-audit`), the findings lifecycle (fix first, suppress only if accepted and
   documented), the standing-exceptions table (mirroring the `per-file-ignores` reasons already
   in `pyproject.toml`), what green does not mean, and cadence.
2. MUST add `pip-audit>=2.7` to the `dev` extra in `pyproject.toml`.
3. MUST add a `pip-audit` step to `run-tests.sh`'s full-gate path (not the fast pytest-forwarding
   path), running every step even if an earlier one failed, matching the script's existing
   pattern.
4. MUST fail the gate (non-zero exit) when `pip-audit` finds an advisory or cannot reach its
   advisory data -- no silent "offline means clean" path.
5. SHOULD keep `docs/SECURITY.md` in the loop `AGENTS.md` already establishes: reference it from
   `AGENTS.md` or `README.md`'s development section so it isn't an orphaned doc.

## Non-goals

- Secrets scanning, hosted CI, or a lock file. Deferred; revisit only against a real need (a
  remote CI runner, a real secret surface).
- Any change to what ruff's `S` rules actually check; that gate already runs today. This issue
  only documents it and adds `pip-audit` alongside it.

## Design notes / links

viewmd's attack surface is narrow by construction (docs/PLAN.md already states there's no
network access, no HTML/code execution from Markdown content); `SECURITY.md` should say that
plainly rather than pad out a table to look bigger than it is.

## Acceptance / verification

- `./run-tests.sh` green, including a new `== pip-audit ==` step in its output.
- Manual: `.venv/bin/python -m pip_audit --progress-spinner off` runs standalone and matches the
  gate's step.
- `docs/SECURITY.md` exists and is linked from `AGENTS.md` or `README.md`.

## Peer review

- **Claude (Sonnet 5)** (agent), 2026-08-02: PASS. `./run-tests.sh` green (54 tests, ruff clean,
  new `pip-audit` step clean, issues index current). `pip-audit`/`ruff` also verified standalone,
  matching the gate's own commands. `docs/SECURITY.md` added and linked from both `AGENTS.md` and
  `README.md`'s Development section, scoped to viewmd's real surface (the `$PAGER` subprocess and
  file/stdin reading) rather than copied wholesale from a larger project.

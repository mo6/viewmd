---
id: VIEWMD-0108
title: Formalize the SDLC as Claude Code skills/agent plus real CI/CD gates
status: in-progress
area: [tools, docs, ci]
effort: high
created: 2026-08-26
updated: 2026-08-26
accepted_by: George Moses <gmo6nl@gmail.com>
accepted_at: 2026-08-26
commits: []
related: []
supersedes: []
changelog:
reason:
---

# Formalize the SDLC as Claude Code skills/agent plus real CI/CD gates

## Summary

viewmd's development process (issue lifecycle, Definition of Ready/Done, worktree-per-issue, the two-commit landing pattern) is fully specified in `AGENTS.md`/`issues/AGILE.md` but lives entirely as prose, enforced only by an agent choosing to follow it. This adds Claude Code skills that encode the procedural steps, an independent subagent for the Definition of Done's reviewing pass, and two technical backstops that don't depend on agent diligence: a GitHub Actions CI workflow and a local pre-push git hook, both driven by the existing `./run-tests.sh` gate.

## Motivation / problem

Nothing today technically stops an agent from merging to `develop` without asking, skipping `./run-tests.sh`, or writing the Definition of Done's "independent reviewing agent" line from the same session that implemented the change — these are all currently just MUSTs in `AGENTS.md`/`issues/AGILE.md` that an agent must recall and self-apply every session. There is also no CI at all: a broken push to `develop`/`main` is only caught if `./run-tests.sh` happened to be run locally first.

## Requirements

1. MUST add `.claude/skills/new-issue/SKILL.md`: scaffolds a new issue from `issues/TEMPLATE.md` using `./tools.sh issues --check` for the next id, then explicitly asks the maintainer to accept it (Definition of Ready) before setting `accepted_by`/`accepted_at` and moving `status` to `in-progress` — never inferring acceptance from silence.
2. MUST add `.claude/skills/start-issue/SKILL.md`: verifies an issue's DoR fields are present, then runs `./tools.sh worktree add VIEWMD-NNNN <bug|feature|story>`.
3. MUST add `.claude/skills/land-issue/SKILL.md`: runs `./run-tests.sh`, verifies the issue's Peer review section has both required lines (independent agent pass, then maintainer sign-off), asks "commit and close this out?", and performs the two-commit landing pattern (`--no-ff` merge into `develop`, then a separate archive+bump commit) per `AGENTS.md`.
4. MUST add `.claude/skills/release/SKILL.md`: the `main`-merge/tag/`CHANGELOG.md`/`gh release create` flow from `AGENTS.md`'s release section, as its own explicit step never bundled into `land-issue`.
5. MUST add `.claude/agents/peer-reviewer.md`: a fresh (non-fork) subagent definition with read-only tools only (`Read`, `Grep`, `Glob`, and `Bash` limited to read-only/check commands such as `git diff`, `git log`, `./run-tests.sh`) — no `Edit`/`Write` — so its Definition of Done review is technically independent of whichever session implemented the change, not just self-attested.
6. MUST add `.github/workflows/ci.yml`: runs on `push`/`pull_request` to `develop` and `main`; sets up Python (3.10 and one later version), installs `.[dev]`, and runs `./run-tests.sh` verbatim (no reimplementation of its steps in YAML).
7. MUST add `tools/hooks/pre-push` (execs `./run-tests.sh`, blocks the push on failure) and `tools/install_hooks.sh` (sets `core.hooksPath` for the current worktree), runnable as `./tools.sh install_hooks`.
8. MUST wire hook installation into `tools/worktree.sh`'s existing per-worktree bootstrap, so every new worktree gets it automatically, the same way `.venv` already is.
9. MUST add a short pointer paragraph in `AGENTS.md` to the new skills/agent/CI, without duplicating detail that now lives in those files.
10. MUST NOT change any of the underlying policy (DoR/DoD criteria, branch model, landing pattern) — this only encodes the existing rules, it doesn't alter them.

## Non-goals

- No change to the DoR/DoD criteria themselves.
- No new agents/skills beyond the four lifecycle skills and the one reviewer subagent.
- No CI beyond the single `run-tests.sh`-driven workflow (no separate lint-only/test-only jobs).

## Design notes / links

Full design and rationale: this session's plan (issue lifecycle skills wrap existing `tools.sh` commands plus the conversational gates already mandated by `issues/AGILE.md`; the reviewer subagent's independence comes from being a fresh, non-forked agent invocation, not from any new policy).

## Acceptance / verification

- `./run-tests.sh` stays green throughout.
- Exercise `new-issue` → `start-issue` → (trivial change) → `land-issue` end to end on a throwaway test issue in a scratch worktree; confirm the DoR/DoD questions are actually asked and the two-commit pattern lands correctly.
- Manually invoke the `peer-reviewer` agent on a real diff; confirm it has no `Edit`/`Write` tools and its verdict references the issue's actual requirements.
- Push a deliberately failing branch to confirm the pre-push hook blocks it; push a passing one to confirm it doesn't.
- Push to a scratch branch with a `pull_request` targeting `develop` to confirm `ci.yml` runs and reports status.

## Peer review


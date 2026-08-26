# Contributing

viewmd is a personal project maintained by a single person (actively developed, no stability
guarantee yet), but contributions are welcome. This file is the short version;
[AGENTS.md](AGENTS.md) is the authoritative process doc — read it before opening a PR.

## Before you write code

**Every change gets an issue first.** Check the next free id with `./tools.sh issues --check`,
write a `VIEWMD-NNNN` file in [issues/](issues/README.md) (`status: proposed`, using
[issues/TEMPLATE.md](issues/TEMPLATE.md)) stating *what* the change must do, then ask the
maintainer to accept it before implementing. The only exception is a change that's itself only
about an issue file (fixing a typo, regenerating the index).

## Submitting a change

If you don't have push access to this repo (most external contributors), fork it on GitHub, cut
your branch from `develop` in your fork using the naming convention below, and open a pull
request against this repo's `develop` branch once your change is ready. `main` is releases only —
never target it.

## Setting up

The maintainer (and any agent working directly in this repo) implements each issue in its own git
worktree, not the primary checkout:

```sh
./tools.sh worktree add VIEWMD-NNNN [bug|feature|story]
```

This creates `../viewmd-VIEWMD-NNNN` on a correctly-named branch cut from `develop`, with its own
`.venv` bootstrapped (`pip install -e '.[dev]'`). If you're working from a fork, this step doesn't
apply — just branch normally within your fork.

## Making the change

- Branch naming: `bug/VIEWMD-NNNN`, `feature/VIEWMD-NNNN`, or `story/VIEWMD-NNNN`.
- `./run-tests.sh` is the full gate (`pytest`, `ruff` incl. security rules, `pip-audit`,
  `issues --check`) — run it bare before considering any change done.
- Markdown paragraphs are single lines, not hard-wrapped — let the reader's editor wrap them.
- Invoke maintainer tooling via `./tools.sh <tool> [args...]`, never a script under `tools/`
  directly.

## Working with agents

Contributions written or assisted by an AI coding agent are welcome. If you use one, point it at
[AGENTS.md](AGENTS.md) and follow it — it's binding for any agent touching this repo, not just
optional guidance. Two things it's worth being explicit about here:

- A review from the same agent that implemented the change is a work summary, not a review — it
  doesn't satisfy the peer-review requirement below. Get an independent pass (a different agent,
  or a human) before asking for the change to land.
- The human maintainer is always the final gate. However much of the implementation and review
  was agent-assisted, landing a change still requires the maintainer's explicit go-ahead, not an
  agent's own initiative.

## Hooks, gates, skills, and agents

The process above is enforced automatically at several layers, not just by reading this file.

- **Gates.** `./run-tests.sh` is the whole dev gate — `pytest`, `ruff check` (including the `S`-prefixed security rules, per [docs/SECURITY.md](docs/SECURITY.md)), `pip-audit`, and `./tools.sh issues --check`. Two backstops run it whether or not you remember to: `.github/workflows/ci.yml` runs it on every push/PR to `develop`/`main` (Python 3.10 and 3.12), and a pre-push git hook (`tools/hooks/pre-push`) runs it before any push leaves the machine, blocking the push if it fails (`git push --no-verify` bypasses it, but don't). The hook is wired in automatically by `./tools.sh worktree add`, or manually via `./tools.sh install_hooks`.
- **Skills** (`.claude/skills/`, Claude Code only). `sdlc-new-issue`, `sdlc-start-issue`, `sdlc-land-issue`, and `sdlc-release` each walk one stage of the issue lifecycle described above (draft and get accepted, set up a worktree, land through the Definition of Done, cut a release) and ask the maintainer the same gate questions this file and AGENTS.md describe, rather than leaving an agent to infer when to stop and ask.
- **Agents** (`.claude/agents/`, launched by `sdlc-land-issue`). `documentation` checks whether `README.md` or `docs/example.md` need updating for a user-facing change (not just `CHANGELOG.md`) and edits them directly if so. `peer-reviewer` performs the Definition of Done's independent review — always a fresh agent, never a fork of the implementing session, with no `Edit`/`Write` tools, so its pass can't be the implementer grading its own work.

None of this replaces the maintainer's own sign-off — see "Working with agents" above.

## Landing the change

Once implemented, tests are green, and the change has been peer-reviewed, show the diff to the
maintainer and ask outright to land it — don't merge or archive the issue on your own initiative.
Landing an issue is `--no-ff` merge into `develop` plus a separate "archive and bump version"
commit; see AGENTS.md for the full Definition of Ready/Done ([issues/AGILE.md](issues/AGILE.md)).

## Architecture and dependencies

- Package layout and module responsibilities: the opening paragraph of [AGENTS.md](AGENTS.md).
- Design rationale (the *why* behind the rendering/paging approach): [docs/PLAN.md](docs/PLAN.md).
- Runtime and dev dependencies, and code style (`ruff` line length and rule set): all pinned in
  [pyproject.toml](pyproject.toml) and enforced by `./run-tests.sh` — there's no separate style
  guide to read, just run the gate.

## Reporting bugs and security issues

Open a GitHub issue for ordinary bugs. For security vulnerabilities, follow
[SECURITY.md](SECURITY.md) instead — do not open a public issue.

## Code of conduct

Participation in this project is governed by [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md).

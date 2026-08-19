---
id: VIEWMD-0087
title: Provide bash/zsh/fish shell completion for viewmd's CLI flags
status: implemented
area: [cli, tools]
effort: medium
created: 2026-08-19
updated: 2026-08-19
accepted_by: George Moses <gmo6nl@gmail.com>
accepted_at: 2026-08-19
commits: [346ffab]
related: []
supersedes: []
changelog: "[1.46.0]"
reason:
---

# Provide bash/zsh/fish shell completion for viewmd's CLI flags

## Summary

Generate and ship shell completion scripts (bash, zsh, fish) for viewmd's argparse-defined flags (`--no-pager`, `--color`, `--width`, `--full-front-matter`/`--no-full-front-matter`, `--toc`/`--no-toc`, `--config`, `--version`), so tab-completion works for the flag surface without hand-maintained duplicate lists.

## Motivation / problem

viewmd has a reasonably wide flag surface for a single-command CLI, several of them `BooleanOptionalAction` pairs a user has to remember the negated spelling of (`--no-toc`, `--no-full-front-matter`). Shell completion is a small addition that removes the need to consult `--help` for exact flag names/values (e.g. remembering `--color` takes `auto`/`always`/`never`).

## Requirements

1. MUST generate completions for bash, zsh, and fish from the single `argparse.ArgumentParser` already defined in `viewmd/__main__.py`, rather than a hand-written, separately-maintained list of flags per shell (avoids drift when a flag is added/renamed).
2. MUST complete `--color`'s three literal choices and `--width`'s `full` literal.
3. MUST complete path arguments as filesystem paths (delegate to the shell's normal file completion), restricted to no extension filter (any file/dir is a valid `path` argument, including `-`).
4. MUST document install steps for each shell in `README.md` (where to source/symlink the generated script).
5. SHOULD be regenerable via a `./tools.sh` entry (e.g. `./tools.sh completions`) rather than a manually-edited static file, so `run-tests.sh` (or a dedicated check) can assert the checked-in scripts match what the current parser would generate.

## Non-goals

- No dynamic/runtime completion of Markdown-file *contents* (headings, wikilink targets) — path/flag completion only.
- No PowerShell completion (out of scope unless requested later).

## Design notes / links

`argcomplete` (bash/zsh, standard for argparse-based tools) is the natural fit for requirement 1; fish completion can be hand-generated once from the same parser at build time. Confirm dependency choice (new runtime dep vs. dev-only generation script) during implementation planning, since `AGENTS.md` lists viewmd's only runtime deps as `rich`/`wcwidth` today.

## Acceptance / verification

Generated scripts checked into the repo (e.g. `completions/viewmd.bash`, `.zsh`, `.fish`); a test or `./tools.sh` check confirms the checked-in scripts are current for the present flag set. Manual verification: sourcing each script in its shell and confirming `viewmd --col<TAB>` and `viewmd --width <TAB>` behave as expected.

## Peer review

- (agent, implementer) Implemented `tools/completions.py` (generates `completions/viewmd.{bash,zsh,fish}` by introspecting `viewmd.__main__.build_parser()`, no new runtime dependency), wired `./tools.sh completions` and a `--check` mode into `./run-tests.sh`, and documented per-shell install steps in `README.md`. `./run-tests.sh` is green for everything this issue touches; it currently fails only on a pre-existing, unrelated `issues --check` gap (VIEWMD-0083/VIEWMD-0086 missing `effort:`, present before this branch's changes, confirmed via `git stash`) that this issue does not own. This is an implementation summary, not an independent review (AGENTS.md) — a separate reviewing pass is still needed before "commit and close this out?" is asked.
- (agent, independent reviewer) Reviewed `tools/completions.py`'s parser-introspection logic against all requirements: flags are read from `build_parser()._actions` directly (no hand-maintained duplicate list, requirement 1); `--color`'s three choices come from `action.choices`, `--width`'s `full` is hardcoded since `_width_arg`'s type function has no `choices` argparse can read (requirement 2); `--config` and the positional path fall back to filesystem-path completion with no extension filter in all three shells (requirement 3, verified in `render_bash`/`render_zsh`/`render_fish`); README documents install steps for all three shells (requirement 4); `./tools.sh completions --check` is wired into `run-tests.sh`'s gate (requirement 5). Manually drove `completions/viewmd.bash` (sourced it, called `_viewmd_completions` with `COMP_WORDS=(viewmd --col)`/`(viewmd --color)` set) and confirmed `--col<TAB>` completes to `--color` and `--color <TAB>` offers `auto always never`, matching the issue's specified manual-verification steps. Merged into `develop` with one conflict, in the auto-generated `issues/README.md` index only (resolved by regenerating via `./tools.sh issues`, no manual content decisions); `./run-tests.sh` reconfirmed green post-merge (1136 passed, ruff, pip-audit, completions --check). Verdict: approve, no changes requested.
- (maintainer, George Moses) 2026-08-19: "accept and close issue 87" — explicit landing approval given in-conversation.


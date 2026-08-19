---
id: VIEWMD-0083
title: Warn on unrecognized config-file keys instead of silently ignoring them
status: in-progress
area: [config]
effort: low
created: 2026-08-19
updated: 2026-08-19
accepted_by: George Moses <gmo6nl@gmail.com>
accepted_at: 2026-08-19
commits: []
related: []
supersedes: []
changelog:
reason:
---

# Warn on unrecognized config-file keys instead of silently ignoring them

## Summary

`viewmd.config.parse_config` currently ignores any key it does not recognize, with no feedback to the user, so that a typo (`wdith = 80` instead of `width = 80`) silently does nothing rather than surfacing as a mistake.

## Motivation / problem

Unknown-key tolerance was chosen for forward compatibility (an older `viewmd` reading a config file written for a newer one with more keys), but it has the side effect of masking typos: nothing distinguishes "this key doesn't exist yet in this version" from "you misspelled a real key." A user who sets `wdith = 80` gets no width override and no explanation why.

## Requirements

1. MUST print a `viewmd: <path>:<line>: unrecognized config key <key>` warning to stderr for every key in the parsed file that is not one of the known keys (`width`, `color`, `full_front_matter`, `toc`).
2. MUST NOT treat an unrecognized key as fatal — parsing continues and the run proceeds exactly as it does today (forward compatibility with newer config files is preserved).
3. MUST NOT emit the warning more than once per unrecognized key per run.
4. SHOULD emit warnings in file order (ascending line number) alongside any other config diagnostics.

## Non-goals

- No "did you mean...?" fuzzy-match suggestion for the mistyped key name.
- No change to CLI-flag parsing (argparse already rejects unknown flags outright).

## Design notes / links

See `viewmd/config.py` `parse_config`'s trailing comment ("Unknown keys are ignored (forward-compatible with future options)") for the existing rationale this issue narrows, not reverses.

## Acceptance / verification

New test in `tests/test_config.py`: a config file with one known key and one misspelled key parses successfully (known key's value still applied) while emitting exactly one stderr warning naming the misspelled key and its line number. `./run-tests.sh` green.

## Peer review

- (agent, implementer) Implemented the stderr warning in `parse_config`, added `test_parse_config_warns_once_on_unrecognized_key`; `./run-tests.sh` passes pytest/ruff/pip-audit (pre-existing `issues --check` failures on VIEWMD-0086/0087, unrelated to this change, are untouched). This is a work summary from the implementer, not an independent review — an independent pass is still needed before "commit and close this out?".
- (agent, independent reviewer) Reviewed the diff against all 4 requirements: warning format/wording matches exactly, non-fatal (falls through an `else`, no exception), exactly-once-per-key is structurally guaranteed since the `raw` dict already rejects duplicate keys before the warning loop runs, and ascending line order holds because `raw` is built via one top-to-bottom pass over `text.splitlines()` with Python dict insertion order preserved. New test matches file style and asserts all three acceptance-criteria pieces. `./run-tests.sh` confirmed green (pytest 1128 passed, ruff, pip-audit); the only failures are pre-existing unrelated `issues --check` gaps on VIEWMD-0086/0087. One non-blocking style nit: the warning prints directly from `config.py` rather than being raised and printed in `__main__.py` like other `viewmd: ...` messages, a reasonable divergence since this warning must not be fatal. Verdict: approve.

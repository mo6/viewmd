---
id: VIEWMD-0083
title: Warn on unrecognized config-file keys instead of silently ignoring them
status: proposed
area: [config]
effort:
created: 2026-08-19
updated: 2026-08-19
accepted_by:
accepted_at:
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


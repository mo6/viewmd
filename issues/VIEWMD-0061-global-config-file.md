---
id: VIEWMD-0061
title: Support a user global configuration file for common options
status: in-progress
area: [cli]
effort: medium
created: 2026-08-16
updated: 2026-08-16
accepted_by: George Moses
accepted_at: 2026-08-16
commits: []
related: [VIEWMD-0007, VIEWMD-0062]
supersedes: []
changelog:
reason:
---

# Support a user global configuration file for common options

## Summary

Add a per-user configuration file that supplies default values for viewmd's CLI options --
`--width`, `--color`, `--full-front-matter`, and (once [VIEWMD-0062](VIEWMD-0062-table-of-contents.md)
lands) a `toc` on/off default -- so a reader who always wants, say, `--width 80` or the ToC
disabled doesn't have to pass that flag on every invocation. An explicit CLI flag always overrides
whatever the config file says; the config file only changes viewmd's *built-in* defaults.

## Motivation / problem

Every option viewmd has today (`--width`, `--color`, `--full-front-matter`) is CLI-only, reset to
its built-in default on every invocation. That's fine for one-off overrides but wrong for a
standing preference -- there's no way to say "I always want `--width 80`" without wrapping viewmd
in a shell alias/function per-user. This is also a direct prerequisite for
[VIEWMD-0007](VIEWMD-0007-link-navigation.md) (the Info-style interactive pager): that issue's own
research note flags that a from-scratch feature like default-on ToC generation (VIEWMD-0062)
needs a way to be toggled on by default without becoming a new permanent CLI flag every reader
must remember to pass -- a config file is the natural place for that, and is smaller, more
self-contained scope than VIEWMD-0007 itself, so it's filed and can land independently first.

## Requirements

1. MUST read a user-global config file at a well-known path, resolved via the XDG Base Directory
   spec: `$XDG_CONFIG_HOME/viewmd/config` if `XDG_CONFIG_HOME` is set (and non-empty), else
   `~/.config/viewmd/config`. The exact file extension/format (see requirement 2) is an
   implementation decision, but the directory/filename stem (`viewmd/config`) MUST follow this
   resolution rule.
2. MUST parse a flat key-value format -- e.g. `configparser`'s INI syntax (stdlib, no new
   dependency, but requires a `[section]` header even for a single flat set of keys) or a small
   hand-rolled `key = value` line format. TOML is deliberately not mandated: `tomllib` is
   stdlib only from Python 3.11 (`pyproject.toml`'s `requires-python = ">=3.10"`), so choosing
   TOML would mean adding a new runtime dependency (`tomli`) purely for this feature -- an
   implementation may still choose TOML with that added dependency, but the format itself is not
   dictated by this requirement.
3. MUST support at minimum these keys, each mirroring an existing CLI flag's value space: `width`
   (an integer column count, or the literal `full`, matching `--width`), `color` (`auto` |
   `always` | `never`, matching `--color`), `full_front_matter` (boolean, matching
   `--full-front-matter`). MUST be structured so a future key (e.g. `toc`, for VIEWMD-0062) can be
   added without changing this resolution mechanism.
4. MUST resolve each option's effective value in this precedence order, highest first: (1) an
   explicit CLI flag, (2) the config file's value for that key, (3) viewmd's existing built-in
   default (`DEFAULT_MAX_WIDTH`, `auto` color resolution, etc., per `viewmd/__main__.py` today).
   An option not mentioned in the config file falls through to (3) unchanged.
5. MUST treat a missing config file as "no overrides" -- not an error, not a warning; viewmd's
   current no-config behavior is exactly the "file absent" case of this feature.
6. MUST fail with a `viewmd: <message>` line to stderr and a non-zero exit (matching the existing
   error-handling convention in `viewmd/__main__.py`, never a raw traceback) if the config file
   exists but fails to parse, or contains a key with an invalid value for its type (e.g.
   `color = purple`) -- the same validation `_width_arg`/`--color`'s `choices=` already apply to
   the CLI flags MUST also apply to the config file's values for the same keys.
7. MUST support an explicit `--config PATH` CLI flag that reads the config from `PATH` instead of
   the resolved default location, and a `VIEWMD_NO_CONFIG` environment variable (any non-empty
   value) that skips reading a config file entirely -- both useful for reproducible test/CI
   invocations that must not pick up a developer's own `~/.config/viewmd/config`.
8. MUST NOT change any existing default's *value* -- with no config file present (the common case
   until a reader creates one), every option's effective default MUST be identical to viewmd's
   behavior today.

## Non-goals

- A project-local/per-directory config file (e.g. `.viewmdrc` in the current working directory or
  walked up from it) -- only the single user-global file is in scope; per-directory config, if
  ever wanted, is its own future issue.
- Any config key that does not already exist as a CLI flag at the time this issue is scoped for
  real, beyond the `toc` key VIEWMD-0062 will add -- this issue's job is the mechanism, not an
  exhaustive settings list.
- A `viewmd config` subcommand for editing/inspecting the file interactively -- plain text file,
  hand-edited.
- Live-reloading a running process's config -- irrelevant, viewmd is not long-running.
- Config file generation/scaffolding (e.g. `viewmd --init-config`) -- out of scope for v1.

## Design notes / links

`viewmd/__main__.py:main` is where every existing CLI default is resolved today (`_resolve_color`,
`_resolve_width`); this issue's precedence chain (requirement 4) slots in as an extra layer read
before those functions' own built-in fallback, not a replacement for them. Direct prerequisite for
[VIEWMD-0062](VIEWMD-0062-table-of-contents.md) (needs a `toc` config key to default the new
ToC-generation feature on/off) and, longer-term, for [VIEWMD-0007](VIEWMD-0007-link-navigation.md)
(an interactive pager mode likely wants its own standing preferences -- default keybinding set,
whether to auto-follow single-link nodes, etc. -- once that issue is actually scoped).

## Acceptance / verification

- `./run-tests.sh` green, including new `pytest` coverage for: config file absent (behavior
  unchanged, requirement 8), config file present overriding each of `width`/`color`/
  `full_front_matter` individually (requirement 3-4), a CLI flag overriding a config file value
  for the same key (requirement 4's precedence order), a malformed config file or an invalid
  value for a known key producing a `viewmd: ...` stderr message and non-zero exit rather than a
  traceback (requirement 6), `--config PATH` reading from an explicit alternate location
  (requirement 7), and `VIEWMD_NO_CONFIG` suppressing config-file reads entirely (requirement 7).
- Manual check: create `~/.config/viewmd/config` (or `$XDG_CONFIG_HOME/viewmd/config`) setting
  `width` to a non-default value, run `viewmd README.md --no-pager` with no `--width` flag, and
  confirm the output wraps at the configured width; then pass `--width full` on the same
  invocation and confirm the flag wins.

## Peer review

Not applicable; not yet built.

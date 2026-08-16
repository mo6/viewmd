---
id: VIEWMD-0067
title: Enable mouse/trackpad scroll-wheel support in the default less pager
status: proposed
area: [cli]
effort: low
created: 2026-08-16
updated: 2026-08-16
accepted_by:
accepted_at:
commits: []
related: [VIEWMD-0007]
supersedes: []
changelog:
reason:
---

# Enable mouse/trackpad scroll-wheel support in the default less pager

## Summary

Add `--mouse` to `viewmd/pager.py`'s default `less` invocation so a reader's mouse wheel or trackpad scroll gesture actually scrolls the paged output, the way it does in a bare `less somefile` today. Currently it doesn't, even though viewmd already pipes its rendered output through `less`.

## Motivation / problem

Reported by the maintainer: scrolling with the mouse/trackpad does nothing while viewing viewmd's output, despite `less` being the pager underneath. Root cause is `DEFAULT_PAGER = ["less", "-R", "-F", "-X", "-S"]` (`viewmd/pager.py`): `-X` (`--no-init`) tells `less` to skip sending the terminal's init/deinit sequences, which is what switches the terminal into its alternate screen buffer. Most terminal emulators only translate mouse-wheel events into arrow-key input for the foreground program while that program is using the alternate screen; without it, wheel/trackpad scroll events go to the terminal's own native scrollback instead of to `less`, so `less` never receives them as input at all -- from `less`'s perspective nothing happened, which is exactly what the maintainer observed. `-X` itself is intentional (it matches `git`'s own default pager flags, `less -FRX`, so the paged output stays visible in the terminal's scrollback after quitting instead of being wiped by the alternate-screen exit) and is not being removed by this issue -- GNU `less` 581+ has a separate `--mouse` flag that enables wheel scrolling natively, independent of the alternate screen, which is the actual fix.

## Requirements

1. MUST add `--mouse` to `viewmd/pager.py`'s `DEFAULT_PAGER` so mouse-wheel/trackpad scrolling moves the view up/down in the default pager, without removing or altering `-R`/`-F`/`-X`/`-S`.
2. MUST NOT change pager behavior when a user has set `$PAGER` themselves -- `--mouse` is only added to viewmd's own *default*, exactly like `-S` (VIEWMD-0018) was; an explicit `$PAGER` override is used verbatim, as today.
3. MUST NOT break or degrade paging on a `less` build old enough to not support `--mouse` (pre-582) -- confirmed that `less` treats an unrecognized long option as a non-fatal warning to stderr and continues running normally (verified directly: `less --bogus-flag -F -X` still exits 0 and still displays its input), so no version probing is required, but this must be re-verified specifically for `--mouse` against at least one such older build if one is reasonably available, per the Acceptance section.
4. MUST NOT change any other pager behavior (line-chopping, screen-clearing on quit, colored output) -- this issue is additive only.

## Non-goals

- Any change to viewmd's own future from-scratch interactive pager ([VIEWMD-0007](VIEWMD-0007-link-navigation.md)'s v1) -- that pager won't delegate to external `less` at all, so it needs its own mouse-scroll handling; this issue only fixes today's `less`-delegated pager. VIEWMD-0007 has its own mouse-scrolling requirement, added alongside this issue.
- Configuring scroll speed/direction (`less --mouse` defaults to 1 line per wheel step; `--MOUSE` reverses direction) -- not exposed as a viewmd option, matching `-S`/`-X`'s own fixed, non-configurable posture.
- Mouse click-to-navigate, text selection, or any other mouse interaction beyond wheel-scroll -- out of scope, `--mouse` incidentally also enables `less`'s own click-to-mark behavior, which is unaffected/unmodified by this issue either way.

## Design notes / links

`viewmd/pager.py:9` is the only line this issue touches: `DEFAULT_PAGER = ["less", "-R", "-F", "-X", "-S"]` becomes `[..., "--mouse"]` appended. `docs/PLAN.md`, `docs/SECURITY.md`, and `README.md` each quote the current default flags in prose (`less -R -F -X`) and need updating to match. Related to [VIEWMD-0007](VIEWMD-0007-link-navigation.md): that issue's v1 replaces this external-`less` delegation with viewmd's own scrolling loop for the ToC-popup feature to work at all, at which point this fix's `--mouse` flag becomes irrelevant (there will be no `less` subprocess to pass it to) -- but until VIEWMD-0007 v1 ships, today's `less`-delegated pager is what every reader actually uses, so this fix stands on its own regardless of when (or whether) VIEWMD-0007 is built.

## Acceptance / verification

- `./run-tests.sh` green, including a test asserting `--mouse` is present in `viewmd.pager.DEFAULT_PAGER` and that a user-supplied `$PAGER` is still used verbatim, unmodified (requirement 2).
- Manual check: the maintainer scrolls with a mouse wheel/trackpad while viewing a long file (e.g. `./viewmd.sh README.md`) and confirms the view now moves, where it did not before this fix.
- Manual check (requirement 3): run the same command against whatever `less` version is reasonably available (e.g. an older Homebrew/apt version, or a container image pinned to an older release) and confirm output still displays normally, even if `--mouse` itself has no effect on that build.

## Peer review

Not applicable; not yet built.

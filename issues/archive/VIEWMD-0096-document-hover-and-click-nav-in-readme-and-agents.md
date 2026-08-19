---
id: VIEWMD-0096
title: Document hover feedback and directory-listing click-nav in README; record VIEWMD-0092/0093/0094 lessons in AGENTS.md
status: implemented
area: [docs]
effort: low
created: 2026-08-19
updated: 2026-08-19
accepted_by: George Moses <gmo6nl@gmail.com>
accepted_at: 2026-08-19
commits: [e89572e]
related: [VIEWMD-0081, VIEWMD-0092, VIEWMD-0093, VIEWMD-0094]
supersedes: []
changelog: "[1.43.1]"
reason:
---

# Document hover feedback and directory-listing click-nav in README; record VIEWMD-0092/0093/0094 lessons in AGENTS.md

## Summary

`README.md`'s "Interactive pager" section never mentions VIEWMD-0092's mouse hover-highlighting, and its click-to-follow footnote has been stale since VIEWMD-0081 shipped (1.40.0) — it still says click-to-follow/`B` are "single-document-only" and inert for a directory listing, which stopped being true once subdirectory rows (VIEWMD-0081) and `.md` file rows (VIEWMD-0093) both became clickable. Separately, this session's VIEWMD-0092/0093/0094 work surfaced four reusable lessons worth recording in `AGENTS.md` alongside its existing "lessons learned" paragraphs.

## Motivation / problem

Documentation drift: a reader following the README's own footnote would believe clicking a link in a directory listing does nothing, when it's been a working feature for two releases. VIEWMD-0092 shipped with no README mention at all. Separately, four findings from this session's manual-testing rounds (a wrong terminal-capability assumption corrected only by an empirical probe, a semantic merge conflict git resolved silently, a chip-ambiguity rule that conflated "multi-key" with "ambiguous," and a wrapping style silently cut short by an embedded `RESET`) match the pattern `AGENTS.md` already keeps a running list of, established across VIEWMD-0015/0022/0043.

## Requirements

1. MUST update `README.md`'s "Interactive pager" section to mention hover highlighting of clickable targets.
2. MUST correct the click-to-follow/`B` footnote to reflect that a bare directory listing (subdirectory and `.md` file rows alike) is click-navigable, narrowing the "inert" claim to multi-file views only.
3. MUST document that the `cancel`/`close help` echo-area chip is clickable while a ToC popup or the help screen is open (VIEWMD-0092's own follow-up fix).
4. MUST add lessons to `AGENTS.md`, in the same voice/format as its existing entries (a bold lead sentence, one continuous unwrapped paragraph, citing the originating `VIEWMD-NNNN`), covering: verifying terminal capabilities empirically rather than from reputation/memory; running `./run-tests.sh` immediately after every `--no-ff` merge since a clean auto-merge can still be semantically broken; distinguishing "multiple listed keys" from "genuinely ambiguous outcome" when deciding whether a binding gets a real invoke; and checking for an embedded `RESET` before wrapping an already-colored span in a new style.

## Non-goals

- No change to any other README section (Mermaid diagrams, config file, etc.).
- No new AGENTS.md process rules — these are retrospective lessons, not new gates.

## Design notes / links

See `issues/archive/VIEWMD-0092-hover-feedback-clickable-targets.md`, `VIEWMD-0093-clickable-directory-listing-files.md`, and `VIEWMD-0094-stray-mouse-report-bytes-after-click-quit.md` for the full peer-review trails these lessons are drawn from.

## Acceptance / verification

Read-through: `README.md`'s pager section and footnotes describe current behavior accurately (spot-checked against `viewmd/interactive_pager.py`); `AGENTS.md`'s new paragraphs read consistently with its existing ones. `./run-tests.sh` green (no test asserts on README/AGENTS.md prose, but the gate should stay green after the edit).

## Peer review

- **implementing agent** (agent), 2026-08-19: wrote both docs updates directly per the maintainer's request, then filed this issue after the fact to keep them tracked per AGENTS.md's own issue-first rule, mirroring VIEWMD-0095's precedent for a small direct-request doc fix. No worktree, per the same fast-path the maintainer approved for VIEWMD-0095.
- **George Moses** (maintainer), 2026-08-19: requested directly ("Update README.md. Add key findings in AGENTS.md"); approved without a worktree.

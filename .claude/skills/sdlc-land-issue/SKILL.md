---
name: sdlc-land-issue
description: Land a finished viewmd issue on develop through the Definition of Done -- independent review, maintainer sign-off, and the two-commit landing pattern. Use once an issue's implementation is complete and ./run-tests.sh is green in its worktree, before merging anything into develop.
---

Carry a finished change through `issues/AGILE.md`'s Definition of Done. Do not merge to `develop`
or archive the issue on your own initiative at any point in this sequence -- every gate below ends
in an explicit question to the maintainer.

1. **Green gate.** Run `./run-tests.sh` in the issue's worktree. It must be clean before anything
   else here happens.

2. **Documentation check.** Launch the `documentation` subagent (via the `Agent` tool,
   `subagent_type: documentation`) on the issue file and the diff (`git diff develop...HEAD`). It
   checks whether `README.md` or `docs/example.md` need updating to describe user-facing behavior
   this change adds or alters, and makes those edits directly when needed -- run it before the
   peer review so any doc edits it makes are included in what gets reviewed.

3. **Independent review.** Launch the `peer-reviewer` subagent (via the `Agent` tool,
   `subagent_type: peer-reviewer`) on the issue file and the diff (`git diff develop...HEAD`). It
   is a fresh agent with no memory of the implementing session and no `Edit`/`Write` tools, which
   is what makes this pass independent rather than self-attested -- never write this review line
   yourself from the implementing session, and never satisfy this step with a `fork` (a fork
   inherits this session's context, defeating the point). If it reports `CHANGES NEEDED`, fix them,
   re-run `./run-tests.sh`, and re-review before continuing.

4. **Append the review.** Add the subagent's verdict line verbatim to the issue's Peer review
   section (append, never overwrite any existing line).

5. **Maintainer sign-off.** Show the maintainer the diff and the recorded review findings, then ask
   outright: "commit and close this out?" A maintainer verdict on the change is itself a second,
   distinct Peer-review line (`- **<name>** (maintainer), YYYY-MM-DD: ...`) -- append it, attributed
   to the maintainer, transcribing what they actually said rather than the agent's own opinion. Do
   not proceed past this step without both Peer-review lines present and an explicit yes.

6. **Land it -- two commits on `develop`, not one:**
   - The implementation commit (code + tests + this Peer-review section), on the
     `bug|feature|story/VIEWMD-NNNN` branch, brought into `develop` via
     `git merge --no-ff` (no squash, no rebase).
   - Run `./run-tests.sh` again immediately after the merge, before archiving -- a clean `--no-ff`
     auto-merge is not proof the result is correct, only that git didn't need a human to pick
     between two textual versions of the same lines (see AGENTS.md's semantic-conflict pitfall).
   - A separate "Archive VIEWMD-NNNN, bump to X.Y.Z" commit made directly on `develop` after that:
     move the issue file to `issues/archive/`, set `status: implemented`, `commits:` to the
     implementation commit's short SHA (not this commit's own, which doesn't exist yet while
     writing the file), `changelog:` to the new `CHANGELOG.md` anchor, bump
     `pyproject.toml`/`viewmd/__init__.py`, add the `CHANGELOG.md` entry, and regenerate the issues
     index (`./tools.sh issues`).

7. **Clean up.** Delete the now-landed branch (`git branch -d <kind>/VIEWMD-NNNN`) and remove the
   worktree (`./tools.sh worktree remove VIEWMD-NNNN`) once it has no uncommitted changes.

This does not include the `main`-merge/tag/release step -- that is a separate, explicit maintainer
decision. Use the `sdlc-release` skill for that, never as a side effect of landing an issue.

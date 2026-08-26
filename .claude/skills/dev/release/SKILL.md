---
name: release
description: Cut a viewmd release -- merge develop into main, tag, and publish the GitHub release. Use only on the maintainer's own explicit "cut a release" decision, never automatically after landing an issue.
---

`main` only advances via this explicit step, per `AGENTS.md`. Never run this as a side effect of
`dev:land-issue` -- ask the maintainer outright "cut a release?" before starting, even if `develop`
is already green and several issues have landed since the last release.

1. Confirm `develop` is where you expect it (`git log --oneline -5`) and `./run-tests.sh` is green
   on it. The version to release is whatever `pyproject.toml`/`viewmd/__init__.py` already carries
   on `develop` -- each issue's own archive commit already bumped it (minor for a
   feature/story, patch for a bug fix), so this step does not bump the version itself.
2. `git checkout main && git merge --no-ff develop` -- no squash, no rebase.
3. `git tag vX.Y.Z` matching that version.
4. `git push origin main develop vX.Y.Z`.
5. `gh release create vX.Y.Z --title vX.Y.Z --notes-file <path>`, where `<path>` holds that
   version's `CHANGELOG.md` entry verbatim as the release notes -- not a rewritten summary. A
   version bump on `main` without a published GitHub release is an incomplete release.
6. Switch back off `main` (e.g. `git checkout develop`) once done.

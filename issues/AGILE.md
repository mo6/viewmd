# Definition of Ready / Definition of Done

The two gates an issue passes through, referenced from [AGENTS.md](../AGENTS.md) and
[README.md](README.md). Kept short deliberately: viewmd is a single-package CLI tool with one
maintainer, so there is no epic/feature/story hierarchy to define here, just the two moments that
actually gate work.

## Definition of Ready

An issue is ready to implement when, in this order:

1. It has `effort: low | medium | high` set.
2. It has been shown to the maintainer and explicitly accepted — a plain "yes," never inferred
   from silence or from the maintainer not objecting.
3. `accepted_by` and `accepted_at` are filled on that "yes," and `status` moves to `in-progress`.

Only after all three does implementation start.

## Definition of Done

A change is done, and its issue may be archived, when, in this order:

1. It is implemented against its issue's requirements.
2. `./run-tests.sh` is green (pytest, ruff, `tools/issues.py --check`).
3. It has been peer-reviewed, and every review (agent or maintainer) is recorded as its own line
   in the issue's **Peer review** section, appended, never overwritten.
4. The maintainer has been shown the diff and the review findings and asked outright, "commit
   and close this out?" — and has said yes.

Only after all four does the change get committed, merged to `develop` (`--no-ff`, no
squash/rebase), and the issue moved to `issues/archive/` with its commit id(s) filled in. `main`
only moves on an explicit, separate release step (see [AGENTS.md](../AGENTS.md)).
